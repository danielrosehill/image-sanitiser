# Context

- The user runs Kubuntu (KDE) on their laptop; the app targets Ubuntu/Linux
  desktop first.
- Python tooling is uv-only (no bare pip/venv) per the user's global
  conventions.
- The QR utility the user was using (confirmed 2026-07-24) is
  **Testausserveri/qrpyora-blur** (MIT): pyzbar detection/decoding +
  polygon-mask Gaussian blur, with a `--data` filter to blur only codes
  carrying a given payload. Its pyzbar engine is adopted into the default
  detector stack; its fixed-strength blur is replaced by size-relative,
  verified obfuscation. qreader (YOLOv8) remains available as the
  `[qr-ml]` extra.
- Design rule from the user (2026-07-24): blur must NOT be treated as
  cosmetic — this app is for PII protection; err on the side of caution
  and make sure redacted content is not readable. Implemented as the
  verified escalation ladder in `core/pipeline.py`.
- Google Cloud Vision integration is desired as an optional cloud toolkit;
  the user has an existing Google Cloud/Workspace footprint. Must remain
  opt-in per scan (privacy irony of uploading unredacted images).
- Requested capabilities, in the user's words: open a folder or photograph;
  scan reports like "QR codes detected in these images"; other detection
  classes running locally; manual cropping and "a couple of blurs"; saving;
  a review function — open a folder, work through a review checklist,
  programmatic review then manual review, compare before and after.
- Explicitly incremental: "We don't need to build it all in one day —
  set up the public repository, create a spec, and iterate from there."
- The user's skill library has adjacent prior art worth mining during later
  milestones: `image-annotation` (bbox UI concepts), `pii-scanner`
  (PII patterns), `image-production__scrub-small-images` (metadata
  scrubbing), `snap-it` (screenshot handling).
- Packaging norm for the user's public desktop tools: `.deb` releases via
  the `linux-packaging__release-dev-project` workflow (as done for dictamic).
- Repo conventions observed: default branch `master`, no LICENSE file until
  deliberately added, Human & AI Authorship section in README.
