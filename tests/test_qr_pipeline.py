"""Core promise of the app, as a test: detect a QR code, redact it, and prove
the redacted image no longer decodes."""

import cv2
import numpy as np
import pytest
import qrcode

from image_sanitiser.core import redact, verify
from image_sanitiser.detectors.qr import OpenCVQRDetector

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
def detector():
    return OpenCVQRDetector()


def test_detects_and_decodes_qr(photo, detector):
    findings = detector.scan(photo)
    assert len(findings) == 1
    assert findings[0].payload == SECRET
    x, y, w, h = findings[0].bbox
    assert w > 50 and h > 50


@pytest.mark.parametrize("method", ["fill", "pixelate"])
def test_redaction_defeats_decoding(photo, detector, method):
    finding = detector.scan(photo)[0]
    redacted = redact.apply(photo, finding, method=method)
    assert verify.is_clean(redacted, [detector]), f"{method} left a readable QR code"


def test_blur_runs_but_is_not_trusted(photo, detector):
    # Blur is cosmetic; the spec forbids it as a default for machine-readable
    # content, so we only assert it executes and changes pixels.
    finding = detector.scan(photo)[0]
    blurred = redact.apply(photo, finding, method="blur", strength=0.6)
    assert not np.array_equal(blurred, photo)


def test_verify_flags_untouched_image(photo, detector):
    assert not verify.is_clean(photo, [detector])
