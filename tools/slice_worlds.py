#!/usr/bin/env python3
"""Cut a foreground parallax band from each world painting (roadmap #3).

Each world gets ONE near layer: a bottom band that slides faster than the
full painting behind it (drawBackground draws the painting tiled at 1x, then
this band on top at ~3x). Band tops are measured per painting so that no
ground object straddles the feathered edge — everything below the cut is
foreground, everything above stays in the static sky layer.

Run from the repo root:  python3 tools/slice_worlds.py
Outputs images/w{N}-near.webp + tools/worlds-preview.png. Re-run any time a
source painting changes.
"""
from PIL import Image
import numpy as np

# world -> (source file, band top, feather end). Fractions of source height.
WORLDS = {
    1: ("images/world-sunset-v5.webp",      0.76, 0.81),  # cliffs top ~0.82
    2: ("images/world-aurora-v5.webp",      0.76, 0.81),  # ridge top ~0.80
    3: ("images/world-snowy-peaks-v5.webp", 0.55, 0.60),  # summit ~0.63
    4: ("images/world-outer-space-v5.webp", 0.77, 0.82),  # moon ridge ~0.82
    5: ("images/world-dusty-hills-v5.webp", 0.62, 0.67),  # rock tops ~0.68
    7: ("images/world-storm-v5.webp",       0.78, 0.83),  # peaks ~0.83 (6 shares this)
}


def wrapseam(img, f=None):
    """Blend the band's last columns over its first so tiled copies meet in a
    soft crossfade instead of a hard cut."""
    w, h = img.size
    if f is None:
        f = max(24, int(w * 0.05))
    end = img.crop((w - f, 0, w, h))
    ramp = np.tile(np.linspace(255, 0, f), (h, 1)).astype(np.uint8)
    img.paste(end, (0, 0), Image.fromarray(ramp))
    return img


def main():
    for world, (src, ftop, ffeather) in WORLDS.items():
        im = Image.open(src).convert("RGB")
        w, h = im.size
        y0 = int(ftop * h)
        band = im.crop((0, y0, w, h)).convert("RGBA")
        # feather the top edge so it melts into the identical static painting
        n = int((ffeather - ftop) * h)
        alpha = np.ones(h - y0, dtype=np.float32)
        alpha[:n] = np.linspace(0, 1, n)
        band.putalpha(Image.fromarray((alpha[:, None] * 255).astype(np.uint8)
                                      .repeat(w, axis=1)))
        wrapseam(band)
        out = f"images/w{world}-near.webp"
        band.save(out, quality=85, method=6)
        print(f"{out}  rows {y0}-{h} of {h}  ({w}x{h - y0})")

    # preview: each painting with its near band shifted right (fake parallax)
    prev_w, prev_h = 700, 466
    prev = Image.new("RGB", (prev_w * 3, prev_h * 2), "#222")
    for i, (world, (src, ftop, _)) in enumerate(sorted(WORLDS.items())):
        im = Image.open(src).convert("RGB").resize((prev_w, prev_h))
        near = Image.open(f"images/w{world}-near.webp")
        s = prev_h / im.height
        nw, nh = int(near.width * s), int(near.height * s)
        near = near.resize((nw, nh))
        off = int(prev_w * 0.06)
        for tile in (-1, 0, 1):
            im.paste(near, (tile * nw + off, int(ftop * prev_h)), near)
        prev.paste(im, ((i % 3) * prev_w, (i // 3) * prev_h))
    prev.save("tools/worlds-preview.png")
    print("tools/worlds-preview.png written — eyeball it before shipping")


if __name__ == "__main__":
    main()
