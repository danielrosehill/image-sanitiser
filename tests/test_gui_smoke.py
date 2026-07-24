"""Headless GUI smoke tests: the full loop through the actual window."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np

from test_qr_pipeline import synthetic_photo


def test_main_window_open_scan_redact_save(tmp_path):
    from PySide6.QtWidgets import QApplication

    from image_sanitiser.core import verify
    from image_sanitiser.gui.app import MainWindow

    app = QApplication.instance() or QApplication([])

    image_path = tmp_path / "photo.png"
    cv2.imwrite(str(image_path), synthetic_photo())

    window = MainWindow()
    assert window.load_image(image_path)

    window.scan_current()
    assert len(window.findings) == 1

    window.redact_findings()
    window.save_copy()

    out_path = tmp_path / "redacted" / "photo.png"
    assert out_path.exists()
    exported = cv2.imread(str(out_path))
    assert verify.is_clean(exported, window.detectors)

    # load_image is folder-driven: the parent folder landed in the sidebar
    assert window.queue.count() >= 1
    assert "exported" in window.queue.item(0).text()

    window.close()
    app.processEvents()


def test_folder_driven_sidebar_workflow(tmp_path):
    from PySide6.QtWidgets import QApplication

    from image_sanitiser.core import verify
    from image_sanitiser.gui.app import MainWindow

    app = QApplication.instance() or QApplication([])

    flagged = tmp_path / "a-flagged.png"
    clean = tmp_path / "b-clean.png"
    cv2.imwrite(str(flagged), synthetic_photo())
    cv2.imwrite(str(clean), np.full((240, 320, 3), 128, dtype=np.uint8))

    window = MainWindow()
    window.load_folder(tmp_path)

    # Sidebar holds the folder; the first image is auto-selected.
    assert window.queue.count() == 2
    assert window.current_path.name == flagged.name

    window.scan_folder()
    assert "1 finding" in window.queue.item(0).text()
    assert "clean" in window.queue.item(1).text()

    # Click through: selecting a sidebar row shows that image.
    window.queue.setCurrentRow(1)
    assert window.current_path.name == clean.name

    # Redact the flagged image, browse away and back: work is kept in
    # memory until exported.
    window.queue.setCurrentRow(0)
    window.scan_current()
    window.redact_findings()
    assert "unsaved" in window.queue.item(0).text()
    window.queue.setCurrentRow(1)
    window.queue.setCurrentRow(0)
    assert verify.is_clean(window.working, window.detectors)

    window.save_copy()
    assert (tmp_path / "redacted" / flagged.name).exists()
    assert "exported" in window.queue.item(0).text()

    window.close()
    app.processEvents()
