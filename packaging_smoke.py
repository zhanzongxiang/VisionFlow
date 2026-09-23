"""Exercise frozen image matching and OCR without starting the main window."""

import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch


def main() -> int:
    report = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd() / "packaging-smoke.log"
    def record(message: str) -> None:
        with report.open("a", encoding="utf-8") as stream:
            stream.write(message + "\n")
            stream.flush()

    report.write_text("", encoding="utf-8")
    try:
        record("Importing OpenCV and NumPy")
        import cv2
        import numpy as np
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        import app

        record(f"OpenCV {cv2.__version__}, NumPy {np.__version__}: OK")
        qt_app = QApplication.instance() or QApplication([])
        app.configure_ui_font(qt_app)
        with tempfile.TemporaryDirectory() as folder:
            settings_path = Path(folder) / "smoke.ini"
            with patch.object(
                app, "QSettings", side_effect=lambda *_args: QSettings(str(settings_path), QSettings.IniFormat)
            ):
                window = app.MainWindow()
                window.deleteLater()
                record("Qt window: OK")

            path = Path(folder) / "中文模板.png"
            frame = np.full((128, 256, 3), 255, dtype=np.uint8)
            cv2.putText(frame, "Test 123", (12, 82), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
            success, png = cv2.imencode(".png", frame)
            assert success
            path.write_bytes(png.tobytes())
            _cv2, decoded = app.ScriptWorker._read_color_image(path)
            assert decoded.shape == frame.shape
            worker = app.ScriptWorker([], Path(folder))
            worker._capture = lambda: (cv2, frame, (0, 0))
            worker._capture_window = lambda: (cv2, frame, (100, 200))
            step = {"image": str(path), "confidence": 0.95, "timeout": 1}
            assert worker._wait_for_image(step) == (128, 64)
            assert worker._wait_for_window_image(step) == (228, 264)
            record("Chinese-path screen/window image steps: OK")
            scaled = cv2.resize(frame, None, fx=0.9, fy=0.9, interpolation=cv2.INTER_AREA)
            scaled_frame = cv2.copyMakeBorder(scaled, 12, 12, 18, 18, cv2.BORDER_CONSTANT)
            scaled_match = app.find_template_match(cv2, scaled_frame, frame)
            assert scaled_match.score >= 0.95 and abs(scaled_match.scale - 0.9) < 0.001
            fitted, content = app.fit_frame_to_size(cv2, frame, 300, 300)
            assert fitted.shape[:2] == (300, 300) and content[2:] == (300, 150)
            record("Multi-scale matching and aspect-fit capture: OK")
            record("Starting RapidOCR inference")
            worker._run_ocr(frame)
            record("RapidOCR inference: OK")
        record("PASS")
        return 0
    except Exception:
        record(traceback.format_exc())
        record("FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
