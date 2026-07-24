"""qreader-backed QR detection (optional extra: image-sanitiser[qr-ml]).

qreader detects with a YOLOv8 model (qrdet) and decodes with pyzbar. For
redaction purposes detection is what matters — a code we can locate but not
decode still gets obfuscated.
"""

from __future__ import annotations

import cv2
import numpy as np
from qreader import QReader  # heavy: pulls torch + ultralytics

from image_sanitiser.core.models import Finding
from image_sanitiser.detectors.base import Detector


class QReaderDetector(Detector):
    name = "qr"
    kind = "local"

    def __init__(self):
        self._reader = QReader()

    def scan(self, image: np.ndarray) -> list[Finding]:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        decoded, detections = self._reader.detect_and_decode(
            image=rgb, return_detections=True
        )
        findings = []
        for text, detection in zip(decoded, detections):
            quad = np.asarray(detection["quad_xy"], dtype=np.float32)
            findings.append(
                Finding(
                    detector=self.name,
                    label="qr-code",
                    polygon=quad,
                    confidence=float(detection.get("confidence", 0.0)),
                    payload=text,
                )
            )
        return findings
