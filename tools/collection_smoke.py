"""Render the collection page and optionally verify real Win32 capture on a test window."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "screenshots" / "collection-qa")
    options = parser.parse_args()
    if not options.native:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import cv2
    import numpy as np
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    import app

    application = QApplication([])
    app.configure_ui_font(application)
    application.setStyle("Fusion")
    application.setStyleSheet(app.APP_STYLESHEET)
    options.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        settings = QSettings(str(Path(directory) / "qa.ini"), QSettings.IniFormat)
        with patch.object(app, "QSettings", return_value=settings):
            window = app.MainWindow()
        target = QWidget()
        target.setWindowTitle("VisionFlow Capture QA")
        target.resize(640, 360)
        layout = QVBoxLayout(target)
        layout.addWidget(QLabel("Screenshot verification"))
        for color, text in (
            ("#347854", "Daily rewards: ready"),
            ("#8a3e57", "Mailbox: unread"),
            ("#424548", "Claimed rewards: 3"),
        ):
            label = QLabel(text)
            label.setStyleSheet(f"background: {color}; color: white; padding: 20px; font-size: 16px;")
            layout.addWidget(label)
        target.show()
        window.show()
        application.processEvents()
        window.nav_collection_button.click()
        page = window.collection_page
        page.game_edit.setText("采集验证")
        page.root_edit.setText(str(options.output / "sessions"))
        page.hotkey_box.setCurrentText("关闭")
        page.limit_spin.setValue(1)
        if options.native:
            page.refresh_windows()
            for index in range(page.window_box.count()):
                item = page.window_box.itemData(index)
                if item and item["hwnd"] == int(target.winId()):
                    page.window_box.setCurrentIndex(index)
                    break
            else:
                raise RuntimeError("Test window was not enumerated")
        else:
            image = target.grab().toImage().convertToFormat(app.QImage.Format_RGB888)
            raw = np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine())
            frame = cv2.cvtColor(raw[:, :image.width() * 3].reshape(image.height(), image.width(), 3), cv2.COLOR_RGB2BGR)

            class RenderWorker:
                _last_capture_backend = "QA"

                def __init__(self, *_args):
                    pass

                @staticmethod
                def _enumerate_windows(**_kwargs):
                    return [{"hwnd": 1, "title": "VisionFlow Capture QA", "process_name": "qa.exe"}]

                def _resolve_background_input_handle(self, _window):
                    pass

                def _resolve_emulator_capture_backend(self):
                    pass

                def _capture_window(self):
                    return cv2, frame, (0, 0)

            page.worker_type = RenderWorker
            page.refresh_windows()
            page.window_box.setCurrentIndex(1)
        try:
            page._start()
            deadline = time.monotonic() + 20
            while page.thread is not None and time.monotonic() < deadline:
                application.processEvents()
                time.sleep(0.01)
            if page.thread is not None:
                raise RuntimeError("Capture did not finish")
            if page.preview_pixmap.isNull():
                raise RuntimeError(page.state_label.text())
            manifest = page.session_dir / "frames.jsonl"
            record = json.loads(manifest.read_text(encoding="utf-8").splitlines()[0])
            saved = cv2.imdecode(np.frombuffer((page.session_dir / record["file"]).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
            if saved.std() < 5:
                raise RuntimeError("Captured frame is blank")
            for width, height in ((1120, 720), (920, 620)):
                window.resize(width, height)
                application.processEvents()
                page._resize_preview()
                application.processEvents()
                path = options.output / f"collection-{width}x{height}.png"
                if not window.grab().save(str(path)):
                    raise RuntimeError(f"Could not render {path}")
                print(path)
            print(f"PASS backend={record['backend']} frame={saved.shape[1]}x{saved.shape[0]}")
        finally:
            page.stop()
            if page.thread is not None:
                page.thread.wait(10000)
            application.processEvents()
            window._autosave_timer.stop()
            window.is_dirty = False
            window.close()
            target.close()
            application.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
