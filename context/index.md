# Context

- The user runs Kubuntu (KDE) on their laptop; the app targets Ubuntu/Linux
  desktop first.
- Python tooling is uv-only (no bare pip/venv) per the user's global
  conventions.
- The user referenced a local Python QR-detection utility that "runs locally
  and works beautifully" and wants it integrated. Best match: **qreader**
  (YOLOv8 detection via qrdet + pyzbar decode). It is wired in as the
  optional `[qr-ml]` extra and auto-selected when installed; the
  dependency-free OpenCV detector is the default engine.
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
