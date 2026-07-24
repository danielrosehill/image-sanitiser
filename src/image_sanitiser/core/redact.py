"""Pixel-level obfuscation primitives.

All functions take and return BGR uint8 numpy arrays and never modify their
input. Regions are (x, y, w, h) bounding boxes; `padding` expands the box by
that fraction of its size on every side before obfuscating — a tight crop can
leave decodable quiet-zone modules around a QR code.
"""

from __future__ import annotations

import cv2
import numpy as np

DEFAULT_PADDING = 0.15


def _clamp_box(img: np.ndarray, x: int, y: int, w: int, h: int, padding: float):
    pad_x, pad_y = int(w * padding), int(h * padding)
    x0 = max(0, x - pad_x)
    y0 = max(0, y - pad_y)
    x1 = min(img.shape[1], x + w + pad_x)
    y1 = min(img.shape[0], y + h + pad_y)
    return x0, y0, x1, y1


def fill(img, box, color=(0, 0, 0), padding=DEFAULT_PADDING):
    """Solid rectangle. Destroys information outright — the escalation endpoint."""
    out = img.copy()
    x0, y0, x1, y1 = _clamp_box(out, *box, padding)
    cv2.rectangle(out, (x0, y0), (x1, y1), color, thickness=-1)
    return out


def pixelate(img, box, blocks=6, padding=DEFAULT_PADDING):
    """Mosaic the region down to `blocks` cells across its longest side."""
    out = img.copy()
    x0, y0, x1, y1 = _clamp_box(out, *box, padding)
    roi = out[y0:y1, x0:x1]
    if roi.size == 0:
        return out
    h, w = roi.shape[:2]
    scale = max(1, max(h, w) // max(1, blocks))
    small = cv2.resize(roi, (max(1, w // scale), max(1, h // scale)),
                       interpolation=cv2.INTER_LINEAR)
    out[y0:y1, x0:x1] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return out


def blur(img, box, strength=0.5, padding=DEFAULT_PADDING):
    """Gaussian blur; kernel scales with region size so strength is size-independent.

    The default is deliberately heavy: this is a redaction tool, and a blur
    that leaves content readable is a failure. The verified-redaction
    pipeline (core/pipeline.py) re-scans every region and escalates if any
    detector can still read it.
    """
    out = img.copy()
    x0, y0, x1, y1 = _clamp_box(out, *box, padding)
    roi = out[y0:y1, x0:x1]
    if roi.size == 0:
        return out
    k = int(max(roi.shape[:2]) * max(0.05, min(strength, 1.0)))
    k = max(3, k | 1)  # odd, >= 3
    out[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (k, k), 0)
    return out


METHODS = {"fill": fill, "pixelate": pixelate, "blur": blur}


def apply(img, finding_or_box, method="pixelate", **kwargs):
    """Apply an obfuscation method to a Finding or a raw (x, y, w, h) box."""
    box = finding_or_box.bbox if hasattr(finding_or_box, "bbox") else finding_or_box
    return METHODS[method](img, box, **kwargs)
