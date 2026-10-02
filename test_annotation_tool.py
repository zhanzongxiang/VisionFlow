from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from annotation_tool import (
    AnnotationBox,
    AnnotationPage,
    delete_yolo_class,
    export_yolo_dataset,
    read_yolo_labels,
    update_yolo_class_ids,
    write_yolo_labels,
)


class AnnotationToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_yolo_label_round_trip_keeps_pixel_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.txt"
            original = AnnotationBox(0, 30, 20, 130, 80)
            write_yolo_labels(path, [original], 200, 100)

            rows = path.read_text(encoding="utf-8").split()
            self.assertEqual(rows[0], "0")
            self.assertAlmostEqual(float(rows[1]), 0.4)
            self.assertAlmostEqual(float(rows[2]), 0.5)
            self.assertAlmostEqual(float(rows[3]), 0.5)
            self.assertAlmostEqual(float(rows[4]), 0.6)

            restored = read_yolo_labels(path, 200, 100, 1)
            self.assertEqual(len(restored), 1)
            self.assertAlmostEqual(restored[0].x1, 30)
            self.assertAlmostEqual(restored[0].y1, 20)
            self.assertAlmostEqual(restored[0].x2, 130)
            self.assertAlmostEqual(restored[0].y2, 80)

    def test_export_creates_yolo_train_val_layout_and_empty_negative_labels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "images"
            root.mkdir()
            images = []
            for index in range(4):
                image = root / f"{index:06d}.png"
                image.write_bytes(f"image-{index}".encode("ascii"))
                images.append(image)
            (root / "000000.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
            destination = Path(directory) / "dataset"

            summary = export_yolo_dataset(
                root,
                images,
                ["enter_game", "game_hud"],
                destination,
                validation_ratio=0.25,
            )

            self.assertEqual(summary, {"images": 4, "train": 3, "val": 1})
            self.assertTrue((destination / "data.yaml").is_file())
            self.assertEqual(
                (destination / "classes.txt").read_text(encoding="utf-8"),
                "enter_game\ngame_hud\n",
            )
            exported_images = list((destination / "images").rglob("*.png"))
            exported_labels = list((destination / "labels").rglob("*.txt"))
            self.assertEqual(len(exported_images), 4)
            self.assertEqual(len(exported_labels), 4)
            self.assertTrue(any(not label.read_text(encoding="utf-8").strip() for label in exported_labels))

    def test_deleting_class_can_remove_or_merge_and_reindexes_following_classes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.txt"
            path.write_text(
                "0 0.1 0.1 0.1 0.1\n"
                "1 0.2 0.2 0.1 0.1\n"
                "2 0.3 0.3 0.1 0.1\n",
                encoding="utf-8",
            )
            self.assertTrue(update_yolo_class_ids(path, 1))
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "0 0.1 0.1 0.1 0.1\n1 0.3 0.3 0.1 0.1\n",
            )

            path.write_text(
                "0 0.1 0.1 0.1 0.1\n"
                "1 0.2 0.2 0.1 0.1\n"
                "2 0.3 0.3 0.1 0.1\n",
                encoding="utf-8",
            )
            self.assertTrue(update_yolo_class_ids(path, 1, 0))
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "0 0.1 0.1 0.1 0.1\n0 0.2 0.2 0.1 0.1\n1 0.3 0.3 0.1 0.1\n",
            )

    def test_delete_class_updates_all_labels_and_only_once_per_shared_stem(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = [root / "frame.png", root / "frame.jpg", root / "other.png"]
            label = root / "frame.txt"
            other = root / "other.txt"
            label.write_text("1 0.5 0.5 0.2 0.2\n2 0.4 0.4 0.1 0.1\n", encoding="utf-8")
            other.write_text("2 0.3 0.3 0.1 0.1\n", encoding="utf-8")
            (root / "classes.txt").write_text("first\nremoved\nlast\n", encoding="utf-8")
            classes = ["first", "removed", "last"]

            self.assertEqual(delete_yolo_class(root, images, classes, 1, 2), 2)
            self.assertEqual(label.read_text(encoding="utf-8"), "1 0.5 0.5 0.2 0.2\n1 0.4 0.4 0.1 0.1\n")
            self.assertEqual(other.read_text(encoding="utf-8"), "1 0.3 0.3 0.1 0.1\n")
            self.assertEqual((root / "classes.txt").read_text(encoding="utf-8"), "first\nlast\n")
            self.assertEqual(classes, ["first", "removed", "last"])

    def test_delete_class_rolls_back_label_files_on_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = [root / "a.png", root / "b.png"]
            original = "1 0.5 0.5 0.2 0.2\n"
            for image in images:
                image.with_suffix(".txt").write_text(original, encoding="utf-8")
            class_path = root / "classes.txt"
            class_path.write_text("keep\nremove\n", encoding="utf-8")
            from annotation_tool import _atomic_write_bytes

            def fail_second_label(path: Path, content: bytes) -> None:
                if path == images[1].with_suffix(".txt"):
                    raise OSError("locked label")
                _atomic_write_bytes(path, content)

            with patch("annotation_tool._atomic_write_bytes", side_effect=fail_second_label):
                with self.assertRaisesRegex(OSError, "locked label"):
                    delete_yolo_class(root, images, ["keep", "remove"], 1)

            self.assertEqual(images[0].with_suffix(".txt").read_text(encoding="utf-8"), original)
            self.assertEqual(images[1].with_suffix(".txt").read_text(encoding="utf-8"), original)
            self.assertEqual(class_path.read_text(encoding="utf-8"), "keep\nremove\n")
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_page_loads_images_and_existing_labels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            root.mkdir()
            image = QImage(200, 100, QImage.Format.Format_RGB32)
            image.fill(0xFFFFFFFF)
            image_path = root / "000004.png"
            self.assertTrue(image.save(str(image_path), "PNG"))
            (root / "000004.txt").write_text("0 0.5 0.5 0.5 0.5\n", encoding="utf-8")
            settings = QSettings(str(Path(directory) / "settings.ini"), QSettings.IniFormat)
            page = AnnotationPage(settings)
            self.addCleanup(page.deleteLater)

            self.assertTrue(page.load_directory(root))
            self.assertEqual(len(page.images), 1)
            self.assertTrue(page.images[0].samefile(image_path))
            self.assertEqual(page.class_names, ["enter_game"])
            self.assertEqual(len(page.canvas.boxes), 1)
            self.assertAlmostEqual(page.canvas.boxes[0].x1, 50)
            self.assertAlmostEqual(page.canvas.boxes[0].x2, 150)


if __name__ == "__main__":
    unittest.main()
