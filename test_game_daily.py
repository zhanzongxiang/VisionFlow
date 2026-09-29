from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np

from game_daily import DailyRunner, ProfileError, VisualMatcher, load_profile


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeBackend:
    def __init__(self, states: list[int]):
        self.states = iter(states)
        self.last = 0
        self.clicks: list[tuple[int, int]] = []

    def capture(self):
        self.last = next(self.states, self.last)
        frame = np.zeros((80, 100, 3), dtype=np.uint8)
        frame[0, 0, 0] = self.last
        return frame, (200, 300)

    def click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))


class FakeMatcher:
    def find(self, frame, spec):
        return (40, 30) if frame[0, 0, 0] == spec["state"] else None


def step(name: str, state: int, *, after: int | None = None, optional: bool = False):
    return {
        "name": name, "target": {"state": state},
        "after": {"state": after} if after else None,
        "timeout": 0.6, "confirm_timeout": 0.6, "optional": optional, "offset": (0, 0),
    }


class DailyRunnerTests(unittest.TestCase):
    def runner(self, steps, states, *, max_clicks=10):
        clock = FakeClock()
        backend = FakeBackend(states)
        messages = []
        profile = {"steps": steps, "max_clicks": max_clicks, "max_seconds": 5}
        runner = DailyRunner(
            profile, backend, FakeMatcher(), messages.append, sleep=clock.sleep, clock=clock
        )
        return runner, backend, messages

    def test_dry_run_never_clicks(self):
        runner, backend, messages = self.runner([step("领取", 1)], [1])
        self.assertEqual(runner.run(), 0)
        self.assertEqual(backend.clicks, [])
        self.assertTrue(any("预演" in message for message in messages))

    def test_click_requires_two_confirmation_frames(self):
        runner, backend, _messages = self.runner(
            [step("打开日常", 1, after=2), step("领取", 3)],
            [1, 2, 2, 3, 0, 0],
        )
        self.assertEqual(runner.run(execute=True), 2)
        self.assertEqual(backend.clicks, [(240, 330), (240, 330)])

    def test_failed_confirmation_does_not_repeat_click(self):
        runner, backend, _messages = self.runner([step("领取", 1)], [1] * 12)
        with self.assertRaisesRegex(TimeoutError, "未确认变化"):
            runner.run(execute=True)
        self.assertEqual(backend.clicks, [(240, 330)])

    def test_optional_missing_step_is_skipped(self):
        runner, backend, messages = self.runner(
            [step("没有奖励", 1, optional=True), step("领取", 2)],
            [2] * 5 + [0, 0],
        )
        self.assertEqual(runner.run(execute=True), 1)
        self.assertEqual(len(backend.clicks), 1)
        self.assertTrue(any("跳过" in message for message in messages))

    def test_action_limit_stops_before_second_click(self):
        runner, backend, _messages = self.runner(
            [step("菜单", 1), step("奖励", 2)], [1, 0, 0, 2], max_clicks=1
        )
        with self.assertRaisesRegex(RuntimeError, "点击次数上限"):
            runner.run(execute=True)
        self.assertEqual(len(backend.clicks), 1)

    def test_existing_after_marker_cannot_confirm(self):
        matcher = Mock()
        matcher.find.side_effect = [(40, 30), (10, 10)]
        clock = FakeClock()
        backend = FakeBackend([1])
        runner = DailyRunner(
            {"steps": [step("领取", 1, after=2)], "max_clicks": 1, "max_seconds": 5},
            backend, matcher, sleep=clock.sleep, clock=clock,
        )
        with self.assertRaisesRegex(ProfileError, "点击前已存在"):
            runner.run(execute=True)
        self.assertFalse(backend.clicks)

    def test_loads_two_games_and_rejects_missing_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reward.png").touch()
            (root / "game.onnx").touch()
            document = {
                "games": {
                    "game-a": {
                        "window": {"title_contains": "Game A"},
                        "steps": [{"name": "领取", "target": {"image": "reward.png"}}],
                    },
                    "game-b": {
                        "window": {"process_name": "MuMu.exe"},
                        "steps": [{"name": "领取", "target": {
                            "model": "game.onnx", "class": "claim"
                        }}],
                    },
                }
            }
            path = root / "games.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assertEqual(load_profile(path, "game-a")["steps"][0]["target"]["kind"], "image")
            self.assertEqual(load_profile(path, "game-b")["steps"][0]["target"]["kind"], "yolo")
            (root / "reward.png").unlink()
            with self.assertRaisesRegex(ProfileError, "文件不存在"):
                load_profile(path, "game-a")

    def test_template_matcher_locates_synthetic_button(self):
        with tempfile.TemporaryDirectory() as directory:
            template = np.random.default_rng(42).integers(0, 256, (12, 18, 3), dtype=np.uint8)
            path = Path(directory) / "button.png"
            cv2.imwrite(str(path), template)
            frame = np.zeros((80, 100, 3), dtype=np.uint8)
            frame[20:32, 40:58] = template
            matcher = VisualMatcher()
            self.assertEqual(matcher.find(frame, {
                "kind": "image", "path": path, "confidence": 0.9,
            }), (49, 26))

    def test_yolo_matcher_uses_model_class(self):
        with patch("yolo_runtime.YoloDetector") as detector_type:
            detector_type.return_value.detect.return_value = [
                SimpleNamespace(center=(24, 35), score=0.9)
            ]
            matcher = VisualMatcher()
            spec = {"kind": "yolo", "path": Path("model.onnx"), "class": "reward", "confidence": 0.7}
            self.assertEqual(matcher.find(np.zeros((40, 40, 3), np.uint8), spec), (24, 35))
            detector_type.return_value.detect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
