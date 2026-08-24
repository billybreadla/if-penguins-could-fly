#!/usr/bin/env python3
"""Slice every painted world into three parallax planes — the multiplane pass
that tools/slice_bg0.py did for world 0, generalized to the six world paintings
(sunset, aurora, snowy peaks, outer space, dusty hills, storm).

  far  = the whole upper painting: sky + landforms, bottom-feathered (1x)
  mid  = upper ground/sea strip, feathered top + bottom (2.2x at runtime)
  near = lower ground/sea strip, top-feathered (3.8x at runtime)

World 0 keeps its own slicer (its tree-line mid needs the green cutout); here
the mid plane is a plain feathered band — every painting's ground/sea is
horizontally near-uniform, so the strips tile cleanly at speed. No wrap-seam
blend: these paintings are authored with matching first/last columns (they
tiled raw under drawTiledBg), and ghosting the end columns over the start
double-exposes any cloud that crosses the edge.

Run from the repo root:
  python3 tools/slice_world.py                 # slice every world
  python3 tools/slice_world.py --only 3        # one world
  python3 tools/slice_world.py --src=images/world-sunset-v5.webp
Outputs images/bg{N}-{far,mid,near}.webp + tools/worlds-preview.png.
The (top, bot) fractions below MUST match the WORLD_BANDS table in index.html.
"""
import sys
import numpy as np
from PIL import Image

# world -> source painting, base-gradient stops (sky, ground — also the runtime
# draw colors), and bands. Band tuple = (top, bottom, feather), fractions of
# source height; feather = (top_start, top_end, bottom_start, bottom_end) alpha
# ramps in source-absolute fractions, or None for a hard edge.
WORLDS = {
    1: {"src": "images/world-sunset-v5.webp", "sky": (188, 51, 91), "ground": (156, 82, 98), "bands": {
        "far":  (0.00, 0.90, (None, None, 0.84, 0.90)),
        "mid":  (0.86, 0.96, (0.86, 0.90, 0.92, 0.96)),
        "near": (0.92, 1.00, (0.92, 0.96, None, None)),
    }},
    2: {"src": "images/world-aurora-v5.webp", "sky": (0, 17, 68), "ground": (19, 104, 193), "bands": {
        "far":  (0.00, 0.88, (None, None, 0.82, 0.88)),
        "mid":  (0.86, 0.96, (0.86, 0.90, 0.92, 0.96)),
        "near": (0.92, 1.00, (0.92, 0.96, None, None)),
    }},
    3: {"src": "images/world-snowy-peaks-v5.webp", "sky": (90, 202, 249), "ground": (84, 183, 243), "bands": {
        "far":  (0.00, 0.86, (None, None, 0.80, 0.86)),
        "mid":  (0.84, 0.96, (0.84, 0.88, 0.92, 0.96)),
        "near": (0.92, 1.00, (0.92, 0.96, None, None)),
    }},
    4: {"src": "images/world-outer-space-v5.webp", "sky": (3, 8, 47), "ground": (11, 47, 116), "bands": {
        "far":  (0.00, 0.90, (None, None, 0.84, 0.90)),
        "mid":  (0.88, 0.97, (0.88, 0.92, 0.94, 0.97)),
        "near": (0.93, 1.00, (0.93, 0.96, None, None)),
    }},
    5: {"src": "images/world-dusty-hills-v5.webp", "sky": (54, 148, 183), "ground": (191, 81, 49), "bands": {
        "far":  (0.00, 0.84, (None, None, 0.78, 0.84)),
        "mid":  (0.82, 0.94, (0.82, 0.86, 0.90, 0.94)),
        "near": (0.90, 1.00, (0.90, 0.94, None, None)),
    }},
    # world 6 (boss skies) shares the storm painting with world 7
    7: {"src": "images/world-storm-v5.webp", "sky": (11, 12, 51), "ground": (1, 12, 60), "bands": {
        "far":  (0.00, 0.90, (None, None, 0.84, 0.90)),
        "mid":  (0.88, 0.97, (0.88, 0.92, 0.94, 0.97)),
        "near": (0.93, 1.00, (0.93, 0.96, None, None)),
    }},
}


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
    """(Unused for the world paintings — see docstring. Kept for reference.)"""
    w, h = img.size
    if f is None: f = max(24, int(w * 0.05))
    end = img.crop((w - f, 0, w, h))
    ramp = np.tile(np.linspace(255, 0, f), (h, 1)).astype(np.uint8)  # end fades out →
    img.paste(end, (0, 0), Image.fromarray(ramp))                    # original shows through
    return img


def slice_world(world, spec):
    im = Image.open(spec["src"]).convert("RGB")
    w, h = im.size
    for name, (ftop, fbot, (ft0, ft1, fb0, fb1)) in spec["bands"].items():
        y0, y1 = int(ftop * h), int(fbot * h)
        band = im.crop((0, y0, w, y1))
        alpha = (vfeather(y0, y1, h, ft0, ft1, fb0, fb1)[:, None] * 255).astype(np.uint8)
        alpha = np.repeat(alpha, w, axis=1)
        out = band.convert("RGBA")
        out.putalpha(Image.fromarray(alpha))
        out.save(f"images/bg{world}-{name}.webp", quality=85, method=6)
        print(f"bg{world}-{name}.webp  rows {y0}-{y1} of {h}  ({w}x{y1 - y0})")


def preview():
    """Composite every world's planes over its own base gradient with
    exaggerated offsets — the same eyeball check as bg0-preview.png."""
    names = sorted(WORLDS)
    tw, th = 460, 306
    sheet = Image.new("RGB", (tw * 3, th * ((len(names) + 2) // 3)), "#111")
    for i, world in enumerate(names):
        spec = WORLDS[world]
        im = Image.open(spec["src"]).convert("RGB")
        w, h = im.size
        grad = np.zeros((h, w, 3), dtype=np.uint8)
        top, bot = np.array(spec["sky"]), np.array(spec["ground"])
        for y in range(h):
            grad[y, :] = (top + (bot - top) * (y / h)).astype(np.uint8)
        prev = Image.fromarray(grad)
        for name, (ftop, fbot, _) in spec["bands"].items():
            layer = Image.open(f"images/bg{world}-{name}.webp")
            off = {"far": 0, "mid": 260, "near": 620}[name]   # fake speed difference
            for tile in range(-1, 2):
                prev.paste(layer, (tile * w + off, int(ftop * h)), layer)
        prev = prev.resize((tw, th))
        sheet.paste(prev, ((i % 3) * tw, (i // 3) * th))
    sheet.save("tools/worlds-preview.png")
    print("tools/worlds-preview.png written — eyeball it before shipping")


def main():
    only = src = None
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            only = int(a.split("=")[1])
        elif a.startswith("--src="):
            src = a.split("=", 1)[1]          # slice just this painting
            matches = [w for w, s in WORLDS.items() if s["src"] == src]
            if not matches:
                sys.exit(f"no band table for {src} — add one to WORLDS first")
            only = matches[0]
    for world, spec in sorted(WORLDS.items()):
        if only is not None and world != only:
            continue
        slice_world(world, spec)
    preview()


if __name__ == "__main__":
    main()
