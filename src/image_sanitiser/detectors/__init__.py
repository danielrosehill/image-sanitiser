"""Detector plugins.

`default_detectors()` returns the best available engine for each detection
class in the current environment (e.g. qreader-based QR detection when the
qr-ml extra is installed, OpenCV otherwise).
"""

from image_sanitiser.detectors.qr import best_available


def default_detectors():
    return [best_available()]
