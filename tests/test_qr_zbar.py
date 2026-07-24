"""zbar engine specifics; skipped when the system zbar library is absent."""

import pytest

pytest.importorskip("pyzbar.pyzbar", reason="system libzbar not installed")

from test_qr_pipeline import SECRET, synthetic_photo  # noqa: E402


def test_zbar_detects_and_decodes():
    from image_sanitiser.detectors.qr_zbar import ZbarQRDetector

    findings = ZbarQRDetector().scan(synthetic_photo())
    qr_findings = [f for f in findings if f.label == "qr-code"]
    assert len(qr_findings) == 1
    assert qr_findings[0].payload == SECRET
