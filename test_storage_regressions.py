from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

import app


class StorageRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        settings_path = self.root / "test-settings.ini"
        settings_patch = patch.object(
            app, "QSettings",
            side_effect=lambda *_args: QSettings(str(settings_path), QSettings.IniFormat),
        )
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        self.window = app.MainWindow()
        self.addCleanup(self.window.deleteLater)
        self.addCleanup(self.window._autosave_timer.stop)
        self.addCleanup(self.window._close_timer.stop)

    def _select_tasks(self, tasks: list[dict]) -> None:
        self.window.window_tasks = tasks
        self.window._refresh_window_task_list(0)

    def test_cancel_open_keeps_existing_tasks_and_draft(self) -> None:
        source = self.root / "source.json"
        source.write_text(json.dumps({"window_tasks": [{"name": "new", "steps": []}]}), encoding="utf-8")
        self.window.window_tasks[0]["name"] = "keep"
        self.window._set_dirty(True)
        self.window._write_autosave()
        previous_draft = str(self.window._draft_settings.value("draft"))
        previous_tasks = copy.deepcopy(self.window.window_tasks)

        with patch.object(app.QFileDialog, "getOpenFileName", return_value=(str(source), "")):
            with patch.object(app.QMessageBox, "question", return_value=QMessageBox.Cancel):
                self.window._open_script()

        self.assertTrue(self.window.is_dirty)
        self.assertIsNone(self.window.current_file)
        self.assertEqual(self.window.window_tasks, previous_tasks)
        self.assertEqual(self.window._draft_settings.value("draft"), previous_draft)

    def test_save_and_reopen_current_file_reads_newly_written_json(self) -> None:
        source = self.root / "script.json"
        source.write_text(json.dumps({"window_tasks": [{"name": "outdated", "steps": []}]}), encoding="utf-8")
        self.window.current_file = source
        self.window.window_tasks[0]["name"] = "recent edits"
        self.window._set_dirty(True)

        with patch.object(app.QFileDialog, "getOpenFileName", return_value=(str(source), "")):
            with patch.object(app.QFileDialog, "getSaveFileName", return_value=(str(source), "")):
                with patch.object(app.QMessageBox, "question", return_value=QMessageBox.Save):
                    self.window._open_script()

        self.assertEqual(self.window.window_tasks[0]["name"], "recent edits")
        self.assertEqual(json.loads(source.read_text(encoding="utf-8"))["window_tasks"][0]["name"], "recent edits")
        self.assertEqual(json.loads(str(self.window._draft_settings.value("draft")))["window_tasks"][0]["name"], "recent edits")
        self.assertFalse(self.window.is_dirty)

    def test_close_discard_restores_last_accepted_draft(self) -> None:
        baseline = str(self.window._draft_settings.value("draft"))
        self.window.window_tasks[0]["name"] = "discarded"
        self.window._set_dirty(True)
        self.window._write_autosave()
        self.assertNotEqual(self.window._draft_settings.value("draft"), baseline)

        event = QCloseEvent()
        with patch.object(app.QMessageBox, "question", return_value=QMessageBox.Discard):
            self.window.closeEvent(event)

        self.assertTrue(event.isAccepted())
        self.assertEqual(self.window._draft_settings.value("draft"), baseline)
        self.assertEqual(self.window._last_accepted_draft[0], baseline)

    def test_close_discard_preserves_restored_unexported_draft(self) -> None:
        self.window.window_tasks[0]["name"] = "previous draft"
        self.window._write_autosave()
        baseline = str(self.window._draft_settings.value("draft"))
        restored = app.MainWindow()
        self.addCleanup(restored.deleteLater)
        self.addCleanup(restored._autosave_timer.stop)
        self.assertEqual(restored.window_tasks[0]["name"], "previous draft")
        restored.window_tasks[0]["name"] = "new edits"
        restored._set_dirty(True)
        restored._write_autosave()

        with patch.object(app.QMessageBox, "question", return_value=QMessageBox.Discard):
            restored.closeEvent(QCloseEvent())

        self.assertEqual(restored._draft_settings.value("draft"), baseline)

    def test_failed_export_keeps_current_file_and_dirty_state(self) -> None:
        source = self.root / "old.json"
        destination = self.root / "new" / "target.json"
        self.window.current_file = source
        self.window._set_dirty(True)
        with patch.object(app.QFileDialog, "getSaveFileName", return_value=(str(destination), "")):
            with patch.object(app.os, "replace", side_effect=PermissionError("locked")):
                with patch.object(app.QMessageBox, "critical") as error:
                    saved = self.window._export_json()

        self.assertFalse(saved)
        self.assertTrue(self.window.is_dirty)
        self.assertEqual(self.window.current_file, source)
        self.assertFalse(destination.exists())
        self.assertEqual(list(destination.parent.glob("*.tmp")), [])
        error.assert_called_once()

    def test_failed_json_replace_rolls_back_newly_copied_assets(self) -> None:
        source_root = self.root / "source"
        target_root = self.root / "target"
        source_root.mkdir()
        (source_root / "image.png").write_bytes(b"image")
        task = app.default_window_task(1)
        step = app.default_step("wait_image")
        step["image"] = "image.png"
        task["steps"] = [step]
        task["flow"] = app.flow_from_steps([step])
        self.window.current_file = source_root / "original.json"
        self._select_tasks([task])
        self.window._set_dirty(True)
        destination = target_root / "script.json"
        original_replace = os.replace

        def fail_json_only(source, target):
            if Path(target) == destination:
                raise PermissionError("json file is locked")
            return original_replace(source, target)

        with patch.object(app.QFileDialog, "getSaveFileName", return_value=(str(destination), "")):
            with patch.object(app.os, "replace", side_effect=fail_json_only):
                with patch.object(app.QMessageBox, "critical"):
                    self.assertFalse(self.window._export_json())

        self.assertFalse((target_root / "image.png").exists())
        self.assertFalse(destination.exists())
        self.assertEqual(self.window.current_file, source_root / "original.json")
        self.assertTrue(self.window.is_dirty)

    def test_export_copies_task_and_root_images_with_conditions(self) -> None:
        source_root = self.root / "来源"
        target_root = self.root / "导出"
        task_name = "中文任务"
        (source_root / task_name).mkdir(parents=True)
        (source_root / "root.png").write_bytes(b"root")
        (source_root / task_name / "task.png").write_bytes(b"task")
        step = app.default_step("window_click_image")
        step["image"] = "task.png"
        task = app.default_window_task(1)
        task["name"] = task_name
        task["steps"] = [step]
        task["flow"] = app.flow_from_steps([step])
        task["flow"]["nodes"].append({
            "id": "condition", "type": "condition", "x": 100, "y": 100,
            "conditions": [{"type": "image_exists", "image": "root.png"}],
        })
        self.window.current_file = source_root / "original.json"
        self._select_tasks([task])
        destination = target_root / "task.json"

        with patch.object(app.QFileDialog, "getSaveFileName", return_value=(str(destination), "")):
            self.assertTrue(self.window._export_json())

        exported = json.loads(destination.read_text(encoding="utf-8"))["window_tasks"][0]
        self.assertEqual(exported["steps"][0]["image"], "task.png")
        self.assertEqual(exported["flow"]["nodes"][-1]["conditions"][0]["image"], "root.png")
        self.assertEqual((target_root / task_name / "task.png").read_bytes(), b"task")
        self.assertEqual((target_root / "root.png").read_bytes(), b"root")
        self.assertEqual(self.window.current_file, destination)
        self.assertFalse(self.window.is_dirty)

    def test_asset_conflict_does_not_replace_existing_file_or_json(self) -> None:
        source_root = self.root / "original"
        target_root = self.root / "target"
        task = app.default_window_task(1)
        step = app.default_step("wait_image")
        step["image"] = "template.png"
        task["steps"] = [step]
        task["flow"] = app.flow_from_steps([step])
        source_root.mkdir()
        target_root.mkdir()
        (source_root / "template.png").write_bytes(b"fresh")
        (target_root / "template.png").write_bytes(b"old")
        destination = target_root / "script.json"
        destination.write_text("previous JSON", encoding="utf-8")
        self.window.current_file = source_root / "original.json"
        self._select_tasks([task])
        self.window._set_dirty(True)

        with patch.object(app.QFileDialog, "getSaveFileName", return_value=(str(destination), "")):
            with patch.object(app.QMessageBox, "critical") as error:
                self.assertFalse(self.window._export_json())

        self.assertEqual(destination.read_text(encoding="utf-8"), "previous JSON")
        self.assertEqual((target_root / "template.png").read_bytes(), b"old")
        self.assertTrue(self.window.is_dirty)
        self.assertEqual(self.window.current_file, source_root / "original.json")
        error.assert_called_once()

    def test_relative_asset_outside_source_folder_is_rebased_safely(self) -> None:
        source_root = self.root / "source"
        shared = self.root / "shared" / "image.png"
        shared.parent.mkdir()
        shared.write_bytes(b"shared")
        source_root.mkdir()
        task = app.default_window_task(1)
        step = app.default_step("wait_image")
        step["image"] = str(Path("..") / ".." / "shared" / "image.png")
        (source_root / task["name"]).mkdir()
        task["steps"] = [step]
        task["flow"] = app.flow_from_steps([step])
        self.window.current_file = source_root / "script.json"
        self._select_tasks([task])
        original_task = self.window.window_tasks[0]
        destination = self.root / "target" / "script.json"

        with patch.object(app.QFileDialog, "getSaveFileName", return_value=(str(destination), "")):
            with patch.object(app.QMessageBox, "critical") as error:
                self.assertTrue(self.window._export_json(), error.call_args)

        exported_step = json.loads(destination.read_text(encoding="utf-8"))["window_tasks"][0]["steps"][0]
        worker = app.ScriptWorker([], destination.parent, output_dir=destination.parent / task["name"])
        resolved = worker._resolve_input_path(exported_step["image"])
        self.assertEqual(resolved.read_bytes(), b"shared")
        self.assertIs(self.window.window_tasks[0], original_task)
        current_image = self.window.window_tasks[0]["steps"][0]["image"]
        self.assertEqual(current_image, exported_step["image"])
        self.assertEqual(worker._resolve_input_path(current_image).read_bytes(), b"shared")
        self.assertEqual(self.window.window_tasks[0]["flow"]["nodes"][1]["step"]["image"], current_image)
        draft = json.loads(str(self.window._draft_settings.value("draft")))
        self.assertEqual(draft["window_tasks"][0]["steps"][0]["image"], current_image)
        restored = app.MainWindow()
        self.addCleanup(restored.deleteLater)
        self.addCleanup(restored._autosave_timer.stop)
        self.assertEqual(restored.window_tasks[0]["steps"][0]["image"], current_image)
        self.assertEqual(restored.current_file, destination)

    def test_export_detects_task_image_shadowing_root_template(self) -> None:
        source_root = self.root / "source"
        destination = self.root / "target" / "script.json"
        source_root.mkdir()
        (source_root / "image.png").write_bytes(b"intended")
        task = app.default_window_task(1)
        step = app.default_step("wait_image")
        step["image"] = "image.png"
        task["steps"] = [step]
        task["flow"] = app.flow_from_steps([step])
        shadow = destination.parent / task["name"] / "image.png"
        shadow.parent.mkdir(parents=True)
        shadow.write_bytes(b"wrong")
        self.window.current_file = source_root / "old.json"
        self._select_tasks([task])

        with patch.object(app.QFileDialog, "getSaveFileName", return_value=(str(destination), "")):
            with patch.object(app.QMessageBox, "critical") as error:
                self.assertFalse(self.window._export_json())

        self.assertFalse(destination.exists())
        self.assertEqual(shadow.read_bytes(), b"wrong")
        error.assert_called_once()

    def test_model_export_syncs_actions_conditions_canvas_draft_and_second_export(self) -> None:
        source = self.root / "source"
        source.mkdir()
        model = self.root / "模型.onnx"
        model.write_bytes(b"test model")
        task = app.default_window_task(1)
        step = app.default_step("window_click_yolo")
        step.update(model="../模型.onnx", target_class="button")
        task["steps"] = [step]
        task["flow"] = app.flow_from_steps([step])
        task["flow"]["nodes"].append({
            "id": "check", "type": "condition", "x": 100, "y": 100,
            "conditions": [{"type": "yolo_exists", "model": "../模型.onnx", "target_class": "button"}],
        })
        self.window.current_file = source / "original.json"
        self._select_tasks([task])
        action_id = self.window.flow_canvas.flow["nodes"][1]["id"]
        self.window.flow_canvas.node_items[action_id].setSelected(True)
        for folder in ("导出一", "导出二"):
            destination = self.root / folder / "script.json"
            with patch.object(app.QFileDialog, "getSaveFileName", return_value=(str(destination), "")):
                self.assertTrue(self.window._export_json())
            exported = json.loads(destination.read_text(encoding="utf-8"))["window_tasks"][0]
            expected = exported["steps"][0]["model"]
            self.assertTrue(expected.startswith("script_assets"))
            worker = app.ScriptWorker([], destination.parent, output_dir=destination.parent / task["name"])
            self.assertEqual(worker._resolve_input_path(expected).read_bytes(), b"test model")
            draft = json.loads(str(self.window._draft_settings.value("draft")))
            for current in (exported, self.window.window_tasks[0], draft["window_tasks"][0]):
                self.assertEqual(current["steps"][0]["model"], expected)
                self.assertEqual(current["flow"]["nodes"][1]["step"]["model"], expected)
                self.assertEqual(current["flow"]["nodes"][-1]["conditions"][0]["model"], expected)
            self.assertEqual(self.window.flow_canvas.flow["nodes"][1]["step"]["model"], expected)
            self.assertEqual(self.window.yolo_model_edit.text(), expected)
            restored = app.MainWindow()
            self.addCleanup(restored.deleteLater)
            self.addCleanup(restored._autosave_timer.stop)
            self.assertEqual(restored.window_tasks[0]["steps"][0]["model"], expected)
            self.assertEqual(restored.current_file, destination)

    def test_pending_close_preserves_threads_and_discard_without_reprompting(self) -> None:
        released = threading.Event()
        entered = threading.Event()

        class BlockedThread(QThread):
            def run(self):
                entered.set()
                released.wait(5)

        thread = BlockedThread(self.window)
        worker = Mock()
        key = id(self.window.window_tasks[0])
        self.window.window_task_runs[key] = {"thread": thread, "worker": worker, "row": 0}
        self.window.window_task_status[key] = "运行中"
        baseline = str(self.window._draft_settings.value("draft"))
        self.window.window_tasks[0]["name"] = "discard me"
        self.window._set_dirty(True)
        self.window._write_autosave()
        thread.start()
        self.assertTrue(entered.wait(2))
        try:
            with patch.object(app.QMessageBox, "question", return_value=QMessageBox.Discard) as prompt:
                for _ in range(2):
                    event = QCloseEvent()
                    self.window.closeEvent(event)
                    self.assertFalse(event.isAccepted())
                self.assertTrue(thread.isRunning())
                self.assertIn(key, self.window.window_task_runs)
                self.assertTrue(self.window._close_timer.isActive())
                worker.stop.assert_called_once()
                with patch.object(app, "ScriptWorker") as constructor:
                    self.window._start_window_task(0)
                    constructor.assert_not_called()
                released.set()
                self.assertTrue(thread.wait(2000))
                with patch.object(self.window, "close") as close:
                    self.window._finish_pending_close()
                    close.assert_called_once()
                event = QCloseEvent()
                self.window.closeEvent(event)
                self.assertTrue(event.isAccepted())
                prompt.assert_called_once()
            self.assertEqual(self.window._draft_settings.value("draft"), baseline)
            self.assertEqual(self.window.window_task_runs, {})
        finally:
            released.set()
            thread.wait(2000)

    def test_document_replacement_aborts_if_tasks_are_still_stopping(self) -> None:
        original = self.window.window_tasks
        source = self.root / "new.json"
        source.write_text('{"window_tasks": []}', encoding="utf-8")
        with (
            patch.object(self.window, "_wait_for_window_tasks", return_value=False),
            patch.object(app.QFileDialog, "getOpenFileName", return_value=(str(source), "")),
        ):
            self.window._new_script()
            self.assertIs(self.window.window_tasks, original)
            self.window._open_script()
            self.assertIs(self.window.window_tasks, original)
            self.assertIsNone(self.window.current_file)

    def test_valid_yolo_condition_starts_task_thread(self) -> None:
        self.window.current_file = self.root / "script.json"
        task = app.default_window_task(1)
        task["title_contains"] = "Synthetic target"
        step = app.default_step("wait")
        step["seconds"] = 0
        task["flow"] = app.flow_from_steps([step])
        action_id = task["flow"]["nodes"][1]["id"]
        task["flow"]["nodes"].append({
            "id": "check", "type": "condition", "x": 100, "y": 100, "operator": "and",
            "conditions": [{"type": "yolo_exists", "model": "game.onnx", "target_class": "button"}],
        })
        task["flow"]["edges"] = [
            {"from": "start", "to": "check", "port": "next"},
            {"from": "check", "to": action_id, "port": "true"},
            {"from": "check", "to": "end", "port": "false"},
            {"from": action_id, "to": "end", "port": "next"},
        ]
        self._select_tasks([task])
        with (
            patch.object(app.ScriptWorker, "_find_window"),
            patch.object(app.ScriptWorker, "_condition_yolo_exists", return_value=True) as detect,
            patch.object(app.QMessageBox, "information") as warning,
        ):
            self.window._start_window_task(0)
            try:
                deadline = time.monotonic() + 3
                while self.window.window_task_runs and time.monotonic() < deadline:
                    self.qt_app.processEvents()
                    time.sleep(.01)
                self.assertFalse(self.window.window_task_runs)
                warning.assert_not_called()
                detect.assert_called_once()
                self.assertEqual(self.window.window_task_status[id(task)], "已完成")
            finally:
                self.window._stop_all_window_tasks()
                self.window._wait_for_window_tasks()


if __name__ == "__main__":
    unittest.main()
