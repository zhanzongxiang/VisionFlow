from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

import app
from yolo_runtime import YoloDetector


class YoloIntegrationTests(unittest.TestCase):
    @staticmethod
    def _condition_flow(conditions, operator="and"):
        return {
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "check", "type": "condition", "conditions": conditions, "operator": operator},
                {"id": "end", "type": "end"},
            ],
            "edges": [
                {"from": "start", "to": "check", "port": "next"},
                {"from": "check", "to": "end", "port": "true"},
                {"from": "check", "to": "end", "port": "false"},
            ],
        }

    def test_validator_accepts_yolo_and_mixed_conditions(self) -> None:
        yolo = {"type": "yolo_exists", "model": "模型.onnx", "target_class": "button"}
        for operator in ("and", "or", "not"):
            for conditions in ([yolo], [yolo, {"image": "template.png"}]):
                with self.subTest(operator=operator, conditions=conditions):
                    self.assertEqual(app.validate_flow(self._condition_flow(conditions, operator)), [])
        self.assertEqual(app.validate_flow(self._condition_flow([dict(yolo, target_class=0)])), [])

    def test_validator_rejects_incomplete_or_unknown_conditions(self) -> None:
        for conditions in (
            [], None, [None], [{"type": "unknown", "image": "valid.png"}],
            [{"type": "yolo_exists", "model": "game.onnx", "target_class": ""}],
            [{"type": "yolo_exists", "model": "game.pt", "target_class": "button"}],
            [{"type": "yolo_exists", "model": None, "target_class": "button"}],
            [{"image": "valid.png"}, {"image": ""}],
        ):
            with self.subTest(conditions=conditions):
                self.assertTrue(app.validate_flow(self._condition_flow(conditions)))

    def test_raw_model_letterbox_and_nms(self) -> None:
        # 200x100 frame becomes 640x320 with 160 pixels of vertical padding.
        output = np.zeros((1, 5, 10), dtype=np.float32)
        output[0, :, 0] = (160, 256, 64, 64, 0.93)
        output[0, :, 1] = (162, 256, 64, 64, 0.88)
        session = Mock()
        session.get_inputs.return_value = [SimpleNamespace(name="images", shape=[1, 3, 640, 640])]
        session.get_modelmeta.return_value = SimpleNamespace(custom_metadata_map={"names": "{0: 'button'}"})
        session.run.return_value = [output]
        with patch("onnxruntime.InferenceSession", return_value=session):
            detector = YoloDetector(Path("model.onnx"))
        detections = detector.detect(np.zeros((100, 200, 3), dtype=np.uint8), "button", 0.5)
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].center, (50, 30))
        self.assertAlmostEqual(detections[0].score, 0.93, places=2)
        tensor = session.run.call_args.args[1]["images"]
        self.assertEqual(tensor.shape, (1, 3, 640, 640))

    def test_end_to_end_output_and_unknown_class(self) -> None:
        session = Mock()
        session.get_inputs.return_value = [SimpleNamespace(name="images", shape=[1, 3, 100, 200])]
        session.get_modelmeta.return_value = SimpleNamespace(custom_metadata_map={"names": "{0: 'start', 1: 'reward'}"})
        session.run.return_value = [np.array([[[20, 10, 40, 30, .9, 1], [0, 0, 10, 10, .8, 0]]], np.float32)]
        with patch("onnxruntime.InferenceSession", return_value=session):
            detector = YoloDetector(Path("model.onnx"))
        results = detector.detect(np.zeros((100, 200, 3), np.uint8), "reward", 0.5)
        self.assertEqual([item.center for item in results], [(30, 20)])
        with self.assertRaisesRegex(ValueError, "没有类别"):
            detector.class_id("unknown")

    def test_adb_coordinates_use_capture_content_and_send_input(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        worker.last_window = {
            "hwnd": 1,
            "adb_capture_origin": (400, 300),
            "adb_content_rect": (0, 100, 800, 400),
            "adb_source_size": (1600, 800),
        }
        worker._emulator_capture_backend = {"adb": "adb.exe", "serial": "127.0.0.1:7555"}
        worker._last_capture_backend = "ADB"
        self.assertEqual(worker._adb_input_point(600, 500), (400, 200))
        with patch.object(worker, "_run_cancellable_command", return_value=SimpleNamespace(returncode=0)) as run:
            worker._mouse_action("click", 600, 500)
            self.assertEqual(
                run.call_args.args[0],
                ["adb.exe", "-s", "127.0.0.1:7555", "shell", "input", "tap", "400", "200"],
            )
        with self.assertRaisesRegex(app.AutomationError, "画面之外"):
            worker._adb_input_point(600, 350)

    def test_yolo_condition_and_step_round_trip(self) -> None:
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(
                app, "QSettings",
                side_effect=lambda *_args: QSettings(str(Path(temp) / "draft.ini"), QSettings.IniFormat),
            ):
                window = app.MainWindow()
                try:
                    step = app.default_step("window_click_yolo")
                    step.update({"model": "game.onnx", "target_class": "button", "offset_x": 4})
                    normalized = window._normalize_step(step)
                    self.assertEqual(normalized["model"], "game.onnx")
                    self.assertEqual(normalized["offset_x"], 4)
                    task = app.default_window_task()
                    task["steps"] = [step]
                    task["flow"] = app.flow_from_steps([step])
                    task["flow"]["nodes"].insert(1, {
                        "id": "condition-test", "type": "condition", "label": "",
                        "operator": "and", "negate": False, "x": 0, "y": 0,
                        "conditions": [{
                            "type": "yolo_exists", "model": "game.onnx",
                            "target_class": "button", "confidence": 0.5, "timeout": 1.0,
                        }],
                    })
                    normalized_task = window._normalize_window_task(task, 1)
                    condition = next(node for node in normalized_task["flow"]["nodes"] if node["type"] == "condition")
                    self.assertEqual(condition["conditions"][0]["model"], "game.onnx")
                    self.assertEqual(condition["conditions"][0]["type"], "yolo_exists")

                    window.flow_canvas.add_condition_node(connect_before_end=False)
                    selected = window._selected_flow_node()
                    self.assertIsNotNone(selected)
                    window.condition_type_box.setCurrentIndex(window.condition_type_box.findData("yolo_exists"))
                    window.condition_model_edit.setText("game.onnx")
                    window.condition_class_edit.setText("button")
                    self.assertEqual(selected["conditions"][0]["model"], "game.onnx")
                    self.assertFalse(window.condition_image_edit.isVisibleTo(window.condition_widget))
                finally:
                    window._autosave_timer.stop()
                    window.deleteLater()
        del application

    def test_export_copies_relative_yolo_model(self) -> None:
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "game.onnx").write_bytes(b"model")
            with patch.object(
                app, "QSettings",
                side_effect=lambda *_args: QSettings(str(root / "draft.ini"), QSettings.IniFormat),
            ):
                window = app.MainWindow()
                try:
                    window.current_file = root / "source.json"
                    task = app.default_window_task()
                    task["steps"] = [app.default_step("window_click_yolo")]
                    task["steps"][0]["model"] = "game.onnx"
                    task["flow"] = app.flow_from_steps(task["steps"])
                    copies = window._export_asset_copies(root / "export" / "script.json", [task])
                    self.assertEqual(copies, [(root.resolve() / "game.onnx", root.resolve() / "export" / "game.onnx")])
                finally:
                    window._autosave_timer.stop()
                    window.deleteLater()
        del application

    def test_worker_detects_and_clicks_without_real_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "game.onnx"
            path.write_bytes(b"test")
            worker = app.ScriptWorker([], Path(temp))
            worker.last_window = {"hwnd": 1}
            worker._capture_window = Mock(return_value=(None, np.zeros((100, 100, 3), np.uint8), (400, 500)))
            worker._mouse_action = Mock()
            detector = Mock(names={0: "button"})
            detector.detect.return_value = [SimpleNamespace(center=(20, 30), name="button", score=.9)]
            worker._yolo_models[path.resolve()] = detector
            worker.execute_step({
                "type": "window_click_yolo", "model": "game.onnx", "target_class": "button",
                "confidence": .5, "timeout": 1, "offset_x": 5, "offset_y": -2,
            })
            worker._mouse_action.assert_called_once_with("click", 425, 528)


if __name__ == "__main__":
    unittest.main()
