"""Detector plugins.

`default_detectors()` returns the default stack: every locally available
engine per detection class, merged (see qr.QRDetectorStack). Cloud
detectors are never included by default.
"""

from image_sanitiser.detectors.qr import QRDetectorStack


def default_detectors():
    return [QRDetectorStack()]
