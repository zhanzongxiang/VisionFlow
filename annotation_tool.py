"""In-app YOLO rectangle annotation workspace."""

from __future__ import annotations

import json
import os
import random
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
DEFAULT_CLASSES = ["enter_game"]
CLASS_COLORS = (
    "#38bdf8",
    "#f59e0b",
    "#34d399",
    "#f472b6",
    "#a78bfa",
    "#fb7185",
    "#facc15",
    "#2dd4bf",
)


@dataclass
class AnnotationBox:
    class_id: int
    x1: float
    y1: float
    x2: float
    y2: float

    def normalized(self, width: int, height: int) -> tuple[float, float, float, float]:
        left = max(0.0, min(float(width), min(self.x1, self.x2)))
        right = max(0.0, min(float(width), max(self.x1, self.x2)))
        top = max(0.0, min(float(height), min(self.y1, self.y2)))
        bottom = max(0.0, min(float(height), max(self.y1, self.y2)))
        return (
            ((left + right) / 2.0) / max(1, width),
            ((top + bottom) / 2.0) / max(1, height),
            (right - left) / max(1, width),
            (bottom - top) / max(1, height),
        )


def _format_number(value: float) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".") or "0"


def read_yolo_labels(
    path: Path,
    width: int,
    height: int,
    class_count: int | None = None,
) -> list[AnnotationBox]:
    """Read normalized YOLO rows and convert them to image-pixel boxes."""
    if not path.is_file():
        return []
    result: list[AnnotationBox] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return result
    for line in lines:
        fields = line.strip().split()
        if len(fields) < 5:
            continue
        try:
            class_id = int(fields[0])
            center_x, center_y, box_width, box_height = (
                float(fields[1]),
                float(fields[2]),
                float(fields[3]),
                float(fields[4]),
            )
        except (TypeError, ValueError):
            continue
        if class_count is not None and not 0 <= class_id < class_count:
            continue
        if box_width <= 0 or box_height <= 0:
            continue
        center_x = max(0.0, min(1.0, center_x))
        center_y = max(0.0, min(1.0, center_y))
        box_width = max(0.0, min(1.0, box_width))
        box_height = max(0.0, min(1.0, box_height))
        result.append(
            AnnotationBox(
                class_id,
                (center_x - box_width / 2.0) * width,
                (center_y - box_height / 2.0) * height,
                (center_x + box_width / 2.0) * width,
                (center_y + box_height / 2.0) * height,
            )
        )
    return result


