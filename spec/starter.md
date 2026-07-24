# Image Sanitiser — Starter Specification

A single-purpose desktop GUI for Ubuntu/Linux: prepare images for sharing by
finding sensitive content, destroying it, and proving it's gone. Not a general
image editor — every feature serves one loop:

> **detect → review → obfuscate → verify → export**

Guiding principle: *machines find, the human decides, the machine verifies.*

---

## 1. Why this app should exist

Nothing on the Linux desktop combines automatic detection with a redaction
workflow. The neighbours:

| Tool | What it does | What it lacks |
|---|---|---|
| GNOME Obfuscate | Manual blur/pixelate/block on one image | No detection, no batch, no verification |
| Image Scrubber (everestpipkin, web) | Manual paint + EXIF strip in browser | Manual only, single image, web page |
| Metadata Cleaner / ExifCleaner | Strips file metadata | Pixels untouched |
| deface (CLI) | Automatic face anonymisation | Faces only, no GUI, no review |
| AutoRedact (browser) | Auto-detects sensitive info client-side | Browser-based, no folder workflow |

The gap this app fills: **detection-assisted review of whole folders, with a
verification pass that proves the redaction worked.**

## 2. The core loop

1. **Open** a single image or a folder → images land in a queue.
2. **Scan** (programmatic review): selected detectors run over the queue;
   summary reads like *"QR codes detected in 4 of 61 images."*
3. **Review** each flagged image: every finding is a checklist entry —
   accept (choose obfuscation method) or dismiss (false positive / deliberate).
   Add manual regions the detectors missed.
4. **Manual pass**: crop, brush blurs, resolution reduction.
5. **Verify**: the exported pixels are re-scanned. A QR code that still
   decodes, or a face that still detects, fails the image.
6. **Export** sanitised copies — never in place — with metadata stripped.

## 3. Data model

```python
Finding(
    detector: str,          # "qr", "face", "ocr-pii", "gcv-text", "manual"
    label: str,             # "qr-code", "face", "email-address", ...
    polygon: np.ndarray,    # (N, 2) pixel coords; .bbox derives (x, y, w, h)
    confidence: float | None,
    payload: str | None,    # decoded QR text / OCR'd string — shown in review
    status: pending | accepted | dismissed | applied,
)
```

Per image, the session holds: source path, working pixels, findings list,
review state, export/verification result. (Sidecar JSON persistence for
resumable reviews is a later milestone — see §12.)

## 4. Detection

### 4.1 Local detectors (default, offline)

| Class | Engine | Notes |
|---|---|---|
| QR codes | OpenCV `QRCodeDetector` built in; **qreader** (YOLOv8) via `[qr-ml]` extra | qreader finds rotated/small/damaged codes OpenCV misses; auto-selected when installed. Decoded payload is shown in the review UI so you can judge sensitivity ("this QR opens a WhatsApp chat with your number"). |
| Barcodes | zxing-cpp (multi-format) | M4 |
| Faces | YuNet ONNX via OpenCV | M4. Small, fast, no torch. |
| Text → PII | Tesseract OCR word boxes + pattern pass | M4. Patterns: emails, phone numbers (incl. IL formats), URLs, IBAN, credit cards (Luhn), Israeli ID numbers (checksum-validated). Each matching word box becomes a finding. |
| Metadata audit | Pillow/exiv2 | M1. GPS coords, camera serial, embedded thumbnail presence → findings without regions, resolved by the export-time strip. |

### 4.2 Cloud detectors (opt-in, never default)

**Google Cloud Vision**: `TEXT_DETECTION`, `FACE_DETECTION`,
`LOGO_DETECTION`, `OBJECT_LOCALIZATION`, `LANDMARK_DETECTION` (landmark hits
are themselves a location-leak warning).

- Requires an explicit per-batch consent dialog. The dialog must state the
  obvious irony: *you are uploading the unredacted sensitive image to Google.*
  Cloud scan is a deliberate act each time, never a remembered default.
- Auth via `GOOGLE_APPLICATION_CREDENTIALS` or a key path in settings.
- Results map to the same `Finding` model (`kind="cloud"` detectors).
- Cost guard: show image count × features before sending; first 1,000
  units/feature/month are free, then ~$1.50/1,000.

### 4.3 Detector contract

```python
class Detector(ABC):
    name: str            # "qr"
    kind: str            # "local" | "cloud"
    def scan(self, image: np.ndarray) -> list[Finding]: ...
```

Detectors are pure and stateless per scan. A future registry/entry-point
mechanism can admit third-party detector plugins; for now
`detectors.default_detectors()` returns the best engine per class available
in the environment.

## 5. Obfuscation

| Method | Use | Trust |
|---|---|---|
| `fill` | Solid rectangle | The only method that provably destroys information |
| `pixelate` | Mosaic to N blocks | Good default; block count must be small (≤8 across) |
| `blur` | Gaussian, size-relative strength | **Cosmetic.** Fine for faces-as-courtesy; never sufficient for QR/text |
| `inpaint` | Content-aware removal (cv2.inpaint) | M4; cosmetic, for unobtrusive edits |

- Every method expands the region by a **padding** fraction (default 15%) —
  tight crops leave decodable quiet-zone modules around QR codes.
- Per-class defaults: QR/barcode → `fill` or heavy `pixelate` (QR error
  correction level H survives 30% damage — partial blur is not redaction);
  text/PII → `fill`; faces → `pixelate` or `blur` with a "cosmetic only"
  hint.
