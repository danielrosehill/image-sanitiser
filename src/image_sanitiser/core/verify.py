"""Post-redaction verification.

A redaction is only trusted if detectors can no longer find anything in the
region. For QR codes the bar is decode failure: error correction (up to 30%
at level H) means a code that is still *detected* may also still be
*readable*, so partial obfuscation counts as failure.

Whole-image checks back the export gate; region checks back the per-finding
escalation ladder in core/pipeline.py. Regions the reviewer explicitly
dismissed are excluded at the workflow layer (spec §7).
"""

from __future__ import annotations

import numpy as np

from image_sanitiser.core.models import Finding

Box = tuple[int, int, int, int]


def residual_findings(image: np.ndarray, detectors) -> list[Finding]:
    """Re-scan an image; anything returned is still machine-readable."""
    residual: list[Finding] = []
    for detector in detectors:
        residual.extend(detector.scan(image))
    return residual


def is_clean(image: np.ndarray, detectors) -> bool:
    return not residual_findings(image, detectors)


def _intersects(a: Box, b: Box) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def residuals_in_region(
    image: np.ndarray, bbox: Box, detectors, margin: float = 0.2
) -> list[Finding]:
    """Findings overlapping the (slightly expanded) target region."""
    x, y, w, h = bbox
    grown = (
        int(x - w * margin),
        int(y - h * margin),
        int(w * (1 + 2 * margin)),
        int(h * (1 + 2 * margin)),
    )
    return [f for f in residual_findings(image, detectors) if _intersects(f.bbox, grown)]


def region_is_clean(image: np.ndarray, bbox: Box, detectors) -> bool:
    return not residuals_in_region(image, bbox, detectors)
