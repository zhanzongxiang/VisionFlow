"""Exercise frozen image matching and OCR without starting the main window."""

import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


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
        from capture_collection import CaptureSession
        from yolo_runtime import YoloDetector

        record(f"VisionFlow {app.APP_VERSION}")
        require(callable(YoloDetector), "YOLO adapter import failed")
        record(f"OpenCV {cv2.__version__}, NumPy {np.__version__}: OK")
        qt_app = QApplication.instance() or QApplication([])
        app.configure_ui_font(qt_app)
        with tempfile.TemporaryDirectory() as folder:
            settings_path = Path(folder) / "smoke.ini"
            with patch.object(
                app, "QSettings", side_effect=lambda *_args: QSettings(str(settings_path), QSettings.IniFormat)
            ):
                window = app.MainWindow()
                require(hasattr(window, "collection_page"), "Collection page is missing")
                require(hasattr(window, "nav_collection_button"), "Collection navigation is missing")
                require(hasattr(window, "annotation_page"), "Annotation page is missing")
                require(hasattr(window, "nav_annotation_button"), "Annotation navigation is missing")
                require(
                    hasattr(window.annotation_page, "rename_class_button")
                    and hasattr(window.annotation_page, "delete_class_button"),
                    "Annotation class controls are missing",
                )
                require(
                    hasattr(window, "pixel_similarity_spin"),
                    "Image color verification control is missing",
                )
                require(
                    window._normalize_step({
                        "type": "window_click_image", "pixel_similarity": 0.9,
                    })["pixel_similarity"] == 0.9,
                    "Image color threshold was not preserved on import",
                )
                window._autosave_timer.stop()
                window.deleteLater()
                record("Qt window: OK")

            path = Path(folder) / "中文模板.png"
            frame = np.full((128, 256, 3), 255, dtype=np.uint8)
            cv2.putText(frame, "Test 123", (12, 82), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
            success, png = cv2.imencode(".png", frame)
            require(success, "PNG encoding failed")
            path.write_bytes(png.tobytes())
            session = CaptureSession(
                Path(folder), "采集自检", {"hwnd": 1, "title": "Smoke"},
                interval=1, limit=3, dedup=True,
            )
            capture_args = {"backend": "smoke", "origin": (0, 0), "captured_at": "smoke"}
            first = session.save(frame, manual=False, **capture_args)
            require(first is not None, "Collection failed to save first frame")
            require(session.save(frame, manual=False, **capture_args) is None, "Collection dedup failed")
            require(session.save(frame, manual=True, **capture_args) is not None, "Manual collection was dropped")
            session.finish("stopped", "smoke")
            require(session.saved == 2 and session.skipped == 1, "Collection counters differ")
            require((session.directory / "frames.jsonl").is_file(), "Collection manifest is missing")
            record("Collection storage, dedup and manual capture: OK")
            _cv2, decoded = app.ScriptWorker._read_color_image(path)
            require(decoded.shape == frame.shape, "Decoded image dimensions differ")
            worker = app.ScriptWorker([], Path(folder))
            worker._capture = lambda: (cv2, frame, (0, 0))
            worker._capture_window = lambda: (cv2, frame, (100, 200))
            step = {"image": str(path), "confidence": 0.95, "timeout": 1}
            require(worker._wait_for_image(step) == (128, 64), "Screen image match returned incorrect coordinates")
            require(worker._wait_for_window_image(step) == (228, 264), "Window image match returned incorrect coordinates")
            record("Chinese-path screen/window image steps: OK")
            tinted = (frame.astype(np.float32) * 0.35 + 145).astype(np.uint8)
            tinted_match = app.find_template_match(cv2, tinted, frame)
            require(tinted_match.score >= 0.95, "Overlay test lost the structural match")
            require(
                app.template_pixel_similarity(cv2, tinted, frame, tinted_match) < 0.9,
                "Overlay passed the image color threshold",
            )
            record("Image color threshold rejects overlay: OK")
            scaled = cv2.resize(frame, None, fx=0.9, fy=0.9, interpolation=cv2.INTER_AREA)
            scaled_frame = cv2.copyMakeBorder(scaled, 12, 12, 18, 18, cv2.BORDER_CONSTANT)
            scaled_match = app.find_template_match(cv2, scaled_frame, frame)
            require(scaled_match.score >= 0.95 and abs(scaled_match.scale - 0.9) < 0.001, "Multi-scale matching failed")
            fitted, content = app.fit_frame_to_size(cv2, frame, 300, 300)
            require(fitted.shape[:2] == (300, 300) and content[2:] == (300, 150), "Aspect-fit geometry differs")
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
