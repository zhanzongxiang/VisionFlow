from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

import app


class VisualRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_uniform_template_requires_matching_pixels(self) -> None:
        template = np.full((8, 12, 3), (20, 130, 225), dtype=np.uint8)
        frame = np.full((40, 45, 3), (225, 20, 130), dtype=np.uint8)

        score, _location = app.match_template(cv2, frame, template)
        self.assertLess(score, 0.85)

        frame[15:23, 9:21] = template
        score, location = app.match_template(cv2, frame, template)
        self.assertGreater(score, 0.99)
        self.assertEqual(location, (9, 15))

    def test_textured_template_still_matches(self) -> None:
        template = np.random.default_rng(42).integers(0, 256, (9, 13, 3), dtype=np.uint8)
        frame = np.zeros((35, 40, 3), dtype=np.uint8)
        frame[11:20, 17:30] = template

        score, location = app.match_template(cv2, frame, template)
        self.assertGreater(score, 0.99)
        self.assertEqual(location, (17, 11))

    def test_condition_uses_pixel_score_for_uniform_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "template.png"
            path.touch()
            worker = app.ScriptWorker([], Path(directory))
            worker.last_window = {"hwnd": 1}
            template = np.full((7, 9, 3), (30, 40, 50), dtype=np.uint8)
            frame = np.zeros((25, 30, 3), dtype=np.uint8)
            worker._read_color_image = Mock(return_value=(cv2, template))
            worker._capture_window = Mock(return_value=(cv2, frame, (0, 0)))
            worker._sleep = lambda _seconds: None
            condition = {"image": str(path), "confidence": 0.85, "timeout": 0.01}

            self.assertFalse(worker._condition_image_exists(condition))
            frame[4:11, 5:14] = template
            self.assertTrue(worker._condition_image_exists(condition))

    def test_condition_and_or_not_evaluate_as_configured(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        worker._condition_image_exists = Mock(side_effect=lambda item: item["found"])
        conditions = [{"found": True}, {"found": False}]

        self.assertFalse(worker._evaluate_condition({"operator": "and", "conditions": conditions}))
        self.assertTrue(worker._evaluate_condition({"operator": "or", "conditions": conditions}))
        self.assertTrue(worker._evaluate_condition({"operator": "and", "negate": True, "conditions": conditions}))

    def test_auto_layout_preserves_selected_node_for_property_editing(self) -> None:
        canvas = app.FlowCanvas()
        canvas.set_flow(app.flow_from_steps([app.default_step("wait")]))
        action_id = next(
            str(node["id"]) for node in canvas.flow["nodes"] if node["type"] == "action"
        )
        selected = []
        canvas.node_selected.connect(selected.append)
        canvas.node_items[action_id].setSelected(True)
        canvas.auto_layout()

        self.assertTrue(canvas.node_items[action_id].isSelected())
        self.assertEqual(selected[-1]["id"], action_id)
        self.assertIs(selected[-1], canvas.node_items[action_id].node)
        self.assertIs(canvas.node_items[action_id].node, next(
            node for node in canvas.flow["nodes"] if node["id"] == action_id
        ))
        canvas.deleteLater()

    def test_deleting_selected_condition_clears_stale_properties(self) -> None:
        canvas = app.FlowCanvas()
        canvas.set_flow(app.flow_from_steps([app.default_step("wait")]))
        canvas.add_condition_node(connect_before_end=False)
        condition_id = next(
            str(node["id"]) for node in canvas.flow["nodes"] if node["type"] == "condition"
        )
        selected = []
        canvas.node_selected.connect(selected.append)
        canvas.node_items[condition_id].setSelected(True)

        canvas.delete_selected()

        self.assertNotIn(condition_id, canvas.node_items)
        self.assertIsNone(selected[-1])
        canvas.deleteLater()

    def test_condition_property_edits_after_auto_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "draft.ini"
            with patch.object(
                app, "QSettings", side_effect=lambda *_args: QSettings(str(settings_path), QSettings.IniFormat)
            ):
                window = app.MainWindow()
                window.flow_canvas.add_condition_node(connect_before_end=False)
                condition_id = next(
                    str(node["id"]) for node in window.flow_canvas.flow["nodes"]
                    if node["type"] == "condition"
                )
                window.flow_canvas.auto_layout()
                window.node_name_edit.setText("重新排列后可编辑")

                condition = next(
                    node for node in window.flow_canvas.flow["nodes"] if node["id"] == condition_id
                )
                self.assertEqual(condition["label"], "重新排列后可编辑")
                self.assertIs(window._selected_flow_node(), window.flow_canvas.node_items[condition_id].node)
                window._autosave_timer.stop()
                window.deleteLater()

    def test_window_capture_uses_current_client_origin_after_window_moves(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        worker.background_input = False
        worker.last_window = {
            "hwnd": 123, "x": 10, "y": 20, "client_offset_x": 7, "client_offset_y": 10,
        }
        user32 = Mock()
        gdi32 = Mock()
        user32.IsWindow.return_value = True
        user32.IsIconic.return_value = False
        user32.GetDC.return_value = 1
        user32.PrintWindow.return_value = True
        gdi32.CreateCompatibleDC.return_value = 2
        gdi32.CreateCompatibleBitmap.return_value = 3
        gdi32.SelectObject.return_value = 4

        def client_rect(_hwnd, pointer):
            pointer._obj.right = 64
            pointer._obj.bottom = 32
            return True

        def client_to_screen(_hwnd, pointer):
            pointer._obj.x = 257
            pointer._obj.y = 310
            return True

        user32.GetClientRect.side_effect = client_rect
        user32.ClientToScreen.side_effect = client_to_screen
        gdi32.GetDIBits.return_value = 32
        with patch("ctypes.WinDLL", side_effect=lambda name, **_kwargs: user32 if name == "user32" else gdi32):
            _cv2, frame, origin = worker._capture_window()

        self.assertEqual(frame.shape, (32, 64, 3))
        self.assertEqual(origin, (257, 310))
        self.assertNotEqual(origin, (17, 30))


if __name__ == "__main__":
    unittest.main()
