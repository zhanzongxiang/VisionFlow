from __future__ import annotations

import ctypes
import os
import unittest
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app import AutomationError, ScriptWorker


class FakeUser32:
    def __init__(self) -> None:
        self.root_origin = (124, 232)
        self.child_origin = (154, 282)
        self.iconic: set[int] = set()
        self.hidden: set[int] = set()

    def IsWindow(self, hwnd: int) -> bool:
        return hwnd in {1, 2, 99}

    def IsIconic(self, hwnd: int) -> bool:
        return hwnd in self.iconic

    def IsWindowVisible(self, hwnd: int) -> bool:
        return hwnd not in self.hidden

    def ClientToScreen(self, hwnd: int, ptr: object) -> bool:
        ptr._obj.x, ptr._obj.y = self.root_origin if hwnd == 1 else self.child_origin
        return True

    def GetClientRect(self, hwnd: int, ptr: object) -> bool:
        ptr._obj.left = ptr._obj.top = 0
        ptr._obj.right = 600
        ptr._obj.bottom = 400
        return True

    def VkKeyScanW(self, value: str) -> int:
        return (0x100 if value.isupper() else 0) | ord(value.upper())


class WorkerInputRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worker = ScriptWorker([], Path(__file__).parent)
        self.worker.last_window = {
            "hwnd": 1,
            "input_hwnd": 2,
            "input_chain": [1, 2],
            "x": 10,
            "y": 20,
            "normal_x": 400,
            "normal_y": 500,
            "client_offset_x": 8,
            "client_offset_y": 30,
            "capture_width": 600,
            "capture_height": 400,
        }
        self.user32 = FakeUser32()
        self.worker._background_hwnd = lambda: (ctypes, self.user32, 1)
        self.worker._background_input_hwnd = lambda: 2
        self.worker._background_input_handles = lambda: [1, 2]

    def test_client_point_follows_live_window_and_child_origin(self) -> None:
        self.assertEqual(self.worker._background_client_point(178, 305), (24, 23))
        self.user32.root_origin = (500, 600)
        self.user32.child_origin = (530, 650)
        self.assertEqual(self.worker._background_client_point(554, 673), (24, 23))
        self.worker._background_input_hwnd = lambda: 1
        self.assertEqual(self.worker._background_client_point(554, 673), (54, 73))

    def test_client_point_uses_normal_origin_when_root_or_renderer_minimized(self) -> None:
        self.user32.iconic.add(1)
        self.user32.root_origin = (-32000, -32000)
        self.user32.child_origin = (-31970, -31950)
        self.assertEqual(self.worker._background_client_point(478, 600), (40, 20))
        self.user32.iconic.clear()
        self.user32.hidden.add(2)
        self.assertEqual(self.worker._background_client_point(478, 600), (40, 20))
        self.user32.hidden.clear()
        self.worker._emulator_capture_backend = {"main_hwnd": 99}
        self.user32.iconic.add(99)
        self.assertEqual(self.worker._background_client_point(478, 600), (40, 20))

    def test_click_and_drag_release_every_pressed_window_when_stopped(self) -> None:
        self.worker._background_client_point = Mock(return_value=(6, 7))
        self.worker._post_background_mouse_move = Mock()
        sent: list[tuple[int, int]] = []
        self.worker._send_background_message = lambda message, _wparam, _lparam, hwnd: sent.append((message, hwnd))

        def stop(_seconds: float) -> None:
            self.worker.stop()
            self.worker._check_stopped()

        self.worker._sleep = stop
        with self.assertRaisesRegex(AutomationError, "用户已停止"):
            self.worker._post_background_mouse_action("click", 30, 40)
        self.assertEqual(sent[-4:], [(0x0201, 1), (0x0201, 2), (0x0202, 2), (0x0202, 1)])

        self.worker.stop_event.clear()
        sent.clear()
        with self.assertRaisesRegex(AutomationError, "用户已停止"):
            self.worker._post_background_drag(30, 40, 50, 60, 0.05)
        self.assertEqual(sent[-4:], [(0x0201, 1), (0x0201, 2), (0x0202, 2), (0x0202, 1)])

    def test_key_release_runs_when_stop_interrupts_pause(self) -> None:
        sent: list[tuple[int, int, int]] = []
        self.worker._post_background_message = lambda message, code, _lparam, hwnd: sent.append((message, code, hwnd))

        def stop(_seconds: float) -> None:
            self.worker.stop()
            self.worker._check_stopped()

        self.worker._sleep = stop
        with self.assertRaisesRegex(AutomationError, "用户已停止"):
            self.worker._post_background_key("A")
        self.assertEqual(sent, [(0x0100, 0x41, 2), (0x0101, 0x41, 2)])

    def test_macro_releases_mouse_and_keyboard_on_stop(self) -> None:
        posted: list[tuple[int, int, int]] = []
        self.worker._post_background_message = lambda message, wparam, _lparam, hwnd: posted.append((message, wparam, hwnd))
        self.worker._send_background_message = Mock()
        self.worker._background_client_point = Mock(return_value=(6, 7))
        self.worker._post_background_mouse_move = Mock()
        calls = 0

        def stop_before_third_event(_seconds: float) -> None:
            nonlocal calls
            calls += 1
            if calls == 3:
                self.worker.stop()
                self.worker._check_stopped()

        self.worker._sleep = stop_before_third_event
        events = [
            {"type": "mouse_down", "button": "left", "x": 10, "y": 20},
            {"type": "key_down", "key": "A", "key_kind": "char"},
            {"type": "mouse_move", "x": 15, "y": 25},
        ]
        with self.assertRaisesRegex(AutomationError, "用户已停止"):
            self.worker._run_macro_background({"events": events})
        self.assertEqual(posted, [
            (0x0201, 0x0001, 1), (0x0201, 0x0001, 2),
            (0x0100, 0x41, 2), (0x0101, 0x41, 2),
            (0x0202, 0, 2), (0x0202, 0, 1),
        ])

    def test_macro_replays_recorded_shift_and_pressed_mouse_movement(self) -> None:
        posted: list[tuple[int, int]] = []
        moved: list[tuple[int, int, int]] = []
        self.worker._post_background_message = lambda message, wparam, _lparam, _hwnd: posted.append((message, wparam))
        self.worker._send_background_message = Mock()
        self.worker._background_client_point = Mock(return_value=(6, 7))
        self.worker._post_background_mouse_move = lambda x, y, buttons=0: moved.append((x, y, buttons))
        self.worker._sleep = lambda _seconds: None
        events = [
            {"type": "mouse_down", "button": "left", "x": 10, "y": 20},
            {"type": "mouse_move", "x": 11, "y": 21},
            {"type": "mouse_up", "button": "left", "x": 11, "y": 21},
            {"type": "key_down", "key": "shift", "key_kind": "special"},
            {"type": "key_down", "key": "A", "key_kind": "char"},
            {"type": "key_up", "key": "A", "key_kind": "char"},
            {"type": "key_up", "key": "shift", "key_kind": "special"},
        ]
        self.worker._run_macro_background({"events": events})
        self.assertEqual(moved, [(11, 21, 1)])
        self.assertEqual(posted[-4:], [(0x0100, 0x10), (0x0100, 0x41), (0x0101, 0x41), (0x0101, 0x10)])
        self.assertEqual([message for message, _ in posted].count(0x0202), 2)

    def test_macro_side_button_keeps_xbutton_id_on_down_and_up(self) -> None:
        posted: list[tuple[int, int, int]] = []
        self.worker._post_background_message = lambda message, wparam, _lparam, hwnd: posted.append((message, wparam, hwnd))
        self.worker._send_background_message = Mock()
        self.worker._background_client_point = Mock(return_value=(6, 7))
        self.worker._sleep = lambda _seconds: None
        self.worker._run_macro_background({"events": [
            {"type": "mouse_down", "button": "xbutton2", "x": 10, "y": 20},
            {"type": "mouse_up", "button": "xbutton2", "x": 10, "y": 20},
        ]})
        self.assertEqual(posted, [
            (0x020B, (2 << 16) | 0x0040, 1),
            (0x020B, (2 << 16) | 0x0040, 2),
            (0x020C, 2 << 16, 2),
            (0x020C, 2 << 16, 1),
        ])

    def test_scroll_uses_screen_point_not_window_client_point(self) -> None:
        sent: list[tuple[int, int, int, int]] = []
        self.worker._post_background_message = lambda *args: sent.append(args)
        self.worker._background_client_point = Mock(side_effect=AssertionError("scroll must keep screen coordinates"))
        self.worker._post_background_scroll(-5, 200, 1, -2)
        point = self.worker._pack_point(-5, 200)
        self.assertEqual(sent, [
            (0x020A, ((-240 & 0xFFFF) << 16), point, 2),
            (0x020E, ((120 & 0xFFFF) << 16), point, 2),
        ])

    def test_special_letters_and_numbers_are_accepted(self) -> None:
        self.assertEqual(self.worker._background_key_code("A"), 0x41)
        self.assertEqual(self.worker._background_key_code("z"), 0x5A)
        self.assertEqual(self.worker._background_key_code("9"), 0x39)
        self.assertEqual(self.worker._background_key_code("enter"), 0x0D)
        self.assertEqual(self.worker._background_key_code("A", "char"), 0x41)


if __name__ == "__main__":
    unittest.main()
