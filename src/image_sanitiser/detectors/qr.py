"""QR code detection.

Multiple engines run together and their findings are merged: for a
redaction tool, more detectors mean more caught codes, so every engine
available in the environment gets a vote.

- OpenCV `QRCodeDetector` — always present (core dependency).
- pyzbar (zbar) — the engine behind Testausserveri/qrpyora-blur, the tool
  this project grew out of. Also catches 1-D barcodes. Needs the system
  zbar library; skipped cleanly when missing.
- qreader (YOLOv8) — optional `[qr-ml]` extra; best recall on rotated,
  small, or damaged codes.

Findings from different engines covering the same code are merged by bbox
overlap, preferring the copy that carries a decoded payload.
"""

from __future__ import annotations

import cv2
import numpy as np

from image_sanitiser.core.models import Finding
from image_sanitiser.detectors.base import Detector


class OpenCVQRDetector(Detector):
    name = "qr-opencv"
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


def _iou(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


class QRDetectorStack(Detector):
    """Union of every available QR engine, deduplicated by overlap."""

    name = "qr"
    kind = "local"

    def __init__(self):
        self.engines: list[Detector] = [OpenCVQRDetector()]
        try:
            from image_sanitiser.detectors.qr_zbar import ZbarQRDetector

            self.engines.append(ZbarQRDetector())
        except ImportError:
            pass
        try:
            from image_sanitiser.detectors.qr_ml import QReaderDetector

            self.engines.append(QReaderDetector())
        except ImportError:
            pass

    def scan(self, image: np.ndarray) -> list[Finding]:
        merged: list[Finding] = []
        for engine in self.engines:
            for finding in engine.scan(image):
                dup = next(
                    (i for i, m in enumerate(merged) if _iou(m.bbox, finding.bbox) > 0.5),
                    None,
                )
                if dup is None:
                    merged.append(finding)
                elif finding.payload and not merged[dup].payload:
                    merged[dup] = finding
        return merged