def write_yolo_labels(
    path: Path,
    boxes: Iterable[AnnotationBox],
    width: int,
    height: int,
) -> None:
    """Write boxes in the five-column YOLO detection format."""
    rows: list[str] = []
    for box in boxes:
        center_x, center_y, box_width, box_height = box.normalized(width, height)
        if box_width <= 0 or box_height <= 0:
            continue
        rows.append(
            " ".join(
                (
                    str(max(0, int(box.class_id))),
                    _format_number(center_x),
                    _format_number(center_y),
                    _format_number(box_width),
                    _format_number(box_height),
                )
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def update_yolo_class_ids(
    path: Path,
    deleted_id: int,
    replacement_id: int | None = None,
) -> bool:
    """Remove one class from a label file, optionally merging it into another."""
    if not path.is_file():
        return False
    original = path.read_text(encoding="utf-8")
    updated = _remap_yolo_class_ids(original, deleted_id, replacement_id)
    if updated is None:
        return False
    _atomic_write_bytes(path, updated.encode("utf-8"))
    return True


def _remap_yolo_class_ids(
    content: str, deleted_id: int, replacement_id: int | None
) -> str | None:
    changed = False
    output: list[str] = []
    for line in content.splitlines():
        fields = line.strip().split()
        if not fields:
            continue
        try:
            class_id = int(fields[0])
        except (TypeError, ValueError):
            output.append(line)
            continue
        if class_id == deleted_id:
            if replacement_id is None:
                changed = True
                continue
            class_id = replacement_id
            changed = True
        elif class_id > deleted_id:
            class_id -= 1
            changed = True
        fields[0] = str(class_id)
        output.append(" ".join(fields))
    return "\n".join(output) + ("\n" if output else "") if changed else None


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def delete_yolo_class(
    root: Path,
    image_paths: Iterable[Path],
    class_names: list[str],
    deleted_id: int,
    replacement_id: int | None = None,
) -> int:
    """Rewrite all affected labels and the class list, restoring labels on failure."""
    if len(class_names) <= 1 or not 0 <= deleted_id < len(class_names):
        raise ValueError("至少需要保留一个有效类别")
    if replacement_id is not None and (
        not 0 <= replacement_id < len(class_names) or replacement_id == deleted_id
    ):
        raise ValueError("合并目标类别无效")
    mapped_id = replacement_id - (replacement_id > deleted_id) if replacement_id is not None else None
    updates: list[tuple[Path, bytes, bytes]] = []
    seen_labels: set[Path] = set()
    for image_path in image_paths:
        label_path = image_path.with_suffix(".txt")
        if label_path in seen_labels or not label_path.is_file():
            continue
        seen_labels.add(label_path)
        original = label_path.read_bytes()
        updated = _remap_yolo_class_ids(original.decode("utf-8"), deleted_id, mapped_id)
        if updated is not None:
            updates.append((label_path, original, updated.encode("utf-8")))

    class_path = root / "classes.txt"
    remaining_names = class_names[:deleted_id] + class_names[deleted_id + 1:]
    class_content = ("\n".join(remaining_names) + "\n").encode("utf-8")
    applied: list[tuple[Path, bytes]] = []
    try:
        for path, original, updated in updates:
            _atomic_write_bytes(path, updated)
            applied.append((path, original))
        _atomic_write_bytes(class_path, class_content)
    except OSError as exc:
        rollback_errors = []
        for path, original in reversed(applied):
            try:
                _atomic_write_bytes(path, original)
            except OSError as rollback_exc:
                rollback_errors.append(f"{path}: {rollback_exc}")
        if rollback_errors:
            raise OSError(
                f"类别更新失败且部分标签无法恢复，请检查：{'; '.join(rollback_errors)}"
            ) from exc
        raise
    return len(updates)


def _save_class_names(root: Path, class_names: list[str]) -> None:
    (root / "classes.txt").write_text(
        "\n".join(class_names) + ("\n" if class_names else ""),
        encoding="utf-8",
    )


def _load_class_names(root: Path) -> list[str]:
    path = root / "classes.txt"
    if path.is_file():
        try:
            values = [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, UnicodeError):
            values = []
        if values:
            return list(dict.fromkeys(values))
    return list(DEFAULT_CLASSES)


def export_yolo_dataset(
    source_root: Path,
    image_paths: Iterable[Path],
    class_names: list[str],
    destination: Path,
    validation_ratio: float = 0.2,
    seed: int = 42,
) -> dict[str, int]:
    """Copy images and labels into a deterministic YOLO train/val dataset."""
    source_root = Path(source_root).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    if not source_root.is_dir():
        raise ValueError(f"图片目录不存在: {source_root}")
    if not class_names:
        raise ValueError("至少需要一个类别")
    paths = sorted({Path(item).expanduser().resolve() for item in image_paths}, key=lambda item: str(item).lower())
    if not paths:
        raise ValueError("没有可导出的图片")
    if destination == source_root:
        raise ValueError("导出目录不能与图片目录相同")
    if not 0.0 <= float(validation_ratio) < 1.0:
        raise ValueError("验证集比例必须在 0 到 1 之间")

    relative_paths: list[tuple[Path, Path]] = []
    for image_path in paths:
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            relative = image_path.relative_to(source_root)
        except ValueError as exc:
            raise ValueError(f"图片不在源目录内: {image_path}") from exc
        relative_paths.append((image_path, relative))
    if not relative_paths:
        raise ValueError("没有找到可导出的图片")

    rng = random.Random(seed)
    shuffled = list(relative_paths)
    rng.shuffle(shuffled)
    if len(shuffled) > 1 and validation_ratio > 0:
        validation_count = max(1, int(round(len(shuffled) * float(validation_ratio))))
        validation_count = min(len(shuffled) - 1, validation_count)
    else:
        validation_count = 0
    split_items = {
        "val": shuffled[:validation_count],
        "train": shuffled[validation_count:],
    }

    destination.mkdir(parents=True, exist_ok=True)
    for split, items in split_items.items():
        for image_path, relative in items:
            image_target = destination / "images" / split / relative
            label_target = destination / "labels" / split / relative.with_suffix(".txt")
            image_target.parent.mkdir(parents=True, exist_ok=True)
            label_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, image_target)
            source_label = image_path.with_suffix(".txt")
            if source_label.is_file():
                shutil.copy2(source_label, label_target)
            else:
                label_target.write_text("", encoding="utf-8")

    _save_class_names(destination, class_names)
    yaml_lines = [
        "path: .",
        "train: images/train",
        "val: images/val",
        "names:",
    ]
    yaml_lines.extend(
        f"  {index}: {json.dumps(name, ensure_ascii=False)}"
        for index, name in enumerate(class_names)
    )
    (destination / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    return {
        "images": len(relative_paths),
        "train": len(split_items["train"]),
        "val": len(split_items["val"]),
    }


class AnnotationCanvas(QLabel):
    """A scaled image canvas that stores annotation boxes in source pixels."""

    boxes_changed = Signal()
    box_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("annotationCanvas")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(520, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.pixmap = QPixmap()
        self.image_path: Path | None = None
        self.boxes: list[AnnotationBox] = []
        self.class_names: list[str] = []
        self.current_class_id = 0
        self.selected_index = -1
        self._drag_start: QPointF | None = None
        self._drag_current: QPointF | None = None

    def sizeHint(self) -> QSize:
        return QSize(820, 560)

    def set_class_names(self, names: list[str]) -> None:
        self.class_names = list(names)
        self.update()

    def set_current_class(self, class_id: int) -> None:
        self.current_class_id = max(0, int(class_id))

    def set_image(self, path: Path, boxes: list[AnnotationBox]) -> None:
        self.image_path = Path(path)
        self.pixmap = QPixmap(str(path))
        self.boxes = [
            AnnotationBox(box.class_id, box.x1, box.y1, box.x2, box.y2)
            for box in boxes
        ]
        self.selected_index = -1
        self._drag_start = None
        self._drag_current = None
        self.update()

    def image_size(self) -> tuple[int, int]:
        return self.pixmap.width(), self.pixmap.height()

    def image_rect(self) -> QRectF:
        if self.pixmap.isNull() or self.pixmap.width() <= 0 or self.pixmap.height() <= 0:
            return QRectF()
        scale = min(
            self.width() / self.pixmap.width(),
            self.height() / self.pixmap.height(),
        )
        width = self.pixmap.width() * scale
        height = self.pixmap.height() * scale
        return QRectF(
            (self.width() - width) / 2.0,
            (self.height() - height) / 2.0,
            width,
            height,
        )

    def _image_point(self, widget_point: QPointF) -> QPointF | None:
        target = self.image_rect()
        if target.isNull() or not target.contains(widget_point):
            return None
        scale_x = self.pixmap.width() / target.width()
        scale_y = self.pixmap.height() / target.height()
        return QPointF(
            max(0.0, min(float(self.pixmap.width()), (widget_point.x() - target.x()) * scale_x)),
            max(0.0, min(float(self.pixmap.height()), (widget_point.y() - target.y()) * scale_y)),
        )

    def _widget_point(self, image_point: QPointF) -> QPointF:
        target = self.image_rect()
        return QPointF(
            target.x() + image_point.x() * target.width() / max(1, self.pixmap.width()),
            target.y() + image_point.y() * target.height() / max(1, self.pixmap.height()),
        )

    def _hit_test(self, image_point: QPointF) -> int:
        for index in range(len(self.boxes) - 1, -1, -1):
            box = self.boxes[index]
            rect = QRectF(
                min(box.x1, box.x2),
                min(box.y1, box.y2),
                abs(box.x2 - box.x1),
                abs(box.y2 - box.y1),
            )
            if rect.contains(image_point):
                return index
        return -1

    def remove_selected(self) -> bool:
        if not 0 <= self.selected_index < len(self.boxes):
            return False
        self.boxes.pop(self.selected_index)
        self.selected_index = -1
        self.boxes_changed.emit()
        self.box_selected.emit(-1)
        self.update()
        return True

    def clear_boxes(self) -> bool:
        if not self.boxes:
            return False
        self.boxes.clear()
        self.selected_index = -1
        self.boxes_changed.emit()
        self.box_selected.emit(-1)
        self.update()
        return True

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self.pixmap.isNull():
            super().mousePressEvent(event)
            return
        image_point = self._image_point(event.position())
        if image_point is None:
            return
        self.setFocus()
        hit = self._hit_test(image_point)
        if hit >= 0:
            self.selected_index = hit
            self.box_selected.emit(hit)
            self.update()
            return
        self.selected_index = -1
        self.box_selected.emit(-1)
        self._drag_start = image_point
        self._drag_current = image_point
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is not None:
            image_point = self._image_point(event.position())
            if image_point is not None:
                self._drag_current = image_point
                self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._drag_start is not None:
            image_point = self._image_point(event.position()) or self._drag_current
            if image_point is not None:
                left = min(self._drag_start.x(), image_point.x())
                right = max(self._drag_start.x(), image_point.x())
                top = min(self._drag_start.y(), image_point.y())
                bottom = max(self._drag_start.y(), image_point.y())
                if right - left >= 3 and bottom - top >= 3:
                    self.boxes.append(
                        AnnotationBox(
                            max(0, self.current_class_id),
                            left,
                            top,
                            right,
                            bottom,
                        )
                    )
                    self.selected_index = len(self.boxes) - 1
                    self.boxes_changed.emit()
                    self.box_selected.emit(self.selected_index)
            self._drag_start = None
            self._drag_current = None
            self.update()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.remove_selected()
            return
        super().keyPressEvent(event)

    def _class_name(self, class_id: int) -> str:
        if 0 <= class_id < len(self.class_names):
            return self.class_names[class_id]
        return f"class_{class_id}"

    def _color(self, class_id: int) -> QColor:
        return QColor(CLASS_COLORS[class_id % len(CLASS_COLORS)])

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#10151b"))
        if self.pixmap.isNull():
            painter.setPen(QColor("#8994a3"))
            painter.drawText(self.rect(), Qt.AlignCenter, "选择图片目录后，在这里标注目标")
            return

        target = self.image_rect()
        painter.drawPixmap(target.toRect(), self.pixmap)
        scale_x = target.width() / max(1, self.pixmap.width())
        scale_y = target.height() / max(1, self.pixmap.height())
        for index, box in enumerate(self.boxes):
            left = target.x() + min(box.x1, box.x2) * scale_x
            top = target.y() + min(box.y1, box.y2) * scale_y
            right = target.x() + max(box.x1, box.x2) * scale_x
            bottom = target.y() + max(box.y1, box.y2) * scale_y
            color = self._color(box.class_id)
            pen = QPen(color, 3 if index == self.selected_index else 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(left, top, right - left, bottom - top))
            label = f"{box.class_id}: {self._class_name(box.class_id)}"
            label_height = 20
            label_width = max(80, len(label) * 8 + 12)
            label_top = max(target.top(), top - label_height)
            label_rect = QRectF(left, label_top, label_width, label_height)
            painter.fillRect(label_rect, QColor(color.red(), color.green(), color.blue(), 210))
            painter.setPen(QColor("#081016"))
            painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter, f"  {label}")

        if self._drag_start is not None and self._drag_current is not None:
            left = min(self._drag_start.x(), self._drag_current.x())
            top = min(self._drag_start.y(), self._drag_current.y())
            right = max(self._drag_start.x(), self._drag_current.x())
            bottom = max(self._drag_start.y(), self._drag_current.y())
            painter.setPen(QPen(self._color(self.current_class_id), 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(
                QRectF(
                    target.x() + left * scale_x,
                    target.y() + top * scale_y,
                    (right - left) * scale_x,
                    (bottom - top) * scale_y,
                )
            )


class AnnotationPage(QWidget):
    """Manual YOLO annotation and dataset export page."""

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.setObjectName("annotationPage")
        self.settings = settings
        self.root: Path | None = None
        self.images: list[Path] = []
        self.current_index = -1
        self.class_names = list(DEFAULT_CLASSES)
        self.dirty = False
        self._loading = False
        self._build_ui()
        remembered = str(
            settings.value("ui/annotation_root", "")
            if settings is not None
            else ""
        ).strip()
        if remembered:
            self.root_edit.setText(remembered)
        self._update_controls()

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("pageHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 5, 14, 5)
        header_layout.setSpacing(9)
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(0)
        title = QLabel("数据标注")
        title.setObjectName("pageTitle")
        subtitle = QLabel("为采集截图绘制 YOLO 矩形框，并导出训练数据集")
        subtitle.setObjectName("pageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header_layout.addLayout(title_column)
        self.image_count_label = QLabel("0 张图片")
        self.image_count_label.setObjectName("pageCountBadge")
        header_layout.addWidget(self.image_count_label)
        header_layout.addStretch(1)
        self.save_button = QPushButton("保存标签")
        self.save_button.setToolTip("保存当前图片的 YOLO 标签")
        self.export_button = QPushButton("导出 YOLO 数据集")
        self.export_button.setToolTip("复制图片和标签，生成 train/val 目录与 data.yaml")
        header_layout.addWidget(self.save_button)
        header_layout.addWidget(self.export_button)
        page_layout.addWidget(header)

        root_row = QHBoxLayout()
        root_row.setContentsMargins(14, 8, 14, 8)
        root_row.setSpacing(8)
        root_row.addWidget(QLabel("图片目录"))
        self.root_edit = QLineEdit()
        self.root_edit.setPlaceholderText("选择采集批次中的 images 文件夹")
        self.choose_root_button = QPushButton("选择")
        self.load_root_button = QPushButton("加载")
        root_row.addWidget(self.root_edit, 1)
        root_row.addWidget(self.choose_root_button)
        root_row.addWidget(self.load_root_button)
        page_layout.addLayout(root_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 4, 6, 12)
        left_layout.setSpacing(6)
        left_layout.addWidget(QLabel("图片列表"))
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.SingleSelection)
        self.image_list.setAlternatingRowColors(True)
        self.image_list.setMinimumWidth(210)
        left_layout.addWidget(self.image_list, 1)
        self.image_status_label = QLabel("请选择图片目录")
        self.image_status_label.setWordWrap(True)
        self.image_status_label.setObjectName("pageSubtitle")
        left_layout.addWidget(self.image_status_label)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(6, 4, 6, 12)
        center_layout.setSpacing(6)
        self.canvas = AnnotationCanvas()
        center_layout.addWidget(self.canvas, 1)
        navigation = QHBoxLayout()
        self.previous_button = QPushButton("上一张")
        self.next_button = QPushButton("下一张")
        self.save_next_button = QPushButton("保存并下一张")
        self.canvas_status_label = QLabel("未选择图片")
        self.canvas_status_label.setObjectName("pageSubtitle")
        navigation.addWidget(self.previous_button)
        navigation.addWidget(self.next_button)
        navigation.addWidget(self.save_next_button)
        navigation.addStretch(1)
        navigation.addWidget(self.canvas_status_label)
        center_layout.addLayout(navigation)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 4, 12, 12)
        right_layout.setSpacing(9)
        class_group = QGroupBox("类别")
        class_layout = QVBoxLayout(class_group)
        class_row = QHBoxLayout()
        self.class_edit = QLineEdit()
        self.class_edit.setPlaceholderText("例如 enter_game")
        self.add_class_button = QPushButton("添加")
        class_row.addWidget(self.class_edit, 1)
        class_row.addWidget(self.add_class_button)
        class_layout.addLayout(class_row)
        self.class_list = QListWidget()
        self.class_list.setMaximumHeight(140)
        class_layout.addWidget(self.class_list)
        class_actions = QHBoxLayout()
        self.rename_class_button = QPushButton("重命名")
        self.delete_class_button = QPushButton("删除类别")
        class_actions.addWidget(self.rename_class_button)
        class_actions.addWidget(self.delete_class_button)
        class_layout.addLayout(class_actions)
        current_class_row = QHBoxLayout()
        current_class_row.addWidget(QLabel("当前类别"))
        self.current_class_box = QComboBox()
        current_class_row.addWidget(self.current_class_box, 1)
        class_layout.addLayout(current_class_row)
        right_layout.addWidget(class_group)

        box_group = QGroupBox("当前图片")
        box_layout = QVBoxLayout(box_group)
        self.selected_box_label = QLabel("未选择框")
        self.selected_box_label.setWordWrap(True)
        box_layout.addWidget(self.selected_box_label)
        self.delete_box_button = QPushButton("删除选中框")
        self.clear_boxes_button = QPushButton("清空全部框")
        box_layout.addWidget(self.delete_box_button)
        box_layout.addWidget(self.clear_boxes_button)
        right_layout.addWidget(box_group)

        export_group = QGroupBox("数据集导出")
        export_layout = QVBoxLayout(export_group)
        ratio_row = QHBoxLayout()
        ratio_row.addWidget(QLabel("验证集比例"))
        self.validation_ratio_spin = QDoubleSpinBox()
        self.validation_ratio_spin.setRange(0.0, 0.9)
        self.validation_ratio_spin.setSingleStep(0.05)
        self.validation_ratio_spin.setDecimals(2)
        self.validation_ratio_spin.setValue(0.2)
        ratio_row.addWidget(self.validation_ratio_spin)
        export_layout.addLayout(ratio_row)
        export_hint = QLabel("导出会保留没有目标的图片，并生成 data.yaml。")
        export_hint.setWordWrap(True)
        export_hint.setObjectName("pageSubtitle")
        export_layout.addWidget(export_hint)
        right_layout.addWidget(export_group)
        right_layout.addStretch(1)

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setSizes([220, 700, 260])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        page_layout.addWidget(splitter, 1)

        self.choose_root_button.clicked.connect(self._choose_root)
        self.load_root_button.clicked.connect(lambda: self.load_directory(self.root_edit.text()))
        self.root_edit.returnPressed.connect(lambda: self.load_directory(self.root_edit.text()))
        self.image_list.currentRowChanged.connect(self._image_selected)
        self.save_button.clicked.connect(self.save_current_label)
        self.export_button.clicked.connect(self._export_dataset)
        self.previous_button.clicked.connect(lambda: self._navigate(-1))
        self.next_button.clicked.connect(lambda: self._navigate(1))
        self.save_next_button.clicked.connect(self._save_and_next)
        self.add_class_button.clicked.connect(self._add_class)
        self.class_edit.returnPressed.connect(self._add_class)
        self.current_class_box.currentIndexChanged.connect(self._current_class_changed)
        self.class_list.currentRowChanged.connect(self._class_list_changed)
        self.rename_class_button.clicked.connect(self._rename_class)
        self.delete_class_button.clicked.connect(self._delete_class)
        self.delete_box_button.clicked.connect(self._delete_selected_box)
        self.clear_boxes_button.clicked.connect(self._clear_boxes)
        self.canvas.boxes_changed.connect(self._boxes_changed)
        self.canvas.box_selected.connect(self._box_selected)

    def _choose_root(self) -> None:
        initial = self.root_edit.text().strip() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, "选择图片目录", initial)
        if directory:
            self.load_directory(directory)

    @staticmethod
    def _scan_images(root: Path) -> list[Path]:
        return sorted(
            (
                path for path in root.rglob("*")
                if path.is_file()
                and path.suffix.lower() in IMAGE_SUFFIXES
                and not any(part.lower() in {"labels", "train", "val"} for part in path.relative_to(root).parts[:-1])
            ),
            key=lambda path: str(path).lower(),
        )

    def load_directory(self, value: str | Path) -> bool:
        root = Path(str(value)).expanduser().resolve()
        if not root.is_dir():
            self.image_status_label.setText(f"目录不存在: {root}")
            self._update_controls()
            return False
        self.save_current_if_dirty()
        self.root = root
        self.root_edit.setText(str(root))
        if self.settings is not None:
            self.settings.setValue("ui/annotation_root", str(root))
        self.class_names = _load_class_names(root)
        self.images = self._scan_images(root)
        self.current_index = -1
        self.dirty = False
        self.canvas.set_class_names(self.class_names)
        self._refresh_classes()
        self._refresh_image_list()
        if self.images:
            self.image_list.setCurrentRow(0)
        else:
            self.image_status_label.setText("目录中没有 PNG/JPG/BMP/WEBP 图片")
            self.canvas.set_image(root, [])
        self._update_controls()
        return bool(self.images)

    def _refresh_classes(self) -> None:
        self.class_list.clear()
        self.current_class_box.blockSignals(True)
        self.current_class_box.clear()
        for index, name in enumerate(self.class_names):
            self.class_list.addItem(f"{index}  {name}")
            self.current_class_box.addItem(f"{index}: {name}", index)
        self.current_class_box.blockSignals(False)
        self.canvas.set_class_names(self.class_names)
        if self.class_names:
            current_index = max(0, self.current_class_box.currentIndex())
            self.current_class_box.setCurrentIndex(current_index)
            self.class_list.setCurrentRow(current_index)
            self.canvas.set_current_class(int(self.current_class_box.currentData() or 0))

    def _refresh_image_list(self) -> None:
        self._loading = True
        self.image_list.clear()
        for path in self.images:
            label_path = path.with_suffix(".txt")
            suffix = " · 已标注" if label_path.is_file() else ""
            item = QListWidgetItem(f"{path.name}{suffix}")
            item.setData(Qt.UserRole, str(path))
            item.setToolTip(str(path))
            self.image_list.addItem(item)
        self._loading = False
        self.image_count_label.setText(f"{len(self.images)} 张图片")

    def _image_selected(self, row: int) -> None:
        if self._loading or not 0 <= row < len(self.images):
            return
        if row == self.current_index:
            return
        if not self.save_current_if_dirty():
            return
        self._load_image(row)

    def _load_image(self, row: int) -> None:
        path = self.images[row]
        image = QImage(str(path))
        if image.isNull():
            self.image_status_label.setText(f"无法读取图片: {path}")
            return
        boxes = read_yolo_labels(
            path.with_suffix(".txt"),
            image.width(),
            image.height(),
            len(self.class_names),
        )
        self._loading = True
        self.current_index = row
        self.canvas.set_image(path, boxes)
        self._loading = False
        self.dirty = False
        self.image_status_label.setText(f"{row + 1}/{len(self.images)}  ·  {path.name}")
        self.canvas_status_label.setText(f"{image.width()} × {image.height()}  ·  {len(boxes)} 个框")
        self._box_selected(-1)
        self._update_controls()

    def _boxes_changed(self) -> None:
        if self._loading:
            return
        self.dirty = True
        self._update_canvas_status()
        self._update_controls()

    def _box_selected(self, index: int) -> None:
        if 0 <= index < len(self.canvas.boxes):
            box = self.canvas.boxes[index]
            self.selected_box_label.setText(
                f"第 {index + 1} 个框 · 类别 {box.class_id} · "
                f"({box.x1:.0f}, {box.y1:.0f}) - ({box.x2:.0f}, {box.y2:.0f})"
            )
        else:
            self.selected_box_label.setText("未选择框")
        self._update_controls()

    def _update_canvas_status(self) -> None:
        if not 0 <= self.current_index < len(self.images):
            self.canvas_status_label.setText("未选择图片")
            return
        width, height = self.canvas.image_size()
        self.canvas_status_label.setText(
            f"{width} × {height}  ·  {len(self.canvas.boxes)} 个框"
            + ("  ·  未保存" if self.dirty else "")
        )

    def _update_controls(self) -> None:
        has_image = 0 <= self.current_index < len(self.images)
        has_box = 0 <= self.canvas.selected_index < len(self.canvas.boxes)
        self.save_button.setEnabled(has_image and self.dirty)
        self.export_button.setEnabled(bool(self.images) and bool(self.class_names))
        self.previous_button.setEnabled(has_image and self.current_index > 0)
        self.next_button.setEnabled(has_image and self.current_index < len(self.images) - 1)
        self.save_next_button.setEnabled(has_image and self.current_index < len(self.images) - 1)
        self.delete_box_button.setEnabled(has_box)
        self.clear_boxes_button.setEnabled(has_image and bool(self.canvas.boxes))
        has_class = bool(self.class_names)
        self.rename_class_button.setEnabled(has_class)
        self.delete_class_button.setEnabled(len(self.class_names) > 1)

    def _current_class_changed(self, index: int) -> None:
        class_id = self.current_class_box.itemData(index)
        if class_id is not None:
            self.canvas.set_current_class(int(class_id))
            self.class_list.blockSignals(True)
            self.class_list.setCurrentRow(int(class_id))
            self.class_list.blockSignals(False)

    def _class_list_changed(self, row: int) -> None:
        if 0 <= row < self.current_class_box.count():
            self.current_class_box.setCurrentIndex(row)

    def _add_class(self) -> None:
        name = self.class_edit.text().strip()
        if not name:
            return
        if name in self.class_names:
            self.current_class_box.setCurrentIndex(self.class_names.index(name))
            self.class_edit.clear()
            return
        self.class_names.append(name)
        self.class_edit.clear()
        self._refresh_classes()
        self.current_class_box.setCurrentIndex(len(self.class_names) - 1)
        if self.root is not None:
            _save_class_names(self.root, self.class_names)
        self._update_controls()

    def _selected_class_id(self) -> int | None:
        class_id = self.current_class_box.currentData()
        if class_id is None:
            return None
        return int(class_id)

    def _rename_class(self) -> None:
        class_id = self._selected_class_id()
        if class_id is None or not 0 <= class_id < len(self.class_names):
            return
        name, accepted = QInputDialog.getText(
            self,
            "重命名类别",
            "类别名称：",
            text=self.class_names[class_id],
        )
        name = str(name).strip()
        if not accepted or not name or name == self.class_names[class_id]:
            return
        if name in self.class_names:
            QMessageBox.information(self, "无法重命名", "已经存在同名类别。")
            return
        self.class_names[class_id] = name
        if self.root is not None:
            _save_class_names(self.root, self.class_names)
        self._refresh_classes()
        self.current_class_box.setCurrentIndex(class_id)
        self.image_status_label.setText(
            f"已重命名类别；类别编号 {class_id} 保持不变，已有标签无需修改"
        )

    def _delete_class(self) -> None:
        deleted_id = self._selected_class_id()
        if deleted_id is None or not 0 <= deleted_id < len(self.class_names):
            return
        if len(self.class_names) <= 1:
            QMessageBox.information(
                self,
                "无法删除",
                "至少保留一个类别。可以先添加新类别，再删除当前类别。",
            )
            return
        if not self.save_current_if_dirty():
            return

        other_classes = [
            (index, name)
            for index, name in enumerate(self.class_names)
            if index != deleted_id
        ]
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("删除类别")
        dialog.setText(f"确定删除类别“{self.class_names[deleted_id]}”吗？")
        dialog.setInformativeText(
            "删除后类别编号会重新排列。已有图片标签可以删除，"
            "也可以合并到另一个类别。"
        )
        remove_button = dialog.addButton("删除已有框", QMessageBox.DestructiveRole)
        merge_button = dialog.addButton("合并到其他类别", QMessageBox.AcceptRole)
        dialog.addButton("取消", QMessageBox.RejectRole)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked not in {remove_button, merge_button}:
            return

        replacement_id: int | None = None
        if clicked is merge_button:
            choices = [f"{index}: {name}" for index, name in other_classes]
            selected, accepted = QInputDialog.getItem(
                self,
                "合并类别",
                "保留为：",
                choices,
                0,
                False,
            )
            if not accepted:
                return
            selected_index = choices.index(selected)
            replacement_id = other_classes[selected_index][0]

        if self.root is None:
            removed_name = self.class_names.pop(deleted_id)
            self._refresh_classes()
            self.image_status_label.setText(f"已删除类别“{removed_name}”")
            return
        try:
            changed_files = delete_yolo_class(
                self.root, self.images, self.class_names, deleted_id, replacement_id
            )
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.critical(self, "删除类别失败", str(exc))
            return
        removed_name = self.class_names.pop(deleted_id)
        self._refresh_classes()
        if self.current_index >= 0:
            self._load_image(self.current_index)
        action = "合并" if replacement_id is not None else "删除"
        self.image_status_label.setText(
            f"已{action}类别“{removed_name}”，更新 {changed_files} 个标签文件"
        )

    def _delete_selected_box(self) -> None:
        if self.canvas.remove_selected():
            self._box_selected(-1)

    def _clear_boxes(self) -> None:
        if not self.canvas.boxes:
            return
        answer = QMessageBox.question(
            self,
            "清空标注",
            "确定清空当前图片的全部矩形框吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.canvas.clear_boxes()

    def save_current_label(self) -> bool:
        if not 0 <= self.current_index < len(self.images):
            return False
        path = self.images[self.current_index]
        width, height = self.canvas.image_size()
        if width <= 0 or height <= 0:
            return False
        try:
            write_yolo_labels(path.with_suffix(".txt"), self.canvas.boxes, width, height)
            if self.root is not None:
                _save_class_names(self.root, self.class_names)
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return False
        self.dirty = False
        self._refresh_image_item(self.current_index)
        self._update_canvas_status()
        self._update_controls()
        self.image_status_label.setText(f"{self.current_index + 1}/{len(self.images)}  ·  {path.name}  ·  已保存")
        return True

    def save_current_if_dirty(self) -> bool:
        return not self.dirty or self.save_current_label()

    def _refresh_image_item(self, row: int) -> None:
        if not 0 <= row < len(self.images):
            return
        item = self.image_list.item(row)
        if item is None:
            return
        path = self.images[row]
        suffix = " · 已标注" if path.with_suffix(".txt").is_file() else ""
        item.setText(f"{path.name}{suffix}")

    def _navigate(self, delta: int) -> None:
        target = self.current_index + int(delta)
        if not 0 <= target < len(self.images):
            return
        if self.save_current_if_dirty():
            self.image_list.setCurrentRow(target)

    def _save_and_next(self) -> None:
        if self.save_current_label():
            self._navigate(1)

    def _export_dataset(self) -> None:
        if not self.images:
            return
        if not self.save_current_if_dirty():
            return
        initial = str(self.root.parent / "yolo_dataset") if self.root is not None else str(Path.home())
        destination_text = QFileDialog.getExistingDirectory(self, "选择数据集导出目录", initial)
        if not destination_text:
            return
        destination = Path(destination_text).expanduser().resolve()
        if any(destination.iterdir()):
            answer = QMessageBox.question(
                self,
                "导出目录已有文件",
                f"{destination}\n已有文件，是否覆盖同名数据？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        try:
            summary = export_yolo_dataset(
                self.root or Path("."),
                self.images,
                self.class_names,
                destination,
                self.validation_ratio_spin.value(),
            )
        except (OSError, ValueError, shutil.Error) as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        self.image_status_label.setText(
            f"已导出 {summary['images']} 张 · 训练 {summary['train']} · 验证 {summary['val']}"
        )
        QMessageBox.information(
            self,
            "导出完成",
            f"YOLO 数据集已导出到：\n{destination}\n\n"
            f"图片 {summary['images']} 张，训练 {summary['train']} 张，验证 {summary['val']} 张。",
        )
