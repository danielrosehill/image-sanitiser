"""Detector plugin interface.

A detector inspects an image and returns Findings. Detectors must run
locally unless marked cloud-backed via `kind` — the GUI groups them so cloud
detectors are always opt-in per scan (spec §4.2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from image_sanitiser.core.models import Finding


class Detector(ABC):
    name: str = "base"
    kind: str = "local"  # "local" | "cloud"

    @abstractmethod
    def scan(self, image: np.ndarray) -> list[Finding]:
        """Return findings for a BGR uint8 image."""
