"""Verified redaction: apply → re-scan → escalate until unreadable.

Design rule (from the project brief): err on the side of caution. No
obfuscation method is decorative. Whatever the reviewer picks, the pipeline
keeps escalating — stronger blur → heavy pixelate → solid fill → fill with
extra padding — until the detectors can no longer read anything in the
region. The reviewer's choice sets the starting aesthetic, not the safety
level.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from image_sanitiser.core import redact, verify
from image_sanitiser.core.models import Finding


@dataclass
class RedactionResult:
    image: np.ndarray
    method_used: str
    params: dict = field(default_factory=dict)
    escalated: bool = False
    clean: bool = False


def _ladder(method: str, params: dict) -> list[tuple[str, dict]]:
    steps: list[tuple[str, dict]] = [(method, params)]
    if method == "blur":
        strength = params.get("strength", 0.5)
        steps.append(("blur", {**params, "strength": min(1.0, strength * 2)}))
    if method != "pixelate":
        steps.append(("pixelate", {"blocks": 4}))
    steps.append(("fill", {}))
    steps.append(("fill", {"padding": 0.35}))
    return steps


def redact_verified(
    image: np.ndarray,
    finding: Finding,
    detectors,
    method: str = "pixelate",
    **params,
) -> RedactionResult:
    """Redact one finding and guarantee, by re-scanning, that it is unreadable."""
    last: RedactionResult | None = None
    for i, (step_method, step_params) in enumerate(_ladder(method, params)):
        candidate = redact.apply(image, finding, method=step_method, **step_params)
        clean = verify.region_is_clean(candidate, finding.bbox, detectors)
        last = RedactionResult(
            candidate, step_method, step_params, escalated=i > 0, clean=clean
        )
        if clean:
            return last
    return last  # ladder exhausted; caller must surface clean=False loudly
