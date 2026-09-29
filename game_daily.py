"""Bounded, visual daily-task runner using VisionFlow's window backends."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Protocol


class ProfileError(ValueError):
    pass


class CaptureInput(Protocol):
    def capture(self) -> tuple[Any, tuple[int, int]]: ...

    def click(self, x: int, y: int) -> None: ...


def _positive_number(value: Any, name: str, *, maximum: float = 3600) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= maximum:
        raise ProfileError(f"{name} 必须是 0 到 {maximum} 之间的数字")
    return float(value)


def _positive_int(value: Any, name: str, *, maximum: int = 100) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= maximum:
        raise ProfileError(f"{name} 必须是 1 到 {maximum} 之间的整数")
    return value


def _visual(value: Any, base_dir: Path, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError(f"{name} 必须是图片或 YOLO 目标")
    has_image = bool(value.get("image"))
    has_model = bool(value.get("model"))
    if has_image == has_model:
        raise ProfileError(f"{name} 必须且只能指定 image 或 model")
    path = base_dir / str(value["image"] if has_image else value["model"])
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ProfileError(f"{name} 文件不存在: {path}")
    if has_model and (path.suffix.lower() != ".onnx" or not str(value.get("class", "")).strip()):
        raise ProfileError(f"{name} 需要 .onnx 模型和 class 类别")
    confidence = value.get("confidence", 0.85 if has_image else 0.5)
    if (
        isinstance(confidence, bool) or not isinstance(confidence, (float, int))
        or not 0.1 <= confidence <= 0.99
    ):
        raise ProfileError(f"{name} 的 confidence 必须在 0.1 到 0.99 之间")
    return {
        "kind": "image" if has_image else "yolo",
        "path": path,
        "class": str(value.get("class", "")).strip(),
        "confidence": float(confidence),
    }


def load_profile(config: Path, game: str) -> dict[str, Any]:
    try:
        document = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"无法读取配置: {exc}") from exc
    profiles = document.get("games") if isinstance(document, dict) else None
    if not isinstance(profiles, dict) or game not in profiles:
        raise ProfileError(f"未找到游戏 {game}；可选: {', '.join(profiles or {})}")
    profile = profiles[game]
    if not isinstance(profile, dict):
        raise ProfileError("游戏配置必须是对象")
    window = profile.get("window")
    if not isinstance(window, dict) or not (
        str(window.get("title_contains", "")).strip() or str(window.get("process_name", "")).strip()
    ):
        raise ProfileError("window 至少需要 title_contains 或 process_name")
    steps = profile.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ProfileError("steps 至少需要一个视觉步骤")
    max_clicks = _positive_int(profile.get("max_clicks", 10), "max_clicks")
    max_seconds = _positive_number(profile.get("max_seconds", 120), "max_seconds")
    normalized = []
    for index, step in enumerate(steps, 1):
        name = f"steps[{index}]"
        if not isinstance(step, dict) or not str(step.get("name", "")).strip():
            raise ProfileError(f"{name} 需要 name")
        offset = step.get("offset", [0, 0])
        if (
            not isinstance(offset, list) or len(offset) != 2
            or any(isinstance(item, bool) or not isinstance(item, int) or abs(item) > 500 for item in offset)
        ):
            raise ProfileError(f"{name}.offset 必须是两个 -500 到 500 的整数")
        optional = step.get("optional", False)
        if not isinstance(optional, bool):
            raise ProfileError(f"{name}.optional 必须是布尔值")
        normalized.append({
            "name": str(step["name"]).strip(),
            "target": _visual(step.get("target"), config.parent, f"{name}.target"),
            "after": _visual(step["after"], config.parent, f"{name}.after") if "after" in step else None,
            "timeout": _positive_number(step.get("timeout", 8), f"{name}.timeout", maximum=120),
            "confirm_timeout": _positive_number(
                step.get("confirm_timeout", 5), f"{name}.confirm_timeout", maximum=120
            ),
            "optional": optional,
            "offset": tuple(offset),
        })
    return {
        "window": {
            "title_contains": str(window.get("title_contains", "")).strip(),
            "process_name": str(window.get("process_name", "")).strip(),
            "window_timeout": _positive_number(window.get("timeout", 10), "window.timeout", maximum=120),
        },
        "steps": normalized,
        "max_clicks": max_clicks,
        "max_seconds": max_seconds,
    }


class WindowBackend:
    def __init__(self, config: dict[str, Any], base_dir: Path, log: Callable[[str], None]):
        from app import AutomationError, ScriptWorker

        self.worker = ScriptWorker([], base_dir)
        self.worker.log.connect(log)
        self.worker._find_window(config)
        matches = [
            window for window in self.worker._enumerate_windows(include_hidden=True)
            if self.worker._window_matches(
                window, config["title_contains"], config["process_name"]
            )
        ]
        if len(matches) != 1:
            raise AutomationError(f"窗口匹配到 {len(matches)} 个实例，请缩小标题或进程条件")

    def capture(self) -> tuple[Any, tuple[int, int]]:
        _cv2, frame, origin = self.worker._capture_window()
        return frame, origin

    def click(self, x: int, y: int) -> None:
        self.worker._mouse_action("click", x, y)


class VisualMatcher:
    def __init__(self):
        self.templates: dict[Path, Any] = {}
        self.models: dict[Path, Any] = {}

    def find(self, frame: Any, spec: dict[str, Any]) -> tuple[int, int] | None:
        import cv2

        if spec["kind"] == "image":
            from app import find_template_match

            path = spec["path"]
            if path not in self.templates:
                import numpy as np

                template = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
                if template is None:
                    raise ProfileError(f"无法读取模板图片: {path}")
                self.templates[path] = template
            result = find_template_match(cv2, frame, self.templates[path])
            if result.score < spec["confidence"]:
                return None
            return (
                result.location[0] + result.size[0] // 2,
                result.location[1] + result.size[1] // 2,
            )
        from yolo_runtime import YoloDetector

        path = spec["path"]
        if path not in self.models:
            self.models[path] = YoloDetector(path)
        detections = self.models[path].detect(frame, spec["class"], spec["confidence"])
        return max(detections, key=lambda item: item.score).center if detections else None


class DailyRunner:
    def __init__(
        self, profile: dict[str, Any], backend: CaptureInput, matcher: VisualMatcher,
        log: Callable[[str], None] = print, *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.profile = profile
        self.backend = backend
        self.matcher = matcher
        self.log = log
        self.sleep = sleep
        self.clock = clock

    def _capture(self, deadline: float) -> tuple[Any, tuple[int, int]]:
        if self.clock() >= deadline:
            raise TimeoutError("已达到任务总时限")
        result = self.backend.capture()
        if self.clock() >= deadline:
            raise TimeoutError("截图完成时已超过任务时限")
        return result

    def _locate(self, spec: dict[str, Any], deadline: float) -> tuple[Any, tuple[int, int], tuple[int, int]] | None:
        while self.clock() < deadline:
            frame, origin = self._capture(deadline)
            point = self.matcher.find(frame, spec)
            if point is not None:
                return frame, origin, point
            self.sleep(0.25)
        return None

    def _confirm(
        self, step: dict[str, Any], deadline: float,
    ) -> bool:
        consecutive = 0
        while self.clock() < deadline:
            frame, _origin = self._capture(deadline)
            if step["after"] is not None:
                confirmed = self.matcher.find(frame, step["after"]) is not None
            else:
                confirmed = self.matcher.find(frame, step["target"]) is None
            consecutive = consecutive + 1 if confirmed else 0
            if consecutive >= 2:
                return True
            self.sleep(0.25)
        return False

    def run(self, *, execute: bool = False) -> int:
        deadline = self.clock() + self.profile["max_seconds"]
        clicks = 0
        for step in self.profile["steps"]:
            name = step["name"]
            self.log(f"寻找: {name}")
            found = self._locate(step["target"], min(deadline, self.clock() + step["timeout"]))
            if found is None:
                if self.clock() >= deadline:
                    raise TimeoutError("已达到任务总时限")
                if step["optional"]:
                    self.log(f"跳过未出现的可选步骤: {name}")
                    continue
                raise TimeoutError(f"未找到必需目标: {name}")
            frame, origin, point = found
            x, y = point[0] + step["offset"][0], point[1] + step["offset"][1]
            if not (0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]):
                raise ProfileError(f"{name} 的点击偏移超出截图范围")
            if clicks >= self.profile["max_clicks"]:
                raise RuntimeError("已达到点击次数上限")
            if step["after"] is not None and self.matcher.find(frame, step["after"]) is not None:
                raise ProfileError(f"{name} 的确认目标在点击前已存在，无法验证点击结果")
            self.log(f"{'点击' if execute else '预演'}: {name} @ ({x}, {y})")
            if not execute:
                self.log("预演只检查首个可操作目标；未发送输入")
                return 0
            self.backend.click(origin[0] + x, origin[1] + y)
            clicks += 1
            self.sleep(0.25)
            if not self._confirm(step, min(deadline, self.clock() + step["confirm_timeout"])):
                raise TimeoutError(f"点击后画面未确认变化，已停止: {name}")
            self.log(f"已确认: {name}")
        self.log(f"任务完成，共点击 {clicks} 次")
        return clicks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按游戏配置运行视觉日常任务；默认只预演")
    parser.add_argument("config", type=Path, help="包含 games 的 JSON 配置文件")
    parser.add_argument("--game", required=True, help="games 中的游戏名称")
    parser.add_argument("--execute", action="store_true", help="确认实际发送点击")
    args = parser.parse_args(argv)
    try:
        config = args.config.expanduser().resolve()
        profile = load_profile(config, args.game)
        backend = WindowBackend(profile["window"], config.parent, print)
        DailyRunner(profile, backend, VisualMatcher()).run(execute=args.execute)
        return 0
    except (ProfileError, TimeoutError, RuntimeError, OSError, KeyboardInterrupt) as exc:
        print(f"停止: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
