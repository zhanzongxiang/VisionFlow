from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

import app
from capture_collection import CaptureSession, CollectionPage, CollectionThread, game_folder


WINDOW = {"hwnd": 42, "title": "Test Game", "process_name": "game.exe"}


class FakeCaptureWorker:
    instances = []

    def __init__(self, *_args):
        self.instances.append(self)
        self.calls = 0
        self._last_capture_backend = "Test"
        self._resolve_background_input_handle = Mock()
        self._resolve_emulator_capture_backend = Mock()
        self._mouse_action = Mock(side_effect=AssertionError("must never send input"))
        self._press_key = Mock(side_effect=AssertionError("must never send input"))

    @staticmethod
    def _enumerate_windows(**_kwargs):
        return [dict(WINDOW)]

    def _capture_window(self):
        self.calls += 1
        return cv2, np.full((30, 40, 3), self.calls % 255, np.uint8), (12, 24)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = CaptureSession(self.root, "测试游戏", WINDOW, 1, 10, True)
        self.frame = np.full((30, 40, 3), (40, 170, 80), np.uint8)

    def save(self, frame=None, manual=False):
        return self.session.save(
            self.frame if frame is None else frame, manual=manual,
            backend="ADB", origin=(12, 24), captured_at="2026-09-29T12:00:00+08:00",
        )

    def test_saves_full_png_manifest_and_final_counts(self):
        record = self.save()
        self.session.finish("stopped", "done")
        output = self.session.directory / record["file"]
        decoded = cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        np.testing.assert_array_equal(decoded, self.frame)
        rows = (self.session.directory / "frames.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(rows[0]), record)
        metadata = json.loads((self.session.directory / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["saved"], 1)
        self.assertEqual(metadata["window"]["hwnd"], 42)
        self.assertEqual(record["width"], 40)
        self.assertEqual(record["backend"], "ADB")
        self.assertEqual(metadata["status"], "stopped")

    def test_exact_duplicates_skipped_but_manual_and_one_pixel_change_preserved(self):
        self.assertIsNotNone(self.save())
        self.assertIsNone(self.save())
        self.assertIsNotNone(self.save(manual=True))
        changed = self.frame.copy()
        changed[0, 0, 0] += 1
        self.assertIsNotNone(self.save(changed))
        self.assertEqual((self.session.saved, self.session.skipped), (3, 1))

    def test_equal_bytes_with_different_dimensions_not_duplicate(self):
        self.save()
        self.assertIsNotNone(self.save(self.frame.reshape(40, 30, 3)))

    def test_dedup_can_be_disabled(self):
        self.session.dedup = False
        self.save()
        self.assertIsNotNone(self.save())

    def test_manual_capture_still_obeys_limit(self):
        self.session.limit = 1
        self.save()
        with self.assertRaisesRegex(RuntimeError, "上限"):
            self.save(manual=True)

    def test_distinct_batches_and_sanitized_game_folder(self):
        other = CaptureSession(self.root, "测试游戏", WINDOW, 1, 10, True)
        self.assertNotEqual(other.directory, self.session.directory)
        self.assertEqual(game_folder("../Game:1"), "_Game_1")
        self.assertEqual(game_folder("CON"), "_CON")
        with self.assertRaises(ValueError):
            game_folder(" ... ")

    def test_encoding_failure_does_not_increment_count(self):
        with patch("capture_collection.cv2.imencode", return_value=(False, None)):
            with self.assertRaises(OSError):
                self.save()
        self.assertEqual(self.session.saved, 0)
        self.assertEqual(list(self.session.images.iterdir()), [])

    def test_manifest_error_rolls_back_new_png(self):
        original_open = Path.open

        def fail_manifest(path, *args, **kwargs):
            if path.name == "frames.jsonl":
                raise OSError("disk error")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", fail_manifest):
            with self.assertRaisesRegex(OSError, "disk error"):
                self.save()
        self.assertEqual(self.session.saved, 0)
        self.assertFalse(list(self.session.images.iterdir()))


class CollectionThreadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        FakeCaptureWorker.instances.clear()

    def thread(self, worker_type=FakeCaptureWorker, *, limit=1):
        return CollectionThread(worker_type, WINDOW, self.root, "Game", 0.2, limit, True)

    def test_limit_finishes_and_no_input_called(self):
        thread = self.thread(limit=2)
        results = []
        thread.result.connect(lambda ok, msg: results.append((ok, msg)))
        thread.run()
        worker = FakeCaptureWorker.instances[-1]
        worker._mouse_action.assert_not_called()
        worker._press_key.assert_not_called()
        self.assertEqual(worker.last_window["hwnd"], WINDOW["hwnd"])
        self.assertEqual(len(list(self.root.rglob("*.png"))), 2)
        metadata = json.loads(next(self.root.rglob("session.json")).read_text(encoding="utf-8"))
        self.assertEqual(metadata["status"], "limit_reached")
        self.assertTrue(results[0][0])

    def test_stale_window_stops_without_creating_batch(self):
        thread = self.thread()
        results = []
        thread.result.connect(lambda ok, msg: results.append((ok, msg)))
        with patch.object(FakeCaptureWorker, "_enumerate_windows", return_value=[]):
            thread.run()
        self.assertFalse(results[0][0])
        self.assertFalse(list(self.root.iterdir()))

    def test_stop_during_capture_does_not_save(self):
        class CancellingWorker(FakeCaptureWorker):
            def _capture_window(self):
                self.stop_event.set()
                return super()._capture_window()

        thread = self.thread(CancellingWorker)
        thread.run()
        self.assertFalse(list(self.root.rglob("*.png")))

    def test_retries_then_stops_after_three_capture_failures(self):
        thread = self.thread()
        results = []
        thread.result.connect(lambda ok, msg: results.append((ok, msg)))
        with patch.object(FakeCaptureWorker, "_capture_window", side_effect=RuntimeError("capture lost")) as capture:
            thread.run()
        self.assertEqual(capture.call_count, 3)
        self.assertFalse(results[0][0])
        self.assertIn("capture lost", results[0][1])

    def test_paused_worker_only_captures_on_manual_request(self):
        thread = self.thread(limit=10)
        thread.set_paused(True)
        thread.start()
        try:
            time.sleep(0.15)
            self.assertEqual(FakeCaptureWorker.instances[-1].calls, 0)
            thread.snapshot()
            deadline = time.monotonic() + 2
            while not list(self.root.rglob("*.png")) and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(len(list(self.root.rglob("*.png"))), 1)
            time.sleep(0.25)
            self.assertEqual(FakeCaptureWorker.instances[-1].calls, 1)
            thread.set_paused(False)
            deadline = time.monotonic() + 2
            while FakeCaptureWorker.instances[-1].calls < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertGreaterEqual(FakeCaptureWorker.instances[-1].calls, 2)
        finally:
            thread.stop()
            self.assertTrue(thread.wait(3000))

    def test_paused_manual_capture_retries_transient_failure(self):
        class TransientWorker(FakeCaptureWorker):
            def _capture_window(self):
                if self.calls == 0:
                    self.calls += 1
                    raise RuntimeError("temporary capture error")
                return super()._capture_window()

        thread = self.thread(TransientWorker)
        thread.set_paused(True)
        thread.snapshot()
        thread.start()
        try:
            self.assertTrue(thread.wait(2000))
            self.assertEqual(len(list(self.root.rglob("*.png"))), 1)
            record = json.loads(next(self.root.rglob("frames.jsonl")).read_text(encoding="utf-8"))
            self.assertTrue(record["manual"])
        finally:
            thread.stop()
            thread.wait(3000)


class CollectionPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = QSettings(str(self.root / "settings.ini"), QSettings.IniFormat)
        self.page = CollectionPage(FakeCaptureWorker, self.settings)
        self.page.hotkey_box.setCurrentText("关闭")
        self.page.game_edit.setText("Test Game")
        self.page.root_edit.setText(str(self.root / "captures"))
        self.page.refresh_windows()
        self.page.window_box.setCurrentIndex(1)

    def tearDown(self):
        self.page.stop()
        if self.page.thread:
            self.assertTrue(self.page.thread.wait(3000))
        self.application.processEvents()
        self.page.deleteLater()

    def wait_for_finished(self):
        deadline = time.monotonic() + 3
        while self.page.thread is not None and time.monotonic() < deadline:
            self.application.processEvents()
            time.sleep(0.01)
        self.assertIsNone(self.page.thread)

    def test_start_finish_preview_and_controls(self):
        self.page.limit_spin.setValue(1)
        self.page._start()
        self.assertFalse(self.page.start_button.isEnabled())
        self.assertFalse(self.page.window_box.isEnabled())
        self.wait_for_finished()
        self.assertTrue(self.page.start_button.isEnabled())
        self.assertFalse(self.page.stop_button.isEnabled())
        self.assertFalse(self.page.preview_pixmap.isNull())
        self.assertEqual(self.page.frame_list.count(), 1)
        self.assertIn("上限", self.page.state_label.text())
        self.assertTrue(self.page.folder_button.isEnabled())

    def test_missing_window_or_game_does_not_start(self):
        self.page.game_edit.clear()
        self.page._start()
        self.assertIsNone(self.page.thread)
        self.page.game_edit.setText("Game")
        self.page.window_box.setCurrentIndex(0)
        self.page._start()
        self.assertIsNone(self.page.thread)

    def test_global_hotkey_release_emits_snapshot_and_stops_listener(self):
        from pynput import keyboard

        self.page.hotkey_box.setCurrentText("F10")
        with patch.object(keyboard, "Listener") as listener_type:
            self.page._start_hotkey()
            callback = listener_type.call_args.kwargs["on_release"]
            received = []
            self.page.snapshot_requested.connect(lambda: received.append(True))
            callback(keyboard.Key.f9)
            self.assertFalse(received)
            callback(keyboard.Key.f10)
            self.assertEqual(received, [True])
            self.page._stop_hotkey()
            listener_type.return_value.stop.assert_called_once()

    def test_preview_resizes_with_panel_without_new_frame(self):
        self.page.resize(1000, 650)
        self.page.show()
        self.page.limit_spin.setValue(1)
        self.page._start()
        self.wait_for_finished()
        self.page.resize(700, 450)
        self.application.processEvents()
        self.assertLessEqual(self.page.preview.pixmap().width(), self.page.preview.width())
        self.assertLessEqual(self.page.preview.pixmap().height(), self.page.preview.height())
        self.page.hide()

    def test_main_navigation_and_close_wait_for_collection(self):
        with patch.object(app, "QSettings", return_value=self.settings):
            window = app.MainWindow()
        window._autosave_timer.stop()
        page = window.collection_page
        page.worker_type = FakeCaptureWorker
        page.hotkey_box.setCurrentText("关闭")
        page.root_edit.setText(str(self.root / "close-test"))
        page.game_edit.setText("Game")
        window.nav_collection_button.click()
        self.assertIs(window.main_tabs.currentWidget(), page)
        page.window_box.setCurrentIndex(1)
        page._start()
        thread = page.thread
        self.assertTrue(window._has_running_threads())
        with patch.object(window, "_confirm_discard", return_value=True):
            window.close()
        self.assertTrue(thread.cancel.is_set())
        self.assertTrue(thread.wait(3000))
        self.application.processEvents()
        window._close_timer.stop()
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
