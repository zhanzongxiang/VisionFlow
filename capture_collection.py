"""Read-only screenshot collection, session storage, and its Qt workspace page."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QEvent, QThread, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QSplitter, QStyle, QVBoxLayout, QWidget,
)


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def game_folder(name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")[:80].rstrip(" .")
    if not clean:
        raise ValueError("请填写游戏名称")
    if clean.split(".")[0].upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10)),
    }:
        clean = "_" + clean
    return clean


class CaptureSession:
    """One append-only image manifest per session; exact dedup never deletes files."""

    def __init__(self, root: Path, game: str, window: dict, interval: float, limit: int, dedup: bool):
        batch = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
        self.directory = Path(root).expanduser().resolve() / game_folder(game) / batch
        self.directory.mkdir(parents=True, exist_ok=False)
        self.images = self.directory / "images"
        self.images.mkdir()
        self.saved = 0
        self.skipped = 0
        self.limit = limit
        self.dedup = dedup
        self.seen: set[str] = set()
        self.metadata = {
            "version": 1, "game": game, "session": batch, "started_at": timestamp(),
            "window": {key: window.get(key) for key in ("hwnd", "title", "process_name")},
            "interval_seconds": interval, "max_images": limit, "dedup": dedup,
            "status": "collecting",
        }
        self._write_metadata()

    def _write_metadata(self) -> None:
        payload = {**self.metadata, "saved": self.saved, "skipped_duplicates": self.skipped}
        temporary = self.directory / "session.json.tmp"
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.directory / "session.json")

    def save(self, frame, *, manual: bool, backend: str, origin: tuple, captured_at: str) -> dict | None:
        if self.saved >= self.limit:
            raise RuntimeError("已达到保存数量上限")
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3 or not frame.size:
            raise ValueError("截图必须是非空 BGR 图像")
        digest = hashlib.sha256(str(frame.shape).encode("ascii") + frame.tobytes()).hexdigest()
        if self.dedup and not manual and digest in self.seen:
            self.skipped += 1
            return None
        ok, encoded = cv2.imencode(".png", frame)
        if not ok:
            raise OSError("截图 PNG 编码失败")
        filename = f"{self.saved + 1:06d}.png"
        destination = self.images / filename
        record = {
            "file": f"images/{filename}", "captured_at": captured_at,
            "width": frame.shape[1], "height": frame.shape[0],
            "backend": backend, "origin": list(origin), "manual": manual,
            "sha256": digest,
        }
        with destination.open("xb") as output:
            output.write(encoded.tobytes())
        try:
            with (self.directory / "frames.jsonl").open("a", encoding="utf-8") as manifest:
                manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            destination.unlink(missing_ok=True)
            raise
        self.saved += 1
        self.seen.add(digest)
        return record

    def finish(self, status: str, message: str) -> None:
        self.metadata.update({"status": status, "message": message, "ended_at": timestamp()})
        self._write_metadata()


class CollectionThread(QThread):
    session_ready = Signal(str)
    frame_saved = Signal(str, object)
    counts = Signal(int, int)
    notice = Signal(str)
    result = Signal(bool, str)

    def __init__(self, worker_type, window: dict, root: Path, game: str,
                 interval: float, limit: int, dedup: bool, parent=None):
        super().__init__(parent)
        self.worker_type = worker_type
        self.window = dict(window)
        self.root, self.game = root, game
        self.interval, self.limit, self.dedup = interval, limit, dedup
        self.cancel = threading.Event()
        self.paused = threading.Event()
        self.manual = threading.Event()

    def stop(self) -> None:
        self.cancel.set()

    def set_paused(self, paused: bool) -> None:
        self.paused.set() if paused else self.paused.clear()

    def snapshot(self) -> None:
        self.manual.set()

    def run(self) -> None:
        session = None
        success, message = True, "采集已停止"
        status = "stopped"
        try:
            worker = self.worker_type([], self.root)
            # Sharing only an Event lets Stop interrupt the existing capture backend.
            worker.stop_event = self.cancel
            current = next((
                item for item in worker._enumerate_windows(include_hidden=True)
                if item["hwnd"] == self.window["hwnd"]
                and item.get("process_name") == self.window.get("process_name")
            ), None)
            if current is None:
                raise RuntimeError("所选窗口已关闭，请刷新窗口列表")
            worker.last_window = current
            worker._resolve_background_input_handle(current)
            worker._resolve_emulator_capture_backend()
            if self.cancel.is_set():
                return
            session = CaptureSession(
                self.root, self.game, current, self.interval, self.limit, self.dedup
            )
            self.session_ready.emit(str(session.directory))
            next_capture = 0.0
            failures = 0
            while not self.cancel.is_set():
                manual = self.manual.is_set()
                if not manual and (self.paused.is_set() or time.monotonic() < next_capture):
                    self.cancel.wait(0.05)
                    continue
                if manual:
                    self.manual.clear()
                try:
                    _cv2, frame, origin = worker._capture_window()
                except Exception as exc:
                    if self.cancel.is_set():
                        break
                    failures += 1
                    if failures >= 3:
                        raise RuntimeError(f"连续三次截图失败: {exc}") from exc
                    if manual:
                        self.manual.set()
                    self.notice.emit(f"截图失败，重试 {failures}/3: {exc}")
                    self.cancel.wait(0.5)
                    continue
                if self.cancel.is_set():
                    break
                # Discard an in-flight timer frame if Pause arrived during capture.
                if self.paused.is_set() and not manual:
                    continue
                failures = 0
                record = session.save(
                    frame, manual=manual, backend=worker._last_capture_backend,
                    origin=origin, captured_at=timestamp(),
                )
                self.counts.emit(session.saved, session.skipped)
                if record is not None:
                    self.frame_saved.emit(str(session.directory / record["file"]), record)
                if session.saved >= self.limit:
                    status, message = "limit_reached", "已达到保存数量上限"
                    break
                next_capture = time.monotonic() + self.interval
        except Exception as exc:
            if not self.cancel.is_set():
                success, status, message = False, "failed", str(exc)
        finally:
            if session is not None:
                try:
                    session.finish(status, message)
                except OSError as exc:
                    success, message = False, f"无法保存采集批次信息: {exc}"
            self.result.emit(success, message)


class CollectionPage(QWidget):
    snapshot_requested = Signal()

    def __init__(self, worker_type, settings, parent=None):
        super().__init__(parent)
        self.setObjectName("collectionPage")
        self.worker_type, self.settings = worker_type, settings
        self.thread: CollectionThread | None = None
        self.listener = None
        self.session_dir: Path | None = None
        self.preview_pixmap = QPixmap()
        self._build_ui()
        self.snapshot_requested.connect(self._snapshot)

    def _icon_button(self, icon, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setIcon(self.style().standardIcon(icon))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setFixedSize(34, 32)
        return button

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QWidget()
        header.setObjectName("pageHeader")
        bar = QHBoxLayout(header)
        title = QLabel("数据采集")
        title.setObjectName("pageTitle")
        bar.addWidget(title)
        bar.addStretch()
        self.start_button = QPushButton("开始采集")
        self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.pause_button = self._icon_button(QStyle.SP_MediaPause, "暂停 / 继续")
        self.pause_button.setCheckable(True)
        self.stop_button = self._icon_button(QStyle.SP_MediaStop, "停止采集")
        self.snapshot_button = self._icon_button(QStyle.SP_DialogSaveButton, "补拍一张")
        self.folder_button = self._icon_button(QStyle.SP_DirOpenIcon, "打开当前批次目录")
        for button in (self.start_button, self.pause_button, self.stop_button,
                       self.snapshot_button, self.folder_button):
            bar.addWidget(button)
        layout.addWidget(header)
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(12, 4, 12, 4)
        self.state_label = QLabel("未开始")
        self.state_label.setWordWrap(True)
        self.count_label = QLabel("已保存 0 / 跳过 0")
        status_bar.addWidget(self.state_label, 1)
        status_bar.addWidget(self.count_label)
        layout.addLayout(status_bar)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        settings_scroll.setMinimumWidth(300)
        settings_scroll.setMaximumWidth(370)
        settings_widget = QWidget()
        settings_widget.setObjectName("collectionSettings")
        settings_widget.setAttribute(Qt.WA_StyledBackground, True)
        form = QFormLayout(settings_widget)
        form.setContentsMargins(12, 12, 12, 12)
        form.setVerticalSpacing(14)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.game_edit = QLineEdit(str(self.settings.value("collection/game", "")))
        self.window_box = QComboBox()
        self.window_box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.window_box.setMinimumContentsLength(10)
        self.window_box.addItem("未选择窗口", None)
        self.refresh_button = self._icon_button(QStyle.SP_BrowserReload, "刷新窗口列表")
        row = QHBoxLayout()
        row.addWidget(self.window_box, 1)
        row.addWidget(self.refresh_button)
        self.root_edit = QLineEdit(str(self.settings.value(
            "collection/root", str(Path.home() / "Pictures" / "VisionFlow")
        )))
        self.root_edit.setMinimumWidth(0)
        self.root_edit.setToolTip(self.root_edit.text())
        self.root_edit.textChanged.connect(self.root_edit.setToolTip)
        self.window_box.currentTextChanged.connect(self.window_box.setToolTip)
        self.browse_button = self._icon_button(QStyle.SP_DirOpenIcon, "选择保存目录")
        path_row = QHBoxLayout()
        path_row.addWidget(self.root_edit, 1)
        path_row.addWidget(self.browse_button)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.2, 60)
        self.interval_spin.setValue(1)
        self.interval_spin.setSuffix(" 秒")
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 100000)
        self.limit_spin.setValue(1000)
        self.dedup_box = QCheckBox("跳过完全重复图片")
        self.dedup_box.setChecked(True)
        self.hotkey_box = QComboBox()
        self.hotkey_box.addItems(["F10", "F11", "F12", "关闭"])
        self.hotkey_box.setToolTip("运行或暂停时全局补拍；按键仍会传递给游戏")
        form.addRow("游戏名称", self.game_edit)
        form.addRow("目标窗口", row)
        form.addRow("保存目录", path_row)
        form.addRow("采集间隔", self.interval_spin)
        form.addRow("保存上限", self.limit_spin)
        form.addRow("重复筛选", self.dedup_box)
        form.addRow("补拍快捷键", self.hotkey_box)
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        settings_scroll.setWidget(settings_widget)
        splitter.addWidget(settings_scroll)
        right = QWidget()
        content = QVBoxLayout(right)
        self.preview = QLabel("暂无截图")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(180, 120)
        self.preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.preview.installEventFilter(self)
        content.addWidget(self.preview, 1)
        self.frame_list = QListWidget()
        self.frame_list.setMaximumHeight(160)
        self.frame_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content.addWidget(self.frame_list)
        content.addWidget(self.path_label)
        splitter.addWidget(right)
        splitter.setSizes([330, 730])
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        self.inputs = (
            self.game_edit, self.window_box, self.refresh_button, self.root_edit,
            self.browse_button, self.interval_spin, self.limit_spin, self.dedup_box, self.hotkey_box,
        )
        self.start_button.clicked.connect(self._start)
        self.pause_button.toggled.connect(self._pause)
        self.stop_button.clicked.connect(self.stop)
        self.snapshot_button.clicked.connect(self._snapshot)
        self.refresh_button.clicked.connect(self.refresh_windows)
        self.browse_button.clicked.connect(self._browse)
        self.folder_button.clicked.connect(self._open_folder)
        self.frame_list.currentItemChanged.connect(self._show_frame)
        self._set_running(False)

    @property
    def is_running(self) -> bool:
        return self.thread is not None and self.thread.isRunning()

    def refresh_windows(self) -> None:
        if self.is_running:
            return
        selected = self.window_box.currentData() or {}
        self.window_box.clear()
        self.window_box.addItem("未选择窗口", None)
        try:
            for window in self.worker_type._enumerate_windows():
                self.window_box.addItem(
                    f"{window['title']} [{window.get('process_name', '')}]", window
                )
                if window["hwnd"] == selected.get("hwnd"):
                    self.window_box.setCurrentIndex(self.window_box.count() - 1)
        except Exception as exc:
            self.state_label.setText(f"无法获取窗口: {exc}")

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.root_edit.text())
        if path:
            self.root_edit.setText(path)

    def _open_folder(self) -> None:
        if self.session_dir is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.session_dir)))

    def _set_running(self, running: bool) -> None:
        for widget in self.inputs:
            widget.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.pause_button.setEnabled(running)
        self.stop_button.setEnabled(running)
        self.snapshot_button.setEnabled(running)
        self.folder_button.setEnabled(self.session_dir is not None)

    def _start(self) -> None:
        if self.thread is not None:
            return
        window = self.window_box.currentData()
        try:
            game = self.game_edit.text().strip()
            game_folder(game)
            if not isinstance(window, dict):
                raise ValueError("请选择目标窗口")
            if not self.root_edit.text().strip():
                raise ValueError("请选择保存目录")
            root = Path(self.root_edit.text()).expanduser().resolve()
        except (ValueError, OSError) as exc:
            self.state_label.setText(str(exc))
            return
        self.settings.setValue("collection/game", game)
        self.settings.setValue("collection/root", str(root))
        self.session_dir = None
        self.frame_list.clear()
        self.preview_pixmap = QPixmap()
        self.preview.clear()
        self.path_label.clear()
        self.count_label.setText("已保存 0 / 跳过 0")
        self.pause_button.setChecked(False)
        thread = CollectionThread(
            self.worker_type, window, root, game, self.interval_spin.value(),
            self.limit_spin.value(), self.dedup_box.isChecked(), self,
        )
        self.thread = thread
        thread.session_ready.connect(self._session_ready)
        thread.frame_saved.connect(self._frame_saved)
        thread.counts.connect(self._counts)
        thread.notice.connect(self.state_label.setText)
        thread.result.connect(self._result)
        thread.finished.connect(self._finished)
        self._set_running(True)
        self.state_label.setText("采集中")
        self._start_hotkey()
        thread.start()

    def _start_hotkey(self) -> None:
        name = self.hotkey_box.currentText().lower()
        if name == "关闭":
            return
        try:
            from pynput import keyboard

            key = getattr(keyboard.Key, name)
            self.listener = keyboard.Listener(
                on_release=lambda released: self.snapshot_requested.emit() if released == key else None
            )
            self.listener.start()
        except Exception as exc:
            self._stop_hotkey()
            self.state_label.setText(f"全局补拍不可用，仍可使用补拍按钮: {exc}")

    def _stop_hotkey(self) -> None:
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

    def stop(self) -> None:
        self._stop_hotkey()
        if self.thread is not None:
            self.thread.stop()
            self.state_label.setText("正在停止")
            self.pause_button.setEnabled(False)
            self.snapshot_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def _pause(self, paused: bool) -> None:
        if self.thread is not None:
            self.thread.set_paused(paused)
            self.state_label.setText("已暂停" if paused else "采集中")
            self.pause_button.setIcon(self.style().standardIcon(
                QStyle.SP_MediaPlay if paused else QStyle.SP_MediaPause
            ))

    @Slot()
    def _snapshot(self) -> None:
        if self.thread is not None and not self.thread.cancel.is_set():
            self.thread.snapshot()

    @Slot(str)
    def _session_ready(self, directory: str) -> None:
        self.session_dir = Path(directory)
        self.path_label.setText(directory)
        self.folder_button.setEnabled(True)

    @Slot(int, int)
    def _counts(self, saved: int, skipped: int) -> None:
        self.count_label.setText(f"已保存 {saved} / 跳过 {skipped}")

    @Slot(bool, str)
    def _result(self, success: bool, message: str) -> None:
        self.state_label.setText(message if success else f"采集失败: {message}")

    @Slot()
    def _finished(self) -> None:
        self._stop_hotkey()
        thread = self.thread
        self.thread = None
        if thread is not None:
            thread.deleteLater()
        self.pause_button.setChecked(False)
        self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self._set_running(False)

    @Slot(str, object)
    def _frame_saved(self, path: str, record: dict) -> None:
        follow_latest = (
            self.frame_list.count() == 0
            or self.frame_list.currentRow() == self.frame_list.count() - 1
        )
        item = QListWidgetItem(
            f"{Path(path).name}  {record['width']} x {record['height']}  "
            f"{record['backend']}  {'补拍' if record['manual'] else '定时'}"
        )
        item.setData(Qt.UserRole, path)
        item.setToolTip(path)
        self.frame_list.addItem(item)
        # Keep the UI bounded; all saved images remain on disk and in the manifest.
        if self.frame_list.count() > 200:
            self.frame_list.takeItem(0)
        if follow_latest:
            self.frame_list.setCurrentItem(item)

    def _show_frame(self, item, _previous=None) -> None:
        self.preview_pixmap = QPixmap(item.data(Qt.UserRole)) if item is not None else QPixmap()
        self._resize_preview()

    def _resize_preview(self) -> None:
        if not self.preview_pixmap.isNull():
            self.preview.setPixmap(self.preview_pixmap.scaled(
                self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        else:
            self.preview.setText("暂无截图")

    def eventFilter(self, watched, event) -> bool:
        if watched is self.preview and event.type() == QEvent.Resize:
            self._resize_preview()
        return super().eventFilter(watched, event)
