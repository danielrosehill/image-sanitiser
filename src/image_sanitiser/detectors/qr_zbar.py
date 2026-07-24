"""pyzbar (zbar) detection — QR codes plus 1-D barcodes.

This is the engine used by Testausserveri/qrpyora-blur (MIT), the utility
this project grew out of. Requires the system zbar library
(`sudo apt install libzbar0`); importing this module fails cleanly without
it and the engine is skipped.
"""

from __future__ import annotations

import numpy as np
from pyzbar import pyzbar

from image_sanitiser.core.models import Finding
from image_sanitiser.detectors.base import Detector


class ZbarQRDetector(Detector):
    name = "qr-zbar"
    kind = "local"

    def scan(self, image: np.ndarray) -> list[Finding]:
        findings = []
        for code in pyzbar.decode(image):
            if code.polygon:
                polygon = np.asarray(
                    [(point.x, point.y) for point in code.polygon], dtype=np.float32
                )
            else:
                r = code.rect
                polygon = np.asarray(
                    [
                        (r.left, r.top),
                        (r.left + r.width, r.top),
                        (r.left + r.width, r.top + r.height),
                        (r.left, r.top + r.height),
                    ],
                    dtype=np.float32,
                )
            label = "qr-code" if code.type == "QRCODE" else f"barcode-{code.type.lower()}"
            findings.append(
                Finding(
                    detector=self.name,
                    label=label,
                    polygon=polygon,
                    payload=code.data.decode("utf-8", "replace") or None,
                )
            )
        return findings
