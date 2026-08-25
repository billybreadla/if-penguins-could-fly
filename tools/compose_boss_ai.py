#!/usr/bin/env python3
"""Compose AI boss bakes into game-ready sprites (same filenames as before).

The raw render is tight-cropped, the cannon bore (leftmost gun pixels) is
measured from the alpha mask, and the canvas is padded so the bore lands on
the muzzle fractions the engine already uses. Damage states reuse the seeded
soot/ember machinery from compose_bosses. Also composes the AI ring into the
287x520 cell the engine's RING3D_FRAME expects.

Run from the repo root:  python3 tools/compose_boss_ai.py
"""
from PIL import Image, ImageFilter
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
    """Compose the painted ring ref into the 287x520 cell with baked depth.

    Hole is measured from the center row/col runs and cut as a TRANSPARENT
    ellipse — flood fills leak through anti-aliased seams in the painted
    outline, and the hole must stay see-through (penguin flies through).
    Depth cues baked into the paint: torus inner-wall shading visible
    through the hole, top-left form shading (warm lit / cool shade),
    a luminance bevel that stamps the ornament relief, specular glints,
    plus a soft drop shadow composited in the cell.
    """
    im = Image.open("images/generated-refs/ring.png").convert("RGB")
    a = np.asarray(im).astype(np.float32)
    nonwhite = a.min(-1) < 235   # uint8! ~0.92*255
    H, W = nonwhite.shape
    cy, cx = H // 2, W // 2
    row = np.where(nonwhite[cy])[0]
    col = np.where(nonwhite[:, cx])[0]
    hx0, hx1 = row[row < cx].max(), row[row > cx].min()   # inner edges on row
    hy0, hy1 = col[col < cy].max(), col[col > cy].min()
    ox0, ox1 = row.min(), row.max()                       # outer edges
    oy0, oy1 = col.min(), col.max()
    hole_w, hole_h = hx1 - hx0, hy1 - hy0
    rr_out = max((oy1 - oy0) / hole_h, (ox1 - ox0) / hole_w)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rr = np.hypot((xx - cx) / (hole_w / 2), (yy - cy) / (hole_h / 2))
    theta = np.arctan2(yy - cy, xx - cx)                  # y down: -pi/2 = up

    # alpha: paint opaque, hole fully transparent, eat the AA seam near it
    alpha = np.where(nonwhite, 255.0, 0.0)
    alpha[rr <= 1.12] = 0
    alpha[(rr <= 1.18) & (a.min(-1) > 215)] = 0
    band = alpha > 0

    # 1. torus inner wall seen through the hole (dark at top, lit at bottom)
    wall = np.clip((1.0 + 0.32 * (rr_out - 1) - rr) / (0.32 * (rr_out - 1)), 0, 1) ** 1.4 * band
    f = 0.86 + 0.30 * np.sin(theta)
    a *= (1 + (f - 1) * wall)[..., None]

    # 2. form shading from top-left, warm lit side / cool shade side
    thL = np.deg2rad(-135)
    c = np.cos(theta - thL)
    wform = np.clip((rr - 1.18) / 0.45, 0, 1) * np.clip((rr_out * 1.04 - rr) / 0.30, 0, 1) * band
    for i, k in enumerate((0.11, 0.08, 0.03)):
        a[..., i] *= 1 + k * c * wform

    # 3. bevel: relief from the blurred luminance field, light top-left
    L = np.asarray(Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("L").filter(
        ImageFilter.GaussianBlur(2))).astype(np.float32)
    gy, gx = np.gradient(L)
    a += (26 * np.tanh((gx + gy) / 28))[..., None] * band[..., None]

    # 4. specular glints (main up-left, rim light lower-right)
    rmid = (1 + rr_out) / 2
    for tg, str_ in ((np.deg2rad(-118), 0.70), (np.deg2rad(52), 0.35)):
        g = np.exp(-((theta - tg) / 0.40) ** 2 - ((rr - rmid) / (0.30 * (rr_out - 1))) ** 2) * band
        a += (np.array([255, 246, 218]) * (g * str_)[..., None])

    rgba = np.dstack([a.clip(0, 255), alpha]).astype(np.uint8)
    ys, xs = np.where(alpha > 0)
    l, t, r, b = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    im2 = Image.fromarray(rgba[t:b, l:r])
    k = 301.0 / hole_h
    im2 = im2.resize((max(1, int(im2.width * k)), max(1, int(im2.height * k))), Image.LANCZOS)
    im2 = im2.resize((287, max(1, int(im2.height * 287 / im2.width))), Image.LANCZOS)

    # cell + soft drop shadow (fits in whatever padding the cell has)
    cell = Image.new("RGBA", (287, 520), (0, 0, 0, 0))
    top = (520 - im2.height) // 2
    off = max(0, min(12, top - 2))
    sh = np.zeros((520, 287), np.float32)
    sh[top:top + im2.height, :im2.width] = np.asarray(im2)[..., 3]
    sh = np.asarray(Image.fromarray(sh.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(8))).astype(np.float32)
    sh = np.roll(sh, off, axis=0) * 0.36
    cell.paste(Image.new("RGBA", (287, 520), (22, 16, 42, 255)), (0, 0),
               Image.fromarray(sh.clip(0, 255).astype(np.uint8)))
    cell.paste(im2, (0, top), im2)
    cell.save("images/ring-3d-v3.webp", quality=90, method=6)
    print(f"ring-3d-v3.webp 287x520 from ref, transparent hole {hole_w}x{hole_h}px, "
          f"band rr 1.0-{rr_out:.2f}, k={k:.3f}")


if __name__ == "__main__":
    bosses()
    ring()
