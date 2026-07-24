"""Generate the app icon (256x256 PNG): a photo glyph, part-pixelated, with a
redaction bar. Placeholder aesthetics, deterministic output — rerun and
recommit to replace:

    .venv/bin/python packaging/generate-icon.py
"""

import random

from PIL import Image, ImageDraw

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# app tile
d.rounded_rectangle((8, 8, 248, 248), radius=44, fill=(28, 32, 41, 255))
# photo card
d.rounded_rectangle((40, 56, 216, 200), radius=12, fill=(236, 239, 244, 255))
# sky, sun, mountains — the classic photo glyph
d.rectangle((52, 68, 204, 154), fill=(120, 170, 220, 255))
d.ellipse((160, 78, 184, 102), fill=(255, 214, 90, 255))
d.polygon([(52, 154), (100, 104), (136, 154)], fill=(70, 110, 90, 255))
d.polygon([(112, 154), (152, 116), (204, 154)], fill=(90, 130, 105, 255))
# pixelation mosaic over the right side of the photo
random.seed(7)
BLOCK = 18
for gx in range(138, 204, BLOCK):
    for gy in range(68, 154, BLOCK):
        g = random.choice([125, 150, 175, 200])
        d.rectangle(
            (gx, gy, min(gx + BLOCK, 204), min(gy + BLOCK, 154)), fill=(g, g, g, 255)
        )
# redaction bar
d.rounded_rectangle((52, 164, 204, 188), radius=6, fill=(15, 15, 18, 255))

img.save("packaging/image-sanitiser.png")
print("wrote packaging/image-sanitiser.png")
