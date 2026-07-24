"""Core promise of the app, as tests: detect a QR code, redact it with ANY
method, and prove the redacted image no longer reads."""

import cv2
import numpy as np
import pytest
import qrcode

from image_sanitiser.core import pipeline, redact, verify
from image_sanitiser.core.models import Finding
from image_sanitiser.detectors.base import Detector
from image_sanitiser.detectors.qr import OpenCVQRDetector, QRDetectorStack

SECRET = "https://example.com/reset?token=super-secret-12345"


def synthetic_photo() -> np.ndarray:
    """A QR code (error correction H — the most damage-tolerant) on a gradient."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=4
    )
    qr.add_data(SECRET)
    qr.make(fit=True)
    code = np.array(qr.make_image(fill_color="black", back_color="white").convert("RGB"))
    gradient = np.linspace(80, 190, 1200, dtype=np.uint8)
    canvas = np.dstack([np.tile(gradient, (900, 1))] * 3)
    h, w, _ = code.shape
    canvas[200:200 + h, 300:300 + w] = code
    return cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR)


@pytest.fixture(scope="module")
def photo():
    return synthetic_photo()


@pytest.fixture(scope="module")
def stack():
    return QRDetectorStack()


def test_detects_and_decodes_qr(photo):
    findings = OpenCVQRDetector().scan(photo)
    assert len(findings) == 1
    assert findings[0].payload == SECRET
    x, y, w, h = findings[0].bbox
    assert w > 50 and h > 50


def test_stack_merges_all_available_engines(photo, stack):
    assert len(stack.engines) >= 1
    findings = stack.scan(photo)
    assert len(findings) == 1  # engines agree; overlap-merged into one finding
    assert findings[0].payload == SECRET


@pytest.mark.parametrize("method", ["fill", "pixelate", "blur"])
def test_redaction_defeats_every_engine(photo, stack, method):
    """Any method at default settings must leave nothing readable — blur is
    a redaction method here, not a cosmetic effect."""
    finding = stack.scan(photo)[0]
    redacted = redact.apply(photo, finding, method=method)
    assert verify.is_clean(redacted, [stack]), f"{method} left a readable code"


def test_verify_flags_untouched_image(photo, stack):
    assert not verify.is_clean(photo, [stack])


class SolidFillOnlyDetector(Detector):
    """Stub that stays 'triggered' until the region is a uniform solid block —
    drives the escalation ladder all the way to its endpoint."""

    name = "stub-strict"

    def __init__(self, bbox):
        self._bbox = bbox

    def scan(self, image):
        x, y, w, h = self._bbox
        roi = image[y:y + h, x:x + w]
        if roi.std() < 1.0:
            return []
        polygon = np.asarray(
            [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], dtype=np.float32
        )
        return [Finding(detector=self.name, label="stub", polygon=polygon)]


def test_escalation_ladder_reaches_fill(photo):
    finding = OpenCVQRDetector().scan(photo)[0]
    strict = SolidFillOnlyDetector(finding.bbox)
    result = pipeline.redact_verified(
        photo, finding, [strict], method="blur", strength=0.3
    )
    assert result.clean
    assert result.escalated
    assert result.method_used == "fill"


def test_no_escalation_when_first_method_verifies(photo, stack):
    finding = stack.scan(photo)[0]
    result = pipeline.redact_verified(photo, finding, [stack], method="pixelate")
    assert result.clean and not result.escalated
