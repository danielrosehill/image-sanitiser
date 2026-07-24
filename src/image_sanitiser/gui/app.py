"""Minimal M0 GUI: open an image or folder, scan for QR codes, redact, save a copy.

This is a thin walking skeleton of the workflow in spec/starter.md
(open → scan → review → apply → export). The review UI, per-finding
acceptance, and before/after compare land in later milestones.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QStatusBar,
    QToolBar,
)

from image_sanitiser.core import pipeline
from image_sanitiser.detectors import default_detectors

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _to_pixmap(bgr: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, _ = rgb.shape
    return QPixmap.fromImage(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Sanitiser")
        self.resize(1200, 800)

        self.detectors = default_detectors()
        self.current_path: Path | None = None
        self.working: np.ndarray | None = None
        self.findings = []

        self.viewer = QLabel("Open an image or a folder to begin")
        self.viewer.setAlignment(Qt.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.viewer)
        scroll.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(scroll)

        self.queue = QListWidget()
        self.queue.currentItemChanged.connect(
            lambda current, _previous: self._queue_item_activated(current)
        )
        dock = QDockWidget("Queue")
        dock.setWidget(self.queue)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        for text, slot in [
            ("Open Image", self.open_image),
            ("Open Folder", self.open_folder),
            ("Scan", self.scan_current),
            ("Scan Folder", self.scan_folder),
            ("Redact Findings", self.redact_findings),
            ("Save Copy", self.save_copy),
        ]:
            action = QAction(text, self)
            action.triggered.connect(slot)
            toolbar.addAction(action)

        self.setStatusBar(QStatusBar())

    # -- file handling ------------------------------------------------
    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)",
        )
        if path:
            self.load_image(Path(path))

    def open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Open folder")
        if path:
            self.load_folder(Path(path))

    def load_folder(self, folder: Path):
        self.queue.clear()
        for entry in sorted(folder.iterdir()):
            if entry.suffix.lower() in IMAGE_EXTENSIONS:
                item = QListWidgetItem(entry.name)
                item.setData(Qt.UserRole, str(entry))
                self.queue.addItem(item)
        self.statusBar().showMessage(f"{self.queue.count()} images queued from {folder}")

    def load_image(self, path: Path) -> bool:
        image = cv2.imread(str(path))
        if image is None:
            QMessageBox.warning(self, "Image Sanitiser", f"Could not read {path}")
            return False
        self.current_path = path
        self.working = image
        self.findings = []
        self._refresh()
        self.statusBar().showMessage(str(path))
        return True

    def _queue_item_activated(self, item):
        if item is not None:
            self.load_image(Path(item.data(Qt.UserRole)))

    # -- scanning -----------------------------------------------------
    def scan_current(self):
        if self.working is None:
            return
        self.findings = [f for det in self.detectors for f in det.scan(self.working)]
        summary = f"{len(self.findings)} finding(s) in {self.current_path.name}"
        payloads = [f.payload for f in self.findings if f.payload]
        if payloads:
            summary += " — decoded: " + "; ".join(payloads)
        self.statusBar().showMessage(summary)
        self._refresh()

    def scan_folder(self):
        # M0: synchronous pass over the queue; moves to a worker pool in M3.
        flagged = 0
        for i in range(self.queue.count()):
            item = self.queue.item(i)
            image = cv2.imread(item.data(Qt.UserRole))
            if image is None:
                continue
            count = sum(len(det.scan(image)) for det in self.detectors)
            name = Path(item.data(Qt.UserRole)).name
            item.setText(f"{name}  [{count} finding(s)]" if count else name)
            flagged += bool(count)
        self.statusBar().showMessage(
            f"Scan complete: findings in {flagged} of {self.queue.count()} images"
        )

    # -- redaction ----------------------------------------------------
    def redact_findings(self):
        if self.working is None or not self.findings:
            self.statusBar().showMessage("Nothing to redact — run Scan first")
            return
        escalated = 0
        unresolved = 0
        for finding in self.findings:
            result = pipeline.redact_verified(
                self.working, finding, self.detectors, method="pixelate"
            )
            self.working = result.image
            escalated += result.escalated
            unresolved += not result.clean
        count = len(self.findings)
        self.findings = []
        message = f"Redacted {count} region(s), verified unreadable"
        if escalated:
            message += f" ({escalated} escalated)"
        if unresolved:
            message = (
                f"WARNING: {unresolved} of {count} region(s) still detectable "
                "after full escalation"
            )
        self.statusBar().showMessage(f"{message} — Save Copy to export")
        self._refresh()

    def save_copy(self):
        if self.working is None or self.current_path is None:
            return
        out_dir = self.current_path.parent / "redacted"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / self.current_path.name
        # cv2.imwrite re-encodes pixels only: EXIF, GPS and embedded
        # thumbnails from the original are not carried across.
        cv2.imwrite(str(out_path), self.working)
        self.statusBar().showMessage(f"Saved {out_path}")

    # -- display ------------------------------------------------------
    def _refresh(self):
        if self.working is None:
            return
        pixmap = _to_pixmap(self.working)
        if self.findings:
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(255, 40, 40), max(2, pixmap.width() // 400)))
            for finding in self.findings:
                x, y, w, h = finding.bbox
                painter.drawRect(x, y, w, h)
            painter.end()
        self.viewer.setPixmap(pixmap)
        self.viewer.adjustSize()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    for arg in sys.argv[1:]:
        target = Path(arg)
        if target.is_dir():
            window.load_folder(target)
        elif target.is_file():
            window.load_image(target)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
