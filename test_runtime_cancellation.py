from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

import app


class RuntimeCancellationTests(unittest.TestCase):
    def test_stop_during_yolo_capture_or_inference_prevents_click(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "game.onnx"
            model.touch()
            for stage in ("capture", "inference"):
                with self.subTest(stage=stage):
                    worker = app.ScriptWorker([], Path(folder))
                    detector = Mock(names={0: "button"})
                    hits = [SimpleNamespace(center=(10, 20), name="button", score=.9)]
                    detector.detect.return_value = hits
                    frame = (None, np.zeros((30, 40, 3), np.uint8), (0, 0))

                    def cancel_capture():
                        worker.stop()
                        return frame

                    def cancel_detect(*_args):
                        worker.stop()
                        return hits

                    worker._capture_window = Mock(return_value=frame)
                    if stage == "capture":
                        worker._capture_window.side_effect = cancel_capture
                    else:
                        detector.detect.side_effect = cancel_detect
                    worker._yolo_models[model.resolve()] = detector
                    worker._mouse_action = Mock()
                    with self.assertRaisesRegex(app.AutomationError, "用户已停止"):
                        worker.execute_step({
                            "type": "window_click_yolo", "model": str(model),
                            "target_class": "button", "timeout": 1,
                        })
                    worker._mouse_action.assert_not_called()
                    if stage == "capture":
                        detector.detect.assert_not_called()

    def test_stop_after_template_recognition_prevents_dispatch(self) -> None:
        for step_type, method in (
            ("click_image", "_wait_for_image"),
            ("window_click_image", "_wait_for_window_image"),
        ):
            with self.subTest(step=step_type):
                worker = app.ScriptWorker([], Path.cwd())

                def cancel_and_match(_step):
                    worker.stop()
                    return (10, 20)

                setattr(worker, method, cancel_and_match)
                worker._mouse_action = Mock()
                with self.assertRaisesRegex(app.AutomationError, "用户已停止"):
                    worker.execute_step({"type": step_type})
                worker._mouse_action.assert_not_called()

    def test_stopped_worker_never_starts_input_or_zero_sleep(self) -> None:
        worker = app.ScriptWorker([], Path.cwd())
        worker.stop()
        for method, args in (
            ("_mouse_action", ("click", 1, 2)),
            ("_drag", (1, 2, 3, 4, .1)),
            ("_press_key", ("ENTER",)),
            ("_type_text", ("abc",)),
            ("_post_background_mouse_action", ("click", 1, 2)),
            ("_post_background_drag", (1, 2, 3, 4, .1)),
            ("_post_background_key", ("ENTER",)),
            ("_sleep", (0,)),
        ):
            with self.subTest(method=method):
                with self.assertRaisesRegex(app.AutomationError, "用户已停止"):
                    getattr(worker, method)(*args)
        with patch.object(app.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(app.AutomationError, "用户已停止"):
                worker._run_cancellable_command(["unused.exe"], timeout=1)
            popen.assert_not_called()

    def test_command_cancellation_reaps_real_child(self) -> None:
        worker = app.ScriptWorker([], Path.cwd())
        processes = []
        real_popen = subprocess.Popen
        timer = threading.Timer(.2, worker.stop)
        self.addCleanup(timer.join)
        self.addCleanup(timer.cancel)

        def start(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            timer.start()
            return process

        started = time.monotonic()
        with patch.object(app.subprocess, "Popen", side_effect=start):
            with self.assertRaisesRegex(app.AutomationError, "用户已停止"):
                worker._run_cancellable_command(
                    [sys.executable, "-c", "import time; time.sleep(30)"], timeout=60,
                )
        self.assertLess(time.monotonic() - started, 3)
        self.assertIsNotNone(processes[0].poll())

    def test_command_timeout_reaps_child_and_preserves_success_output(self) -> None:
        worker = app.ScriptWorker([], Path.cwd())
        processes = []
        real_popen = subprocess.Popen

        def start(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        with patch.object(app.subprocess, "Popen", side_effect=start):
            with self.assertRaises(subprocess.TimeoutExpired):
                worker._run_cancellable_command(
                    [sys.executable, "-c", "import time; time.sleep(30)"], timeout=.2,
                )
        self.assertIsNotNone(processes[0].poll())
        result = worker._run_cancellable_command(
            [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)"],
            timeout=5,
        )
        self.assertEqual(result.returncode, 7)
        self.assertIn(b"out", result.stdout)
        self.assertIn(b"err", result.stderr)

    def test_adb_capture_skips_printwindow_even_if_adb_fails(self) -> None:
        user32, gdi32 = Mock(), Mock()
        user32.IsWindow.return_value = True
        user32.IsIconic.return_value = False
        user32.IsWindowVisible.return_value = True

        def client_rect(_hwnd, pointer):
            pointer._obj.right, pointer._obj.bottom = 64, 32
            return True

        def client_origin(_hwnd, pointer):
            pointer._obj.x, pointer._obj.y = 100, 200
            return True

        user32.GetClientRect.side_effect = client_rect
        user32.ClientToScreen.side_effect = client_origin
        frame = np.random.default_rng(1).integers(0, 256, (32, 64, 3), dtype=np.uint8)
        worker = app.ScriptWorker([], Path.cwd())
        worker.last_window = {"hwnd": 123}
        worker._resolve_emulator_capture_backend = Mock(return_value={"kind": "adb"})
        worker._background_input_hwnd = Mock(return_value=123)
        worker._capture_emulator_frame = Mock(return_value=frame)
        with patch("ctypes.WinDLL", side_effect=lambda name, **_: user32 if name == "user32" else gdi32):
            _, captured, origin = worker._capture_window()
            self.assertIs(captured, frame)
            self.assertEqual(origin, (100, 200))
            self.assertEqual(worker.last_window["adb_capture_origin"], origin)
            worker._capture_emulator_frame.return_value = None
            with self.assertRaisesRegex(app.AutomationError, "ADB"):
                worker._capture_window()
        user32.PrintWindow.assert_not_called()
        user32.GetDC.assert_not_called()


class OptimizedSmokeTests(unittest.TestCase):
    def test_optimized_smoke_executes_both_matchers_and_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            for matcher, message in (
                ("_wait_for_image", "Screen image match"),
                ("_wait_for_window_image", "Window image match"),
            ):
                with self.subTest(matcher=matcher):
                    report = Path(folder) / f"{matcher}.txt"
                    program = (
                        "from unittest.mock import patch\n"
                        "import app, packaging_smoke\n"
                        f"with patch.object(app.ScriptWorker, {matcher!r}, return_value=(0, 0)):\n"
                        "    raise SystemExit(packaging_smoke.main())\n"
                    )
                    result = subprocess.run(
                        [sys.executable, "-O", "-c", program, str(report)],
                        cwd=Path(__file__).parent, capture_output=True, timeout=30,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    self.assertEqual(result.returncode, 1, result.stderr.decode(errors="replace"))
                    text = report.read_text(encoding="utf-8")
                    self.assertIn(message, text)
                    self.assertIn("FAIL", text)
                    self.assertNotIn("PASS", text)


if __name__ == "__main__":
    unittest.main()
