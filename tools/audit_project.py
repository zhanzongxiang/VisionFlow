"""Offline audit probes and synthetic benchmarks; never sends real input."""

from __future__ import annotations

import argparse
import ast
import copy
import dis
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtWidgets import QApplication

import app
from game_daily import DailyRunner
from yolo_runtime import YoloDetector


def measure(operation, samples: int, warmups: int = 1) -> dict:
    for _ in range(warmups):
        operation()
    elapsed = []
    for _ in range(samples):
        started = time.perf_counter()
        operation()
        elapsed.append((time.perf_counter() - started) * 1000)
    ordered = sorted(elapsed)
    return {
        "samples": samples,
        "warmups": warmups,
        "median_ms": round(statistics.median(elapsed), 3),
        "p95_nearest_rank_ms": round(ordered[math.ceil(samples * .95) - 1], 3),
        "min_ms": round(min(elapsed), 3),
        "max_ms": round(max(elapsed), 3),
    }


def source_inventory() -> dict:
    result = {}
    for name in ("app.py", "yolo_runtime.py", "game_daily.py"):
        content = (ROOT / name).read_bytes()
        tree = ast.parse(content.decode("utf-8-sig"))
        result[name] = {
            "lines": len(content.splitlines()),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "classes": {
                node.name: {
                    "start": node.lineno,
                    "end": node.end_lineno,
                    "methods": sum(isinstance(item, ast.FunctionDef) for item in node.body),
                }
                for node in tree.body if isinstance(node, ast.ClassDef)
            },
        }
    return result


