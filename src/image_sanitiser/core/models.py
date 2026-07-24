"""Data model shared by detectors, the redaction engine, and the GUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class FindingStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    APPLIED = "applied"


@dataclass
class Finding:
    """A region of an image flagged as sensitive by a detector (or a human)."""

    detector: str
    label: str
    polygon: np.ndarray  # (N, 2) float32, image pixel coordinates
    confidence: float | None = None
    payload: str | None = None  # e.g. decoded QR content, OCR'd text
    status: FindingStatus = FindingStatus.PENDING

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Axis-aligned (x, y, w, h) box around the polygon."""
        xs = self.polygon[:, 0]
        ys = self.polygon[:, 1]
        x0, y0 = int(np.floor(xs.min())), int(np.floor(ys.min()))
        x1, y1 = int(np.ceil(xs.max())), int(np.ceil(ys.max()))
        return x0, y0, x1 - x0, y1 - y0
