#!/usr/bin/env python3
"""Compose AI boss bakes into game-ready sprites (same filenames as before).

The raw render is tight-cropped, the cannon bore (leftmost gun pixels) is
measured from the alpha mask, and the canvas is padded so the bore lands on
the muzzle fractions the engine already uses. Damage states reuse the seeded
soot/ember machinery from compose_bosses. Also composes the AI ring into the
287x520 cell the engine's RING3D_FRAME expects.

Run from the repo root:  python3 tools/compose_boss_ai.py
"""
from PIL import Image
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose_bosses import soot

SRC = "/tmp/opencode/i23d"
# game constants (index.html startBoss): bore fractions per boss tier
TIERS = {"cruiser": (-0.24, -0.18), "gundeck": (-0.34, 0.04), "dread": (-0.42, 0.08)}
MAXW = 1500


def bore_pixel(im):
    """Centroid of opaque pixels in the leftmost 6% band = the gun mouth."""
    a = np.asarray(im)[:, :, 3] > 24
    cols = np.where(a.any(0))[0]
    x0 = cols.min()
    band = a[:, x0:x0 + max(4, int(im.width * 0.06))]
    ys, xs = np.where(band)
    return x0 + xs.mean(), ys.mean()


def pad_to_bore_px(im, bx, by, fx, fy):
    """Pad so the bore pixel sits at (0.5+fx, 0.5+fy) of the final canvas."""
    W0, H0 = im.size
    a = 0.5 + fx
    padL = (a * W0 - bx) / (1 - a)
    if padL < 0:
        padL = 0
        padR = bx / a - W0
    else:
        padR = 0
    b = 0.5 + fy
    padT = (b * H0 - by) / (1 - b)
    if padT < 0:
        padT = 0
        padB = by / b - H0
    else:
        padB = 0
    W, H = int(W0 + padL + padR), int(H0 + padT + padB)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(im, (int(padL), int(padT)))
    return out, (bx + padL, by + padT)


def bosses():
    for name, (fx, fy) in TIERS.items():
        im = Image.open(f"{SRC}/ai_{name}.png").convert("RGBA")
        l, t, r, b = im.getbbox()
        im = im.crop((l, t, r, b))
        bx, by = bore_pixel(im)
        im, (bx, by) = pad_to_bore_px(im, bx, by, fx, fy)
        if im.width > MAXW:
            k = MAXW / im.width
            im = im.resize((MAXW, int(im.height * k)), Image.LANCZOS)
            bx, by = bx * k, by * k
        W, H = im.size
        spots = [(0.42, 0.55), (0.62, 0.38), (0.30, 0.42), (0.72, 0.62), (0.52, 0.70)]
        dmg = soot(im, [(W * a, H * b) for a, b in spots[:4]], seed=hash(name) & 0xffff,
                   darken=0.06, embers=[(W * 0.45, H * 0.5)])
        wrk = soot(im, [(W * a, H * b) for a, b in spots], seed=hash(name) & 0xffff,
                   darken=0.14, embers=[(W * 0.45, H * 0.5), (W * 0.66, H * 0.35),
                                        (W * 0.30, H * 0.45), (W * 0.55, H * 0.66)])
        im.save(f"images/boss3d-{name}.webp", quality=88, method=6)
        dmg.save(f"images/boss3d-{name}-damaged.webp", quality=88, method=6)
        wrk.save(f"images/boss3d-{name}-wrecked.webp", quality=88, method=6)
        print(f"boss3d-{name}.webp {W}x{H} bore frac ({bx / W - 0.5:+.3f}, {by / H - 0.5:+.3f}) target ({fx:+.3f}, {fy:+.3f})")


def ring():
    """Compose the painted ring ref straight into the 287x520 cell.

    Hole is measured from the center row/col runs and cut as an ellipse —
    flood fills leak through anti-aliased seams in the painted outline.
    """
    im = Image.open("images/generated-refs/ring.png").convert("RGB")
    a = np.asarray(im)
    nonwhite = a.min(-1) < 235   # uint8! ~0.92*255
    H, W = nonwhite.shape
    cy, cx = H // 2, W // 2
    row = np.where(nonwhite[cy])[0]
    col = np.where(nonwhite[:, cx])[0]
    hx0, hx1 = row[row < cx].max(), row[row > cx].min()   # inner edges on row
    hy0, hy1 = col[col < cy].max(), col[col > cy].min()
    hole_w, hole_h = hx1 - hx0, hy1 - hy0
    yy, xx = np.mgrid[0:H, 0:W]
    ell = (((xx - cx) / (hole_w / 2)) ** 2 + ((yy - cy) / (hole_h / 2)) ** 2) <= 1.12
    whiteish = ~nonwhite
    hole = whiteish & ell
    alpha = np.where(nonwhite | hole, 255, 0).astype(np.uint8)
    rgba = np.dstack([a, alpha])
    ys, xs = np.where(alpha > 0)
    l, t, r, b = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    im2 = Image.fromarray(rgba[t:b, l:r])
    k = 301.0 / hole_h
    im2 = im2.resize((max(1, int(im2.width * k)), max(1, int(im2.height * k))), Image.LANCZOS)
    im2 = im2.resize((287, max(1, int(im2.height * 287 / im2.width))), Image.LANCZOS)
    cell = Image.new("RGBA", (287, 520), (0, 0, 0, 0))
    cell.paste(im2, (0, (520 - im2.height) // 2), im2)
    cell.save("images/ring-3d-v2.webp", quality=90, method=6)
    print(f"ring-3d-v2.webp 287x520 from ref, hole {hole_w}x{hole_h}px k={k:.3f}")


if __name__ == "__main__":
    bosses()
    ring()
