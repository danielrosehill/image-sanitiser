"""Folder-driven GUI: open a folder, click through its images in the
sidebar, scan/redact/export each one.

The sidebar (left dock) is the primary navigation surface: every image in
the open folder appears with a thumbnail and a state badge (findings /
redacted / exported). Opening a single image opens its parent folder.
Redacted-but-unexported images are kept in memory, so clicking through the
folder never loses work. The review checklist and manual regions land in
later milestones (spec/starter.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QImage,
    QImageReader,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
)
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

from image_sanitiser import __version__
from image_sanitiser.core import pipeline
from image_sanitiser.detectors import default_detectors

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PATH_ROLE = Qt.UserRole
THUMB_EDGE = 72


def _to_pixmap(bgr: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, _ = rgb.shape
    return QPixmap.fromImage(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy())


def _thumbnail(path: Path) -> QIcon:
    # QImageReader decodes at reduced scale, so populating the sidebar
    # never loads full-size images.
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid():
        reader.setScaledSize(size.scaled(THUMB_EDGE, THUMB_EDGE, Qt.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        placeholder = QPixmap(THUMB_EDGE, THUMB_EDGE)
        placeholder.fill(QColor(128, 128, 128))
        return QIcon(placeholder)
    return QIcon(QPixmap.fromImage(image))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Sanitiser")
        self.resize(1200, 800)

        self.detectors = default_detectors()
        self.folder: Path | None = None
        self.current_path: Path | None = None
        self.working: np.ndarray | None = None
        self.findings = []
        self._unsaved: dict[str, np.ndarray] = {}  # redacted, not yet exported
        self._syncing = False  # sidebar selection is being set programmatically

        self.viewer = QLabel("Open a folder to begin")
        self.viewer.setAlignment(Qt.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.viewer)
        scroll.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(scroll)

        self.queue = QListWidget()
        self.queue.setIconSize(QSize(THUMB_EDGE, THUMB_EDGE))
        self.queue.setSpacing(2)
        self.queue.setWordWrap(True)
        self.queue.currentItemChanged.connect(self._queue_item_activated)
        self.dock = QDockWidget("Folder")
        self.dock.setWidget(self.queue)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        self.resizeDocks([self.dock], [280], Qt.Horizontal)

        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        for text, shortcut, slot in [
            ("Open Folder…", QKeySequence.Open, self.open_folder),
            ("Open Image…", "Ctrl+I", self.open_image),
            ("Scan", "F5", self.scan_current),
            ("Scan Folder", "Shift+F5", self.scan_folder),
            ("Redact Findings", "Ctrl+R", self.redact_findings),
            ("Save Copy", QKeySequence.Save, self.save_copy),
        ]:
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
            toolbar.addAction(action)

        self.setStatusBar(QStatusBar())

    # -- folder / sidebar ---------------------------------------------
    def open_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Open folder", str(self.folder or Path.home())
        )
        if path:
            self.load_folder(Path(path))

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open image", str(self.folder or Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)",
        )
        if path:
            self.load_image(Path(path))

    def load_folder(self, folder: Path, select: Path | None = None):
        self.folder = folder
        self.queue.blockSignals(True)
        self.queue.clear()
        for entry in sorted(folder.iterdir()):
            if entry.is_file() and entry.suffix.lower() in IMAGE_EXTENSIONS:
                item = QListWidgetItem(_thumbnail(entry), entry.name)
                item.setData(PATH_ROLE, str(entry))
                item.setToolTip(str(entry))
                self.queue.addItem(item)
        self.queue.blockSignals(False)
        self.dock.setWindowTitle(f"Folder — {folder.name} ({self.queue.count()})")
        self.setWindowTitle(f"Image Sanitiser — {folder}")
        if self.queue.count() == 0:
            self.current_path = None
            self.working = None
            self.findings = []
            self.viewer.setPixmap(QPixmap())
            self.viewer.setText("No images in this folder")
            self.statusBar().showMessage(f"No images found in {folder}")
            return
        row = self._row_for(select) if select is not None else None
        self.queue.setCurrentRow(row if row is not None else 0)

    def load_image(self, path: Path) -> bool:
        """Show an image and sync the sidebar to its parent folder."""
        path = Path(path)
        if not self._show_image(path):
            return False
        self._syncing = True
        try:
            row = self._row_for(path)
            if row is None:
                self.load_folder(path.parent, select=path)
            elif self.queue.currentRow() != row:
                self.queue.setCurrentRow(row)
        finally:
            self._syncing = False
        return True

    def _queue_item_activated(self, current, _previous=None):
        if current is not None and not self._syncing:
            self._show_image(Path(current.data(PATH_ROLE)))

    def _row_for(self, path: Path | None) -> int | None:
        if path is None:
            return None
        target = Path(path).resolve()
        for i in range(self.queue.count()):
            if Path(self.queue.item(i).data(PATH_ROLE)).resolve() == target:
                return i
        return None

    def _set_badge(self, path: Path, badge: str | None):
        row = self._row_for(path)
        if row is None:
            return
        item = self.queue.item(row)
        name = Path(item.data(PATH_ROLE)).name
        item.setText(f"{name}\n{badge}" if badge else name)

    def _show_image(self, path: Path) -> bool:
        pending = self._unsaved.get(str(path))
        image = pending if pending is not None else cv2.imread(str(path))
        if image is None:
            QMessageBox.warning(self, "Image Sanitiser", f"Could not read {path}")
            return False
        self.current_path = path
        self.working = image
        self.findings = []
        self._refresh()
        message = str(path)
        if pending is not None:
            message += " — redacted, unsaved (Save Copy to export)"
        self.statusBar().showMessage(message)
        return True

    # -- scanning -----------------------------------------------------
    def scan_current(self):
        if self.working is None:
            return
        self.findings = [f for det in self.detectors for f in det.scan(self.working)]
        n = len(self.findings)
        self._set_badge(self.current_path, f"⚠ {n} finding(s)" if n else "clean")
        summary = f"{n} finding(s) in {self.current_path.name}"
        payloads = [f.payload for f in self.findings if f.payload]
        if payloads:
            summary += " — decoded: " + "; ".join(payloads)
        self.statusBar().showMessage(summary)
        self._refresh()

    def scan_folder(self):
        # M0: synchronous pass over the sidebar; moves to a worker pool in M3.
        flagged = 0
        for i in range(self.queue.count()):
            path = Path(self.queue.item(i).data(PATH_ROLE))
            image = cv2.imread(str(path))
            if image is None:
                continue
            n = sum(len(det.scan(image)) for det in self.detectors)
            self._set_badge(path, f"⚠ {n} finding(s)" if n else "clean")
            flagged += bool(n)
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
        self._unsaved[str(self.current_path)] = self.working
        message = f"Redacted {count} region(s), verified unreadable"
        if escalated:
            message += f" ({escalated} escalated)"
        if unresolved:
            message = (
                f"WARNING: {unresolved} of {count} region(s) still detectable "
                "after full escalation"
            )
            self._set_badge(self.current_path, "⚠ redaction incomplete")
        else:
            self._set_badge(self.current_path, "redacted — unsaved")
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
        self._unsaved.pop(str(self.current_path), None)
        self._set_badge(self.current_path, "exported ✓")
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
    if "--version" in sys.argv[1:]:
        print(f"image-sanitiser {__version__}")
        return 0
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
