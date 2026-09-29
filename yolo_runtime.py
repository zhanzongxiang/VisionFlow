"""Small ONNX inference adapter for Ultralytics YOLO detection exports."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    class_id: int
    name: str
    score: float
    box: tuple[int, int, int, int]

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.box
        return (x1 + x2) // 2, (y1 + y2) // 2


class YoloDetector:
    """Supports standard Ultralytics detect ONNX exports (with or without NMS)."""

    def __init__(self, path: Path):
        import onnxruntime as ort

        self.path = Path(path)
        self.session = ort.InferenceSession(str(self.path), providers=["CPUExecutionProvider"])
        inputs = self.session.get_inputs()
        if len(inputs) != 1 or len(inputs[0].shape) != 4:
            raise ValueError("仅支持单输入的 YOLO 检测 ONNX 模型")
        self.input_name = inputs[0].name
        shape = inputs[0].shape
        self.height = int(shape[2]) if isinstance(shape[2], int) and shape[2] > 0 else 640
        self.width = int(shape[3]) if isinstance(shape[3], int) and shape[3] > 0 else 640
        self.names: dict[int, str] = {}
        metadata = self.session.get_modelmeta().custom_metadata_map or {}
        if "names" in metadata:
            try:
                names = ast.literal_eval(metadata["names"])
                if isinstance(names, dict):
                    self.names = {int(key): str(value) for key, value in names.items()}
                elif isinstance(names, (list, tuple)):
                    self.names = {index: str(value) for index, value in enumerate(names)}
            except (ValueError, SyntaxError, TypeError):
                pass

    def class_id(self, target: str) -> int:
        target = target.strip()
        if not target:
            raise ValueError("请填写要识别的 YOLO 类别名或编号")
        if target.isdecimal():
            class_id = int(target)
            if self.names and class_id not in self.names:
                raise ValueError(f"类别编号 {class_id} 超出模型类别范围")
            return class_id
        matches = [key for key, name in self.names.items() if name.casefold() == target.casefold()]
        if not matches:
            raise ValueError(f"模型中没有类别“{target}”，可改用类别编号")
        return matches[0]

    def detect(self, frame: np.ndarray, target: str, confidence: float) -> list[Detection]:
        class_id = self.class_id(target)
        frame_height, frame_width = frame.shape[:2]
        scale = min(self.width / frame_width, self.height / frame_height)
        resized_width = min(self.width, round(frame_width * scale))
        resized_height = min(self.height, round(frame_height * scale))
        left = (self.width - resized_width) // 2
        top = (self.height - resized_height) // 2
        image = np.full((self.height, self.width, 3), 114, dtype=np.uint8)
        image[top:top + resized_height, left:left + resized_width] = cv2.resize(
            frame, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR
        )
        tensor = np.ascontiguousarray(
            cv2.cvtColor(image, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None], dtype=np.float32
        ) / 255.0
        raw = np.asarray(self.session.run(None, {self.input_name: tensor})[0])
        if raw.ndim != 3 or raw.shape[0] != 1:
            raise ValueError(f"不支持的 YOLO 输出形状: {raw.shape}")
        rows = raw[0]
        # Normal exports are (1, 4 + classes, predictions). NMS exports are
        # (1, predictions, 6) with xyxy, confidence, class id.
        end_to_end = rows.shape[1] == 6 and rows.shape[0] <= 1000
        if not end_to_end and rows.shape[0] < rows.shape[1]:
            rows = rows.T
        if not end_to_end and rows.shape[1] < 5:
            raise ValueError(f"不支持的 YOLO 输出形状: {raw.shape}")
        if not end_to_end and class_id >= rows.shape[1] - 4:
            raise ValueError(f"类别编号 {class_id} 超出模型类别范围")

        if end_to_end:
            candidates = rows[(rows[:, 5].astype(int) == class_id) & (rows[:, 4] >= confidence)]
            boxes = candidates[:, :4].copy()
            scores = candidates[:, 4]
        else:
            scores = rows[:, 4 + class_id]
            candidates = rows[scores >= confidence]
            scores = scores[scores >= confidence]
            boxes = np.empty((len(candidates), 4), dtype=np.float32)
            boxes[:, 0] = candidates[:, 0] - candidates[:, 2] / 2
            boxes[:, 1] = candidates[:, 1] - candidates[:, 3] / 2
            boxes[:, 2] = candidates[:, 0] + candidates[:, 2] / 2
            boxes[:, 3] = candidates[:, 1] + candidates[:, 3] / 2
        if not len(boxes):
            return []
        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - left) / scale
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - top) / scale
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, frame_width - 1)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, frame_height - 1)
        valid = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
        boxes, scores = boxes[valid], scores[valid]
        if not len(boxes):
            return []
        # Keep postprocessing bounded for dense game scenes.
        order = np.argsort(scores)[::-1][:300]
        boxes, scores = boxes[order], scores[order]
        # Greedy class-specific NMS with stable original indices.
        pending = np.argsort(scores)[::-1]
        kept: list[int] = []
        while len(pending) and len(kept) < 100:
            best = int(pending[0])
            kept.append(best)
            rest = pending[1:]
            x1 = np.maximum(boxes[best, 0], boxes[rest, 0])
            y1 = np.maximum(boxes[best, 1], boxes[rest, 1])
            x2 = np.minimum(boxes[best, 2], boxes[rest, 2])
            y2 = np.minimum(boxes[best, 3], boxes[rest, 3])
            intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            overlap = intersection / np.maximum(areas[best] + areas[rest] - intersection, 1)
            pending = rest[overlap <= 0.45]
        return [
            Detection(
                class_id, self.names.get(class_id, str(class_id)), float(scores[index]),
                tuple(int(round(value)) for value in boxes[index]),
            )
            for index in kept
        ]
