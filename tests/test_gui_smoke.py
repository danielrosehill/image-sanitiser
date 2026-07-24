"""Headless GUI smoke test: the full M0 loop through the actual window."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2

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

    window.close()
    app.processEvents()
