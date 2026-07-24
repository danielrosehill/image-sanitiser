# Image Sanitiser

Detection-assisted image redaction studio for Linux. Single purpose:
**detect → review → obfuscate → verify → export** images before sharing.
`spec/starter.md` is the authoritative spec; `context/index.md` holds
background; the original voice prompt is archived in `archive/`.

## Status

M0 complete (scaffold, QR detect/redact/verify core, walking-skeleton GUI,
tests). The GUI is **folder-driven**: a thumbnail sidebar is the primary
navigation (open a folder — or an image, which opens its folder), with
per-image state badges and an in-memory cache of redacted-but-unexported
images. Next: **M1** — review UI, manual regions, crop, metadata
audit/strip. Milestone table: spec §12.

## Commands

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest                       # includes offscreen GUI smoke test
image-sanitiser [path]       # run the app (optionally on an image/folder)
```

## Hard rules

- `core/` must never import Qt — it backs a future headless CLI.
- Source images are never modified; exports go to a `redacted/` directory
  as full re-encodes with metadata stripped.
- Every redaction feature lands with a *defeats-detection* test
  (pattern: `tests/test_qr_pipeline.py::test_redaction_defeats_decoding`).
- No obfuscation is decorative — this is PII protection; err on the side
  of caution. Every applied redaction goes through
  `core/pipeline.redact_verified`: re-scan the region and escalate
  (stronger blur → pixelate → fill) until unreadable; failures surface
  loudly. Defaults live in spec §5.
- Cloud detectors (Google Cloud Vision) are opt-in per scan with a consent
  dialog — never a remembered default.

## Stack

Python ≥3.10 (dev on 3.12), PySide6, OpenCV, numpy, Pillow, pyzbar
(system dep: libzbar0). QR scanning is an engine stack (OpenCV + zbar +
optional qreader), findings overlap-merged. Optional
extras: `[qr-ml]` qreader (YOLOv8 QR detection, auto-selected when
installed), `[ocr]`, `[gcv]`. Packaging target: `.deb` (M6).