def issue_probes(root: Path) -> dict:
    results = {}
    flow = {
        "nodes": [
            {"id": "start", "type": "start"}, {"id": "end", "type": "end"},
            {"id": "check", "type": "condition", "operator": "and", "conditions": [
                {"type": "yolo_exists", "model": "game.onnx", "target_class": "claim"}
            ]},
        ],
        "edges": [
            {"from": "start", "to": "check", "port": "next"},
            {"from": "check", "to": "end", "port": "true"},
            {"from": "check", "to": "end", "port": "false"},
        ],
    }
    errors = app.validate_flow(flow)
    results["F01_yolo_condition_rejected"] = {"observed": bool(errors), "errors": errors}

    task = app.default_window_task()
    step = app.default_step("window_click_yolo")
    step["model"] = "../external/game.onnx"
    task["steps"] = [step]
    task["flow"] = app.flow_from_steps([step])
    exported = copy.deepcopy(task)
    exported["steps"][0]["model"] = "script_assets/game.onnx"
    exported["flow"]["nodes"][1]["step"]["model"] = "script_assets/game.onnx"
    holder = SimpleNamespace(window_tasks=[task])
    app.MainWindow._sync_exported_image_paths(holder, [exported])
    results["F03_model_path_not_synchronized"] = {
        "observed": task["steps"][0]["model"] != exported["steps"][0]["model"],
        "in_memory": task["steps"][0]["model"],
        "exported": exported["steps"][0]["model"],
    }

    worker = app.ScriptWorker([], root)
    condition = {"operator": "and", "negate": True, "conditions": [
        {"type": "image_exists", "image": str(root / "missing.png")}
    ]}
    results["F04_missing_asset_negates_to_true"] = {
        "observed": worker._evaluate_condition(condition),
    }
    missing_device = app.ScriptWorker([], root)
    missing_device._wait_for_yolo = Mock(side_effect=app.AutomationError("YOLO 检测超时: claim"))
    results["F04_yolo_timeout_becomes_absence"] = {
        "observed": not missing_device._condition_yolo_exists({"target_class": "claim"}),
    }

    # Objectness-bearing detection outputs must not be mistaken for class scores.
    detector = object.__new__(YoloDetector)
    detector.width = detector.height = 100
    detector.input_name = "images"
    detector.names = {0: "claim", 1: "other"}
    output = np.zeros((1, 20, 7), np.float32)
    output[0, 0] = [50, 50, 20, 20, .99, .01, .98]
    detector.session = Mock()
    detector.session.run.return_value = [output]
    detections = detector.detect(np.zeros((100, 100, 3), np.uint8), "claim", .5)
    results["F05_objectness_output_misclassified"] = {
        "observed": bool(detections),
        "reported_scores": [item.score for item in detections],
        "expected_claim_score": .99 * .01,
    }

    clock = SimpleNamespace(now=0.0)
    fake_backend = Mock()
    fake_backend.capture.return_value = (np.zeros((80, 100, 3), np.uint8), (0, 0))
    click_times = []
    fake_backend.click.side_effect = lambda *_: click_times.append(clock.now)
    fake_matcher = Mock()

    def slow_find(*_):
        clock.now += 2.0
        return (20, 20)

    fake_matcher.find.side_effect = slow_find
    profile = {"max_seconds": 1.0, "max_clicks": 1, "steps": [{
        "name": "audit", "target": {}, "after": None, "timeout": .5,
        "confirm_timeout": .5, "offset": (0, 0), "optional": False,
    }]}
    runner = DailyRunner(
        profile, fake_backend, fake_matcher, lambda *_: None,
        clock=lambda: clock.now, sleep=lambda _: None,
    )
    try:
        runner.run(execute=True)
    except TimeoutError:
        pass
    results["F06_daily_click_after_deadline"] = {
        "observed": bool(click_times and click_times[0] > profile["max_seconds"]),
        "click_times_s": click_times,
        "max_seconds": profile["max_seconds"],
    }

    clock.now = 0

    def slow_capture():
        clock.now += .6
        return np.zeros((80, 100, 3), np.uint8), (0, 0)

    fake_backend.capture.side_effect = slow_capture
    profile["max_seconds"] = 10
    profile["steps"][0]["optional"] = True
    try:
        runner.run()
        optional_error = ""
    except TimeoutError as exc:
        optional_error = str(exc)
    results["F06_optional_capture_exceeding_step_deadline_aborts"] = {
        "observed": bool(optional_error), "error": optional_error, "elapsed_s": clock.now,
    }

    stub = SimpleNamespace(
        _confirm_discard=lambda: True, _autosave_timer=Mock(),
        _close_requested=False, _close_timer=Mock(),
        _has_running_threads=lambda: True,
        centralWidget=Mock(), main_toolbar=Mock(), statusBar=Mock(),
        _cancel_mouse_capture=lambda: None, _cancel_drag_recording=lambda: None,
        _cancel_macro_listeners=lambda: None, worker=None, worker_thread=None,
        _stop_all_window_tasks=Mock(), _wait_for_window_tasks=Mock(),
        _discarded_changes=False, _write_autosave=Mock(),
        window_task_runs={1: {"thread": Mock(isRunning=Mock(return_value=True))}},
    )
    event = Mock()
    app.MainWindow.closeEvent(stub, event)
    results["F02_close_accepts_with_running_thread"] = {
        "observed": event.accept.called and stub.window_task_runs[1]["thread"].isRunning(),
        "scope": "close handler mock, no actual QThread destruction or crash attempted",
    }
    model_path = root / "cancel-probe.onnx"
    model_path.touch()
    worker = app.ScriptWorker([], root)
    worker.last_window = {"hwnd": 1}
    worker._capture_window = Mock(return_value=(cv2, np.zeros((80, 100, 3), np.uint8), (0, 0)))
    worker._mouse_action = Mock()
    detector = Mock(names={0: "claim"})

    def detect_and_cancel(*_):
        worker.stop()
        return [SimpleNamespace(score=.9, center=(20, 20), name="claim")]

    detector.detect.side_effect = detect_and_cancel
    worker._yolo_models[model_path.resolve()] = detector
    cancellation = ""
    try:
        worker.execute_step({"type": "window_click_yolo", "model": str(model_path), "target_class": "claim"})
    except app.AutomationError as exc:
        if not worker.stop_event.is_set():
            raise
        cancellation = str(exc)
    results["F02_dispatch_after_inference_cancellation"] = {
        "observed": worker.stop_event.is_set() and worker._mouse_action.called,
        "cancellation": cancellation,
        "scope": "mock dispatch only, no real input sent",
    }
    smoke_source = (ROOT / "packaging_smoke.py").read_text(encoding="utf-8")
    assert_count = sum(isinstance(node, ast.Assert) for node in ast.walk(ast.parse(smoke_source)))
    spec_tree = ast.parse((ROOT / "AutomationTool-small.spec").read_text(encoding="utf-8"))
    optimization = next(
        (
            keyword.value.value
            for node in ast.walk(spec_tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Analysis"
            for keyword in node.keywords
            if keyword.arg == "optimize" and isinstance(keyword.value, ast.Constant)
        ),
        0,
    )
    optimized = compile("assert False, 'audit assertion'", "<audit>", "exec", optimize=optimization)
    results["F12_frozen_smoke_asserts_elided"] = {
        "observed": assert_count > 0 and not any(
            "ASSERT" in instruction.opname for instruction in dis.get_instructions(optimized)
        ),
        "smoke_source_assert_count": assert_count,
        "build_setting": f"AutomationTool-small.spec: Analysis optimize={optimization}",
        "scope": "source inspection and CPython optimized bytecode; frozen build not rerun",
    }
    return results


def vision_benchmarks(samples: int) -> dict:
    rng = np.random.default_rng(20260929)
    template = rng.integers(0, 256, (48, 80, 3), dtype=np.uint8)
    result = {}
    for width, height in ((1280, 720), (1920, 1080)):
        frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
        frame[100:148, 120:200] = template
        prefix = f"template_{width}x{height}"
        result[prefix + "_9_scales"] = measure(
            lambda: app.find_template_match(cv2, frame, template), samples
        )
        result[prefix + "_1_scale_experiment"] = measure(
            lambda: app.find_template_match(cv2, frame, template, scales=(1.0,)), samples
        )
        roi = frame[60:260, 80:400]
        result[prefix + "_320x200_roi_9_scales_experiment"] = measure(
            lambda: app.find_template_match(cv2, roi, template), samples
        )
        result[prefix + "_full_std"] = measure(lambda: float(frame.std()), samples)
    return result


def gui_benchmarks(root: Path, samples: int) -> dict:
    settings_path = root / "audit.ini"
    result = {}
    with (
        patch.object(app, "QSettings", side_effect=lambda *_: QSettings(str(settings_path), QSettings.IniFormat)),
        patch.object(app.ScriptWorker, "_enumerate_windows", return_value=[]),
    ):
        window = app.MainWindow()
        window._autosave_timer.stop()
        try:
            window.current_file = root / "script.json"
            assets = root / "audit-assets"
            assets.mkdir()
            rng = np.random.default_rng(42)
            encoded_ok, png = cv2.imencode(
                ".png", rng.integers(0, 256, (180, 320, 3), dtype=np.uint8)
            )
            if not encoded_ok:
                raise RuntimeError("Synthetic PNG encoding failed")
            for count in (20, 100):
                for index in range(count):
                    path = assets / f"template-{index}.png"
                    if not path.exists():
                        path.write_bytes(png.tobytes())
                task = app.default_window_task()
                task["name"] = "audit-assets"
                task["steps"] = [app.default_step("wait")]
                task["flow"] = app.flow_from_steps(task["steps"])
                window.window_tasks = [task]
                window._bind_task_steps(0, 0)
                window.main_tabs.setCurrentWidget(window.editor_page)
                result[f"library_refresh_{count}_png_hidden"] = measure(
                    window._refresh_template_library_if_ready, samples
                )
                edits = iter(range(samples + 5))

                def edit_name():
                    window.node_name_edit.setText(f"audit-{next(edits)}")
                    window._autosave_timer.stop()

                result[f"name_edit_{count}_png_hidden"] = measure(edit_name, samples)
                original_loader = window._load_template_pixmap
                with patch.object(window, "_load_template_pixmap", wraps=original_loader) as loader:
                    edit_name()
                    result[f"name_edit_{count}_image_decodes"] = loader.call_count
                result[f"autosave_with_{count}_png_directory"] = measure(window._write_autosave, samples)

            for node_count in (100, 500):
                flow = app.flow_from_steps([app.default_step("wait") for _ in range(node_count)])
                result[f"flow_rebuild_{node_count}_actions"] = measure(
                    lambda: window.flow_canvas.set_flow(flow, fit=False), samples
                )
                result[f"flow_update_all_edges_{node_count}_actions"] = measure(
                    window.flow_canvas._update_edges, samples
                )
                result[f"validate_flow_{node_count}_actions"] = measure(
                    lambda: app.validate_flow(flow), samples
                )
        finally:
            window._autosave_timer.stop()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--probes-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.samples <= 100:
        parser.error("--samples must be between 1 and 100")
    packages = ("PySide6", "opencv-python", "numpy", "onnxruntime", "rapidocr_onnxruntime", "pyinstaller")
    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": "Offline synthetic tests, no real capture/input/YOLO inference/GPU measurement",
        "environment": {
            "python": platform.python_version(), "os": platform.platform(),
            "logical_cpus": os.cpu_count(), "opencv_threads": cv2.getNumThreads(),
            "packages": {name: importlib.metadata.version(name) for name in packages},
        },
        "sources": source_inventory(),
    }
    application = QApplication.instance() or QApplication([])
    application.setStyle("Fusion")
    application.setStyleSheet(app.APP_STYLESHEET)
    with tempfile.TemporaryDirectory(prefix="visionflow-audit-") as directory:
        root = Path(directory)
        report["issue_probes"] = issue_probes(root)
        if not args.probes_only:
            print("Measuring template matching...", flush=True)
            report["vision_benchmarks"] = vision_benchmarks(args.samples)
            print("Measuring isolated offscreen UI operations...", flush=True)
            report["gui_benchmarks"] = gui_benchmarks(root, args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Audit report: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