- Manual region tools: rectangle and ellipse (M1), freehand brush blur (M4),
  crop (M1).
- **Reduction** (export options, M2): downscale to max dimension, JPEG
  quality, format conversion. Reduction is a privacy feature — it destroys
  fine detail like screen reflections and distant text.

## 6. Review workflow

Image states: `Queued → Scanned (n findings) → In review → Reviewed →
Exported ✓verified`.

- Left dock: queue with thumbnails and state badges.
- Right dock: **checklist** for the current image =
  auto findings (each: accept / method / dismiss) **plus** configurable
  manual checklist items from `~/.config/image-sanitiser/checklist.yaml`,
  e.g. *"Screens/monitors in background?"*, *"Reflections in glasses/windows?"*,
  *"Documents on desk?"*, *"Metadata stripped (auto)"*.
- An image is `Reviewed` only when every checklist entry is resolved.
- Before/after: hold **Space** to peek at the original; split-slider view.
- Keyboard-first: `J/K` next/prev image, `A` accept, `X` dismiss,
  `M` cycle method, `E` export.
- Batch export is gated on all images being `Reviewed` (override with warning).

## 7. Verification pass — the differentiator

After export, re-scan the **exported file** (not the in-memory buffer):

- Run every detector that produced an accepted finding, plus a full QR sweep.
- Any decode or detection overlapping a redacted region ⇒ **FAIL**: the image
  loses its verified badge and the app offers escalation (method → `fill`,
  padding +50%, re-export).
- Findings the reviewer dismissed are excluded from failure matching.
- Metadata check: exported file must carry zero EXIF/XMP/IPTC and no embedded
  thumbnail (a classic leak: the original survives as a JPEG preview inside
  the "redacted" file).
- Exports are always full re-encodes — never byte-partial copies of the
  source file.

Honest limits, documented in-app: verification proves *our detectors can't
read it anymore*, not *nobody can*. Weak pixelation of text is attackable
(Depix-style), mosaic faces can be re-identified. Hence the conservative
defaults above.

## 8. Export

- Output to `<source>/redacted/` (or chosen directory); source files are
  never modified.
- Strip all metadata by default (toggleable per export, default on).
- Optional filename randomisation — original names leak timestamps and
  device conventions.
- Optional session report (JSON/Markdown: per image, findings, decisions,
  verification result). **Off by default** — the report itself is a
  sensitive document.

## 9. Architecture

```
src/image_sanitiser/
├── core/        # numpy/cv2 only — models, redact, verify. NO Qt imports.
├── detectors/   # Detector plugins; best_available() per class
└── gui/         # All PySide6 code
```

- The Qt-free core enables a headless CLI later:
  `image-sanitiser scan DIR --json`, `image-sanitiser redact DIR --preset qr-only`
  — useful for scripted/agent workflows.
- Scans run on `QThreadPool` workers from M3 so the UI never blocks on a
  folder.
- Settings: `~/.config/image-sanitiser/` (TOML + checklist.yaml).
- No telemetry, no network except explicit GCV calls.

## 10. Stack

- Python ≥ 3.10, uv-managed venv
- PySide6 (Qt 6), opencv-python, numpy, Pillow
- Extras: `[qr-ml]` qreader (torch), `[ocr]` pytesseract (+ system
  `tesseract-ocr`), `[gcv]` google-cloud-vision
- Tests: pytest with `QT_QPA_PLATFORM=offscreen`; every redaction feature
  ships with a *defeats-detection* test (see `tests/test_qr_pipeline.py`)

## 11. Packaging

- Dev: `uv venv && uv pip install -e ".[dev]"`
- M6: `.deb` via the existing linux-packaging release workflow (same pattern
  as dictamic), desktop entry + icon; Flatpak considered later.

## 12. Milestones

| # | Scope | Acceptance |
|---|---|---|
| **M0** ✅ | Repo, spec, core primitives (QR detect, fill/pixelate/blur, verify), walking-skeleton GUI (open/scan/redact/save), test suite | `pytest` green: redaction provably defeats decoding; GUI completes the loop headless |
| M1 | Review UI: findings list with accept/dismiss + per-region method; manual rect/ellipse; crop; metadata audit + strip on export; export dir handling | Redact a real screenshot end-to-end without touching the source file |
| M2 | Verification pass wired into export; before/after compare; reduction options | A half-blurred QR code visibly fails verification and escalates |
| M3 | Folder workflow: threaded scans, state badges, checklist pane, keyboard nav, batch export | Review a 50-image folder without UI freeze |
| M4 | Local detectors: faces (YuNet), OCR+PII patterns, barcodes; brush blur; inpaint | Faces and an email address auto-flagged on test corpus |
| M5 | Google Cloud Vision opt-in integration with consent + cost dialog | GCV text findings appear in the same review flow |
| M6 | `.deb` packaging, icon, desktop entry, README screenshots | Installable on stock Kubuntu; launches from menu |

## 13. Open questions

- Final display name — "Image Sanitiser" is the working title; rename is
  cheap right now.
- GCV: which GCP project/billing account; where the key lives (1Password?).
- License: repo currently ships none (all rights reserved by default) —
  add MIT or similar via license-populator?
- Session persistence format for resumable reviews (sidecar JSON vs SQLite).
