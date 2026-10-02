from __future__ import annotations

import os
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np

import app


class ImageRecognitionResilienceTests(unittest.TestCase):
    @staticmethod
    def _pattern(width: int = 50, height: int = 40) -> np.ndarray:
        rng = np.random.default_rng(321)
        return rng.integers(0, 256, (height, width, 3), dtype=np.uint8)

    def test_find_template_match_handles_ten_percent_scale_changes(self) -> None:
        template = self._pattern()
        expected_location = (37, 29)

        for expected_scale in (0.9, 1.1):
            with self.subTest(scale=expected_scale):
                expected_size = (
                    round(template.shape[1] * expected_scale),
                    round(template.shape[0] * expected_scale),
                )
                interpolation = cv2.INTER_AREA if expected_scale < 1.0 else cv2.INTER_CUBIC
                rendered = cv2.resize(template, expected_size, interpolation=interpolation)
                frame = np.full((120, 160, 3), 17, dtype=np.uint8)
                x, y = expected_location
                width, height = expected_size
                frame[y : y + height, x : x + width] = rendered

                match = app.find_template_match(cv2, frame, template)

                self.assertGreater(match.score, 0.99)
                self.assertEqual(match.location, expected_location)
                self.assertEqual(match.size, expected_size)
                self.assertAlmostEqual(match.scale, expected_scale)

    def test_pixel_similarity_rejects_overlay_that_preserves_correlation(self) -> None:
        template = self._pattern(width=24, height=18)
        frame = np.zeros((60, 80, 3), dtype=np.uint8)
        frame[17:35, 23:47] = template
        match = app.find_template_match(cv2, frame, template)
        self.assertEqual(match.location, (23, 17))
        self.assertAlmostEqual(app.template_pixel_similarity(cv2, frame, template, match), 1.0)

        covered = frame.copy()
        covered[17:35, 23:47] = (template.astype(np.float32) * 0.35 + 145).astype(np.uint8)
        covered_match = app.find_template_match(cv2, covered, template)
        self.assertGreater(covered_match.score, 0.99)
        self.assertLess(app.template_pixel_similarity(cv2, covered, template, covered_match), 0.9)

    def test_click_step_rechecks_color_after_wait_step(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        template = self._pattern(width=24, height=18)
        clear = np.zeros((60, 80, 3), dtype=np.uint8)
        clear[17:35, 23:47] = template
        covered = clear.copy()
        covered[17:35, 23:47] = (template.astype(np.float32) * 0.35 + 145).astype(np.uint8)
        worker._resolve_input_path = Mock(return_value=Path(__file__))
        worker._read_color_image = Mock(return_value=(cv2, template))
        worker._capture_window = Mock(side_effect=[
            (cv2, clear, (100, 200)),
            (cv2, covered, (100, 200)),
            (cv2, clear, (100, 200)),
        ])
        worker._sleep = Mock()
        worker._mouse_action = Mock()
        step = {
            "image": "button.png", "confidence": 0.95, "pixel_similarity": 0.9,
            "timeout": 0.5,
        }

        worker.execute_step({"type": "window_wait_image", **step})
        worker._mouse_action.assert_not_called()
        worker.execute_step({"type": "window_click_image", **step})

        self.assertEqual(worker._capture_window.call_count, 3)
        worker._mouse_action.assert_called_once_with("click", 135, 226)

    def test_click_step_times_out_without_clicking_when_only_overlay_exists(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        template = self._pattern(width=24, height=18)
        covered = np.zeros((60, 80, 3), dtype=np.uint8)
        covered[17:35, 23:47] = (template.astype(np.float32) * 0.35 + 145).astype(np.uint8)
        worker._resolve_input_path = Mock(return_value=Path(__file__))
        worker._read_color_image = Mock(return_value=(cv2, template))
        worker._capture_window = Mock(return_value=(cv2, covered, (100, 200)))
        worker._sleep = Mock()
        worker._mouse_action = Mock()
        worker._save_recognition_failure_frame = Mock(return_value=None)
        ticks = iter(index * 0.01 for index in range(100))

        with patch.object(app.time, "monotonic", side_effect=lambda: next(ticks)):
            with self.assertRaisesRegex(app.AutomationError, "窗口内图片超时"):
                worker.execute_step({
                    "type": "window_click_image", "image": "button.png",
                    "confidence": 0.95, "pixel_similarity": 0.9, "timeout": 0.1,
                })

        worker._mouse_action.assert_not_called()

    def test_fit_frame_to_size_preserves_aspect_ratio_and_reports_content(self) -> None:
        source = np.full((40, 80, 3), (20, 160, 220), dtype=np.uint8)

        fitted, content_rect = app.fit_frame_to_size(cv2, source, 100, 100)

        self.assertEqual(fitted.shape, (100, 100, 3))
        self.assertEqual(content_rect, (0, 25, 100, 50))
        self.assertTrue(np.all(fitted[:25] == 0))
        self.assertTrue(np.all(fitted[75:] == 0))
        self.assertTrue(np.all(fitted[25:75] == (20, 160, 220)))

    def test_window_image_wait_retries_a_transient_capture_error(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        template = self._pattern(width=20, height=16)
        frame = np.zeros((60, 80, 3), dtype=np.uint8)
        frame[17:33, 23:43] = template
        logs: list[str] = []
        worker.log.connect(logs.append)
        worker._resolve_input_path = Mock(return_value=Path(__file__))
        worker._read_color_image = Mock(return_value=(cv2, template))
        worker._capture_window = Mock(
            side_effect=[
                app.AutomationError("临时截图失败"),
                (cv2, frame, (100, 200)),
            ]
        )
        worker._sleep = Mock()

        point = worker._wait_for_window_image(
            {"image": "template.png", "timeout": 0.5, "confidence": 0.95}
        )

        self.assertEqual(point, (133, 225))
        self.assertEqual(worker._capture_window.call_count, 2)
        self.assertIn("临时截图失败", "\n".join(logs))

    def test_condition_image_retries_a_transient_capture_error(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        worker.last_window = {"hwnd": 1}
        template = self._pattern(width=20, height=16)
        frame = np.zeros((60, 80, 3), dtype=np.uint8)
        frame[17:33, 23:43] = template
        worker._resolve_input_path = Mock(return_value=Path(__file__))
        worker._read_color_image = Mock(return_value=(cv2, template))
        worker._capture_window = Mock(
            side_effect=[
                app.AutomationError("临时截图失败"),
                (cv2, frame, (100, 200)),
            ]
        )
        worker._sleep = Mock()

        found = worker._condition_image_exists(
            {"image": "template.png", "timeout": 0.5, "confidence": 0.95}
        )

        self.assertTrue(found)
        self.assertEqual(worker._capture_window.call_count, 2)

    def test_emulator_backend_resolver_rescans_after_retry_deadline(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        worker.last_window = {
            "title": "MuMu Player",
            "process_name": "MuMuPlayer.exe",
            "hwnd": 0,
        }
        current_time = {"value": 0.0}
        moments = iter((100.0, 100.0, 102.0, 104.0))

        def monotonic() -> float:
            current_time["value"] = next(moments)
            return current_time["value"]

        def is_file(path: Path) -> bool:
            if current_time["value"] < 104.0:
                return False
            return path.name in {"MuMuManager.exe", "MuMuManagerGlobal.exe", "adb.exe"}

        manager_output = {
            "0": {
                "is_android_started": True,
                "main_wnd": "",
                "render_wnd": "",
                "adb_host_ip": "127.0.0.1",
                "adb_port": 7555,
                "index": 0,
                "name": "Test VM",
                "android_version": "12",
                "pid": 0,
            }
        }
        completed = SimpleNamespace(
            stdout=json.dumps(manager_output).encode("utf-8"),
            stderr=b"",
            returncode=0,
        )

        with (
            patch.object(app.time, "monotonic", side_effect=monotonic),
            patch.object(Path, "is_file", autospec=True, side_effect=is_file),
            patch.object(worker, "_run_cancellable_command", return_value=completed) as run,
        ):
            self.assertIsNone(worker._resolve_emulator_capture_backend())
            self.assertEqual(worker._emulator_capture_retry_at, 103.0)
            self.assertIsNone(worker._resolve_emulator_capture_backend())
            run.assert_not_called()

            backend = worker._resolve_emulator_capture_backend()

        self.assertIsNotNone(backend)
        self.assertEqual(backend["serial"], "127.0.0.1:7555")
        self.assertEqual(worker._emulator_capture_retry_at, 0.0)
        run.assert_called_once()

    def test_window_image_timeout_logs_capture_failure_diagnostics(self) -> None:
        worker = app.ScriptWorker([], Path(__file__).parent)
        template = self._pattern(width=20, height=16)
        logs: list[str] = []
        worker.log.connect(logs.append)
        worker._resolve_input_path = Mock(return_value=Path(__file__))
        worker._read_color_image = Mock(return_value=(cv2, template))
        worker._capture_window = Mock(side_effect=app.AutomationError("临时截图失败"))
        worker._sleep = Mock()

        ticks = iter(index * 0.01 for index in range(1000))
        with patch.object(app.time, "monotonic", side_effect=lambda: next(ticks)):
            with self.assertRaisesRegex(app.AutomationError, "窗口内图片超时"):
                worker._wait_for_window_image(
                    {"image": "template.png", "timeout": 0.2, "confidence": 0.95}
                )

        diagnostic = next(line for line in reversed(logs) if "窗口内图片未识别" in line)
        self.assertRegex(diagnostic, r"截图失败\s*\d+\s*次")
        self.assertIn("临时截图失败", diagnostic)
        self.assertGreater(worker._capture_window.call_count, 1)


if __name__ == "__main__":
    unittest.main()
