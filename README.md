# Image Sanitiser

A desktop app for Ubuntu/Linux whose sole purpose is getting images safe to
share: find QR codes, faces and PII, obfuscate them, strip the metadata —
and then **prove the redaction worked** by re-scanning the export.

Not a general image editor. One loop: **detect → review → obfuscate →
verify → export**. Machines find, the human decides, the machine verifies.

> **Status: early development (M0).** The spec is the main artefact right
> now — see [`spec/starter.md`](spec/starter.md). A walking skeleton exists
> and its core promise is tested: a detected QR code, once redacted, no
> longer decodes.

## Why

Nothing on the Linux desktop combines automatic detection with a redaction
workflow: GNOME Obfuscate is manual-only, Metadata Cleaner ignores pixels,
deface does faces only on the CLI. This app is for the folder of photos you
need to publish — screenshots, apartment listings, hardware photos, event
pictures — where the dangerous stuff (a QR code on a boarding pass, a
visible document, an address in a reflection) is exactly what you forget to
look for.

## What works today (M0)

- Open an image or folder; scan for QR codes (OpenCV built-in, or
  [qreader](https://github.com/Eric-Canas/QReader)'s YOLOv8 detector via the
  `qr-ml` extra — auto-selected when installed); decoded payloads shown so
  you can judge sensitivity.
- Redact findings (pixelate/fill/blur with region padding); save a copy to
  `redacted/` — originals are never touched, metadata is not carried over.
- Verification primitive: re-scan the export; a still-decodable QR fails.

Planned (spec §12): review checklist UI, manual regions + crop,
before/after compare, threaded folder workflow, faces/OCR-PII/barcode
detectors, opt-in Google Cloud Vision, `.deb` packaging.

## Run it

```bash
git clone https://github.com/danielrosehill/image-sanitiser
cd image-sanitiser
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest              # verify the core promise holds on your machine
image-sanitiser     # or: image-sanitiser ~/Pictures/to-publish/
```

## Design notes worth knowing

- **Blur is cosmetic.** QR error correction survives 30% damage and
  pixelated text is attackable, so machine-readable content defaults to
  solid fill / heavy pixelation, and regions are padded 15% beyond the
  detection box.
- **Exports are re-encodes.** No EXIF, GPS, or embedded thumbnail (the
  classic leak: the unredacted original living on as the JPEG preview
  inside the "redacted" file) survives an export.
- **Local by default.** The only network feature, Google Cloud Vision, is
  opt-in per scan behind a consent dialog that spells out what uploading an
  unredacted image means.

## Human & AI Authorship

The concept, requirements, workflow design and product direction are Daniel
Rosehill's. The specification document, code scaffold and tests were written
by Claude (Anthropic), working from Daniel's spoken brief, and are iterated
on under his review.

### About this attribution

This attribution section promotes transparent use of AI tools. Projects that
clearly distinguish human and AI contributions help set a healthy norm for
the broader developer community.
