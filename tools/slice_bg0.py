#!/usr/bin/env python3
"""Slice images/background.webp into three parallax planes for the multiplane
background (world 0). Run from the repo root:  python3 tools/slice_bg0.py

  far  = sky + clouds + mountains (bottom-feathered, slides at 1x)
  mid  = tree line only — green pixels are kept, sky/mountains masked out, so
         the far layer shows through the gaps between bushes
  near = grass + water strip (horizontally uniform, so it can slide fast)

Re-run any time the source painting changes; outputs land in images/.
"""
import numpy as np
from PIL import Image, ImageFilter

SRC = "images/background.webp"

# (name, top, bottom, feathers) — all fractions of source height. Measured from
# the painting: mountains 0.74-0.87, bush line 0.80-0.94, grass 0.91-0.955, water below.
# feather = (top_start, top_end, bottom_start, bottom_end) alpha ramps, or None.
BANDS = [
    ("far",  0.00, 0.93, (None, None, 0.88, 0.93)),
    ("mid",  0.78, 0.95, (0.78, 0.83, 0.91, 0.95)),
    ("near", 0.90, 1.00, (0.90, 0.925, None, None)),
]


def vfeather(y0, y1, hsrc, ft0, ft1, fb0, fb1):
    # feather fractions are source-absolute; convert to band-local rows
    a = np.ones(y1 - y0, dtype=np.float32)
    if ft0 is not None:
        t0 = max(0, int(ft0 * hsrc) - y0); t1 = max(0, int(ft1 * hsrc) - y0)
        a[:t0] = 0.0
        a[t0:t1] = np.linspace(0, 1, t1 - t0)
    if fb0 is not None:
        b0 = int(fb0 * hsrc) - y0; b1 = int(fb1 * hsrc) - y0
        a[b1:] = 0.0
        a[b0:b1] = np.linspace(1, 0, b1 - b0)
    return a


def wrapseam(img, f=None):
    """Blend the band's last columns over its first, so horizontally-tiled
    copies meet with a soft crossfade instead of a hard cut."""
    w, h = img.size
    if f is None: f = max(24, int(w * 0.05))
    end = img.crop((w - f, 0, w, h))
    ramp = np.tile(np.linspace(255, 0, f), (h, 1)).astype(np.uint8)  # end fades out →
    img.paste(end, (0, 0), Image.fromarray(ramp))                    # original shows through
    return img


def main():
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    px = np.asarray(im).astype(np.int16)
    for name, ftop, fbot, (ft0, ft1, fb0, fb1) in BANDS:
        y0, y1 = int(ftop * h), int(fbot * h)
        band = im.crop((0, y0, w, y1))
        alpha = (vfeather(y0, y1, h, ft0, ft1, fb0, fb1)[:, None] * 255).astype(np.uint8)
        alpha = np.repeat(alpha, w, axis=1)
        if name == "mid":
            # keep only foliage: green channel dominates blue (bushes yes,
            # blue-grey mountains and sky no). Blur softens the cutout edges.
            r, g, b = px[y0:y1, :, 0], px[y0:y1, :, 1], px[y0:y1, :, 2]
            keep = ((g > b + 4) & (g > r + 6)).astype(np.uint8) * 255
            keep = np.asarray(Image.fromarray(keep).filter(ImageFilter.GaussianBlur(3)))
            alpha = (alpha.astype(np.uint16) * keep // 255).astype(np.uint8)
        out = band.convert("RGBA")
        out.putalpha(Image.fromarray(alpha))
        if name != "near":                    # near strip is horizontally uniform — no seam
            wrapseam(out)                     # blends RGBA, cutout included
        out.save(f"images/bg0-{name}.webp", quality=85, method=6)
        print(f"bg0-{name}.webp  rows {y0}-{y1} of {h}  ({w}x{y1-y0})")

    # preview: composite the planes over a sky gradient with exaggerated offsets
    prev = Image.new("RGB", (w, h))
    grad = np.zeros((h, w, 3), dtype=np.uint8)
    top, bot = np.array([79, 182, 245]), np.array([159, 216, 251])
    for y in range(h):
        grad[y, :] = (top + (bot - top) * (y / h)).astype(np.uint8)
    prev = Image.fromarray(grad)
    for name, ftop, fbot, _ in BANDS:
        layer = Image.open(f"images/bg0-{name}.webp")
        off = {"far": 0, "mid": 260, "near": 620}[name]  # fake speed difference
        for tile in range(-1, 2):
            prev.paste(layer, (tile * w + off, int(ftop * h)), layer)
    prev.save("tools/bg0-preview.png")
    print("tools/bg0-preview.png written — eyeball it before shipping")


if __name__ == "__main__":
    main()
