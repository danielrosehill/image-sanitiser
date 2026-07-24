"""QR code detection.

The default engine is OpenCV's built-in QRCodeDetector: zero extra
dependencies, fine for clean frontal codes. The optional qreader engine
(`pip install image-sanitiser[qr-ml]`) adds a YOLOv8-based detector that
finds codes OpenCV misses — rotated, blurred, small, at an angle — at the
cost of a torch dependency. If qreader is importable it is used
automatically.
"""

from __future__ import annotations

import cv2
import numpy as np

from image_sanitiser.core.models import Finding
from image_sanitiser.detectors.base import Detector


class OpenCVQRDetector(Detector):
    name = "qr"
    kind = "local"

    def scan(self, image: np.ndarray) -> list[Finding]:
        detector = cv2.QRCodeDetector()
        ok, texts, points, _ = detector.detectAndDecodeMulti(image)
        if not ok or points is None:
            return []
        findings = []
        for text, quad in zip(texts, points):
            findings.append(
                Finding(
                    detector=self.name,
                    label="qr-code",
                    polygon=np.asarray(quad, dtype=np.float32).reshape(-1, 2),
                    payload=text or None,
                )
            )
        return findings


def best_available() -> Detector:
    try:
        from image_sanitiser.detectors.qr_ml import QReaderDetector

        return QReaderDetector()
    except ImportError:
        return OpenCVQRDetector()
