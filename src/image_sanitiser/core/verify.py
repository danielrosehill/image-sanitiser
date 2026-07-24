"""Post-redaction verification.

A redaction is only trusted if the detectors that flagged a region can no
longer find anything in the exported image. For QR codes the bar is decode
failure: error correction (up to 30% at level H) means a code that is still
*detected* may also still be *readable*, so partial obfuscation counts as
failure.

M0 semantics are whole-image: any residual finding fails verification. Later
milestones exclude regions the reviewer explicitly dismissed (spec §7).
"""

from __future__ import annotations

import numpy as np

from image_sanitiser.core.models import Finding


def residual_findings(image: np.ndarray, detectors) -> list[Finding]:
    """Re-scan a redacted image; anything returned is a redaction failure."""
    residual: list[Finding] = []
    for detector in detectors:
        residual.extend(detector.scan(image))
    return residual


def is_clean(image: np.ndarray, detectors) -> bool:
    return not residual_findings(image, detectors)
