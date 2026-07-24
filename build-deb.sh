#!/usr/bin/env bash
# Build the image-sanitiser .deb
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2)}"
PKG=image-sanitiser
ROOT="build/${PKG}_${VERSION}_all"

rm -rf build
mkdir -p "$ROOT/DEBIAN" \
         "$ROOT/usr/bin" \
         "$ROOT/usr/lib/python3/dist-packages" \
         "$ROOT/usr/share/applications" \
         "$ROOT/usr/share/icons/hicolor/256x256/apps" \
         "$ROOT/usr/share/doc/$PKG"

cp -r src/image_sanitiser "$ROOT/usr/lib/python3/dist-packages/"
find "$ROOT/usr/lib/python3/dist-packages" -name '__pycache__' -type d -exec rm -rf {} +

cat > "$ROOT/usr/bin/$PKG" <<'EOF'
#!/usr/bin/python3
from image_sanitiser.gui.app import main

raise SystemExit(main())
EOF
chmod 755 "$ROOT/usr/bin/$PKG"

cp packaging/image-sanitiser.desktop "$ROOT/usr/share/applications/"
cp packaging/image-sanitiser.png     "$ROOT/usr/share/icons/hicolor/256x256/apps/"
cp README.md                         "$ROOT/usr/share/doc/$PKG/"

cat > "$ROOT/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Section: graphics
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pyside6.qtwidgets, python3-opencv, python3-numpy, python3-pyzbar
Maintainer: Daniel Rosehill <public@danielrosehill.com>
Homepage: https://github.com/danielrosehill/image-sanitiser
Description: Detection-assisted image redaction for the Linux desktop
 Single-purpose privacy tool: find QR codes (and, in later versions,
 faces and text PII) in photos, obfuscate them, and verify by
 re-scanning that nothing machine-readable remains.
 .
 Scans run through an engine stack (OpenCV + zbar, plus an optional
 YOLOv8 engine when installed via pip). Every redaction is re-scanned
 and auto-escalated - stronger blur, heavy pixelate, solid fill -
 until no detector can read the region. Exports are re-encoded copies
 with no EXIF/GPS metadata; originals are never modified.
EOF

cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q /usr/share/icons/hicolor || true
exit 0
EOF
chmod 755 "$ROOT/DEBIAN/postinst"

dpkg-deb --build --root-owner-group "$ROOT" "build/${PKG}_${VERSION}_all.deb"
echo "Built: build/${PKG}_${VERSION}_all.deb"
