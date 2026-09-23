from __future__ import annotations

import os
import sys
import types
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox, QStackedWidget

import app


class AppRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])
        cls.settings_directory = tempfile.TemporaryDirectory()
        settings_path = Path(cls.settings_directory.name) / "draft.ini"
        cls.settings_patch = patch.object(
            app, "QSettings", side_effect=lambda *_args: QSettings(str(settings_path), QSettings.IniFormat)
        )
        cls.settings_patch.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.settings_patch.stop()
        cls.settings_directory.cleanup()

    def test_window_ocr_accepts_capture_triplet_and_returns_screen_point(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        worker._capture_window = Mock(return_value=("cv2", "frame", (10, 20)))
        worker._run_ocr = Mock(
            return_value=[
                {
                    "text": "目标",
                    "score": 0.99,
                    "points": [(0, 0), (10, 10)],
                }
            ]
        )
        worker._sleep = lambda _seconds: None

        point = worker._wait_for_ocr(
            {"target_text": "目标", "timeout": 0.1, "confidence": 0.6},
            window=True,
        )

        self.assertEqual(point, (15, 25))
        worker._capture_window.assert_called_once_with()

    def test_dirty_state_is_explicit_and_title_is_marked(self) -> None:
        titles: list[str] = []
        autosaves: list[bool] = []
        fake_window = SimpleNamespace(
            current_file=Path("script.json"),
            is_dirty=False,
            setWindowTitle=titles.append,
            _schedule_autosave=lambda: autosaves.append(True),
        )

        app.MainWindow._set_dirty(fake_window, False)
        app.MainWindow._set_dirty(fake_window, True)

        self.assertFalse(titles[0].endswith(" *"))
        self.assertTrue(titles[-1].endswith(" *"))
        self.assertTrue(fake_window.is_dirty)
        self.assertEqual(len(autosaves), 1)

        app.MainWindow._set_dirty(fake_window, False)
        self.assertFalse(fake_window.is_dirty)
        self.assertFalse(titles[-1].endswith(" *"))

    def test_flow_import_normalizes_null_and_invalid_numeric_values(self) -> None:
        window = app.MainWindow()
        task = {
            "name": "输入容错",
            "steps": [
                {"type": "click", "x": None, "y": "bad"},
            ],
            "flow": {
                "nodes": [
                    {"id": "start", "type": "start", "x": None, "y": "bad"},
                    {
                        "id": "step_1",
                        "type": "action",
                        "x": None,
                        "y": "bad",
                        "step": {"type": "click", "x": None, "y": "bad"},
                    },
                    {"id": "end", "type": "end", "x": None, "y": "bad"},
                ],
                "edges": [
                    {"from": "start", "to": "step_1", "port": "next"},
                    {"from": "step_1", "to": "end", "port": "next"},
                ],
            },
        }

        normalized = window._normalize_window_task(task, 1)
        nodes = {node["id"]: node for node in normalized["flow"]["nodes"]}
        normalized_wait = window._normalize_step({"type": "wait", "seconds": "bad"})

        self.assertEqual(nodes["start"]["x"], 0.0)
        self.assertEqual(nodes["start"]["y"], 0.0)
        self.assertEqual(nodes["step_1"]["step"]["x"], 0)
        self.assertEqual(nodes["step_1"]["step"]["y"], 0)
        self.assertEqual(normalized["steps"][0]["type"], "click")
        self.assertEqual(normalized["steps"][0]["x"], 0)
        self.assertEqual(normalized_wait["seconds"], 1.0)
        window.deleteLater()

    def test_flow_validator_accepts_normalized_linear_flow(self) -> None:
        flow = app.flow_from_steps([app.default_step("wait")])
        self.assertEqual(app.validate_flow(flow), [])

    def test_screen_capture_uses_virtual_desktop_monitor(self) -> None:
        class FakeMss:
            def __init__(self) -> None:
                self.monitors = [
                    {"left": -100, "top": 20, "width": 3, "height": 2},
                    {"left": 0, "top": 20, "width": 2, "height": 2},
                ]
                self.requested_monitor = None

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def grab(self, monitor):
                self.requested_monitor = monitor
                import numpy as np

                return np.zeros((2, 3, 4), dtype=np.uint8)

        fake_instance = FakeMss()
        fake_mss_module = types.SimpleNamespace(mss=lambda: fake_instance)
        worker = app.ScriptWorker([], Path(__file__).parent)

        with patch.dict(sys.modules, {"mss": fake_mss_module}):
            _cv2, frame, origin = worker._capture()

        self.assertEqual(origin, (-100, 20))
        self.assertEqual(frame.shape, (2, 3, 3))
        self.assertIs(fake_instance.requested_monitor, fake_instance.monitors[0])

    def test_main_window_smoke_has_scrollable_properties_and_bounded_log(self) -> None:
        window = app.MainWindow()
        self.assertTrue(hasattr(window, "properties_scroll"))
        self.assertEqual(window.log_view.document().maximumBlockCount(), 5000)
        self.assertFalse(hasattr(window, "down_button"))
        window.deleteLater()

    def test_template_library_resolves_relative_windows_paths_and_decodes_unicode_files(self) -> None:
        window = app.MainWindow()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.json"
            asset = root / "窗口任务 1" / "模板图.png"
            asset.parent.mkdir()
            image = QImage(12, 9, QImage.Format.Format_RGB32)
            image.fill(0xFF22AA66)
            self.assertTrue(image.save(str(asset)))
            window.current_file = script

            resolved = window._resolve_template_library_path(r"窗口任务 1\模板图.png", "任意任务")
            self.assertEqual(resolved, asset)
            self.assertFalse(window._load_template_pixmap(resolved).isNull())

        window._autosave_timer.stop()
        window.deleteLater()

    def test_relative_current_file_is_resolved_from_working_directory(self) -> None:
        window = app.MainWindow()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.json"
            script.write_text("{}", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                window.current_file = Path("script.json")
                self.assertEqual(window._base_dir().resolve(), root.resolve())
            finally:
                os.chdir(previous)
        window._autosave_timer.stop()
        window.deleteLater()

    def test_node_properties_never_exposes_horizontal_scrollbar(self) -> None:
        window = app.MainWindow()
        window.resize(500, 500)
        window.show()
        window.main_tabs.setCurrentWidget(window.editor_page)
        action_item = next(
            item for item in window.flow_canvas.node_items.values()
            if item.node.get("type") == "action"
        )
        action_item.setSelected(True)
        window._on_flow_node_selected(action_item)
        self.qt_app.processEvents()

        self.assertEqual(
            window.properties_scroll.horizontalScrollBarPolicy(),
            app.Qt.ScrollBarAlwaysOff,
        )
        self.assertFalse(window.properties_scroll.horizontalScrollBar().isVisible())
        window.hide()
        window.deleteLater()

    def test_ui_refresh_registers_chinese_font_and_collapsible_inspector(self) -> None:
        family = app.configure_ui_font(self.qt_app)
        self.assertTrue(family)
        window = app.MainWindow()
        window.show()
        window.main_tabs.setCurrentWidget(window.editor_page)
        self.qt_app.processEvents()
        self.assertFalse(window.editor_inspector_panel.isVisible())
        self.assertFalse(window.properties_scroll.isVisible())

        action_item = next(
            item for item in window.flow_canvas.node_items.values()
            if item.node.get("type") == "action"
        )
        action_item.setSelected(True)
        window._on_flow_node_selected(action_item)
        self.qt_app.processEvents()
        self.assertTrue(window.editor_inspector_panel.isVisible())
        self.assertTrue(window.properties_scroll.isVisible())
        self.assertEqual(window.font().family(), family)
        window.hide()
        window.deleteLater()

    def test_immersive_workspace_navigation_uses_real_pages(self) -> None:
        window = app.MainWindow()
        self.assertIsInstance(window.main_tabs, QStackedWidget)

        for button, page in (
            (window.nav_tasks_button, window.window_tasks_page),
            (window.nav_flow_button, window.editor_page),
            (window.nav_logs_button, window.run_history_page),
            (window.nav_templates_button, window.template_library_page),
            (window.nav_settings_button, window.settings_page),
        ):
            button.click()
            self.qt_app.processEvents()
            self.assertIs(window.main_tabs.currentWidget(), page)
            self.assertTrue(button.isChecked())

        window._autosave_timer.stop()
        window.deleteLater()

    def test_log_page_counts_messages_and_template_page_reads_referenced_paths(self) -> None:
        window = app.MainWindow()
        window._clear_log_preview()
        window._append_log("识别按钮失败 | 当前最高匹配度 0.72")
        self.assertIn("日志 1", window.status_metrics_label.text())
        self.assertIn("错误 1", window.status_metrics_label.text())

        template = Path(__file__).parent / "screenshots" / "template.png"
        step = app.default_step("window_click_image")
        step["image"] = str(template)
        window.window_tasks[0]["steps"] = [step]
        window._refresh_template_library()
        self.assertGreaterEqual(window.template_list.count(), 1)
        item_data = window.template_list.item(0).data(app.Qt.UserRole)
        self.assertEqual(Path(item_data["path"]), template)

        window._autosave_timer.stop()
        window.deleteLater()

    def test_template_library_tracks_nodes_and_deletes_only_unreferenced_assets(self) -> None:
        window = app.MainWindow()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            window.current_file = root / "script.json"
            task_dir = root / "任务甲"
            task_dir.mkdir()
            image = QImage(10, 8, QImage.Format.Format_RGB32)
            image.fill(0xFF22AA66)
            template_path = task_dir / "template.png"
            self.assertTrue(image.save(str(template_path)))

            first = app.default_step("click_image")
            first.update({"image": "template.png", "label": "第一次点击"})
            second = app.default_step("click_image")
            second.update({"image": "template.png", "label": "第二次点击"})
            task = window.window_tasks[0]
            task["name"] = "任务甲"
            task["steps"] = [first, second]
            task["flow"] = app.flow_from_steps(task["steps"])
            window._refresh_template_library()
            self.qt_app.processEvents()

            self.assertEqual(window.template_list.count(), 1)
            item = window.template_list.item(0)
            self.assertEqual(item.text(), "template.png")
            data = item.data(app.Qt.UserRole)
            self.assertEqual(data["references"], 2)
            self.assertEqual(len(data["usages"]), 2)
            self.assertIn("引用次数 2", window.template_usage_label.text())
            self.assertEqual(window.template_reference_list.count(), 2)

            with patch.object(QMessageBox, "warning") as warning:
                window._delete_selected_template()
            warning.assert_called_once()
            self.assertTrue(template_path.exists())

            usage = data["usages"][1]
            window._locate_template_usage(usage)
            self.qt_app.processEvents()
            self.assertIs(window.main_tabs.currentWidget(), window.editor_page)
            self.assertEqual(window._selected_flow_node().get("id"), usage["node_id"])

            task["steps"] = [app.default_step("wait")]
            task["flow"] = app.flow_from_steps(task["steps"])
            orphan = task_dir / "orphan.png"
            self.assertTrue(image.save(str(orphan)))
            window._refresh_template_library()
            self.qt_app.processEvents()
            orphan_row = next(
                index
                for index in range(window.template_list.count())
                if window.template_list.item(index).text() == "orphan.png"
            )
            window.template_list.setCurrentRow(orphan_row)
            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                window._delete_selected_template()
            self.assertFalse(orphan.exists())

        window._autosave_timer.stop()
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
