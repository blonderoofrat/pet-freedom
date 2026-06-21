# -*- coding: utf-8 -*-
"""Generate the WordPress.org listing assets for Pet Freedom Companion.

These are the DIRECTORY assets (icon, banner) shown on the public plugin page —
they live in the WP.org SVN /assets/ folder, NOT inside the distributed plugin zip.
Run this, then commit the PNGs to `svn` under the repo's /assets path.

- icon-128x128.png, icon-256x256.png  : a map-pin with a paw print (a pet's legal status by place)
- banner-772x250.png, banner-1544x500.png : pin+paw + title + tagline on the project teal

`screenshot-1.png` is NOT generated here — it is a real capture of the plugin's
"Get Started" admin page, taken via WordPress Playground (seamless mode) using
demo/playground/blueprint-admin.json. Re-capture with Playwright if the page changes.

Requires Pillow. Usage: python generate-assets.py [output_dir]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
TEAL = (30, 138, 110); TEAL_D = (20, 104, 84); WHITE = (255, 255, 255)
BOLD = [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf", "DejaVuSans-Bold.ttf"]
REG  = [r"C:\Windows\Fonts\segoeui.ttf",  r"C:\Windows\Fonts\arial.ttf",   "DejaVuSans.ttf"]


def _fontpath(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _fit_font(draw, text, max_w, paths, start, minsz=10):
    fp = _fontpath(paths)
    s = start
    while s > minsz:
        f = ImageFont.truetype(fp, s) if fp else ImageFont.load_default()
        if draw.textlength(text, font=f) <= max_w:
            return f
        s -= 2
    return ImageFont.truetype(fp, minsz) if fp else ImageFont.load_default()


def _pin_paw(img, cx, cy, R, pin=WHITE, paw=TEAL):
    d = ImageDraw.Draw(img)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=pin)
    d.polygon([(cx - R * 0.72, cy + R * 0.70), (cx + R * 0.72, cy + R * 0.70), (cx, cy + R * 2.05)], fill=pin)
    def oval(x, y, w, h): d.ellipse([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=paw)
    for dx, dy in [(-0.52, -0.46), (-0.18, -0.60), (0.18, -0.60), (0.52, -0.46)]:
        oval(cx + R * dx, cy + R * dy, R * 0.24, R * 0.32)   # toe beans
    oval(cx, cy + R * 0.26, R * 0.96, R * 0.74)              # main pad


def make_icon(size, path):
    S = size * 4
    img = Image.new("RGB", (S, S), TEAL)
    _pin_paw(img, S // 2, int(S * 0.40), int(S * 0.27))
    img.resize((size, size), Image.LANCZOS).save(path)


def make_banner(w, h, path):
    S = 2; W, H = w * S, h * S
    img = Image.new("RGB", (W, H), TEAL); d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(TEAL[i] + (TEAL_D[i] - TEAL[i]) * t) for i in range(3)))
    _pin_paw(img, int(H * 0.55), int(H * 0.40), int(H * 0.24))
    tx = int(H * 0.92); maxw = int(W * 0.965) - tx
    title = _fit_font(d, "Pet Freedom Companion", maxw, BOLD, int(H * 0.20))
    sub = _fit_font(d, "Map a pet's legal status across the world", maxw, REG, int(H * 0.115))
    d.text((tx, int(H * 0.30)), "Pet Freedom Companion", font=title, fill=WHITE)
    d.text((tx, int(H * 0.30) + int(title.size * 1.18)), "Map a pet's legal status across the world",
           font=sub, fill=(216, 237, 229))
    img.resize((w, h), Image.LANCZOS).save(path)


if __name__ == "__main__":
    make_icon(256, os.path.join(OUT, "icon-256x256.png"))
    make_icon(128, os.path.join(OUT, "icon-128x128.png"))
    make_banner(1544, 500, os.path.join(OUT, "banner-1544x500.png"))
    make_banner(772, 250, os.path.join(OUT, "banner-772x250.png"))
    print("Wrote icon + banner assets to", OUT)
