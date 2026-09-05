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
    """Compose the painted ring ref into the engine's tilted-torus cell.

    Engine contract (RING3D_FRAME / bake_ring.py): the 287x520 cell IS the
    ring — outer ellipse 287x520 (yaw-tilted, width = RING.aspect 0.55 of
    height), hole 166x301 centered (holeH == 520 * RING.holeFrac). The
    circular painted ring is inverse-remapped into that ellipse, then depth
    is baked in final space: the far-side inner wall visible through the
    hole, top-left form shading (warm lit / cool shade), a luminance bevel
    that stamps the ornament relief, and specular glints.
    """
    CW, CH = 287, 520
    HOLE_H = 301.0                    # RING3D_FRAME.holeH — must match exactly
    HOLE_W = HOLE_H * 0.55            # same tilt squash as the outer ellipse
    OUT_RR = (CH / 2) / (HOLE_H / 2)  # outer edge in hole units (1.727)
    im = Image.open("images/generated-refs/ring.png").convert("RGB")
    src = np.asarray(im).astype(np.float32)
    nonwhite = src.min(-1) < 235   # uint8! ~0.92*255
    Hs, Ws = nonwhite.shape
    scy, scx = Hs // 2, Ws // 2
    row = np.where(nonwhite[scy])[0]
    col = np.where(nonwhite[:, scx])[0]
    hx0, hx1 = row[row < scx].max(), row[row > scx].min()   # inner edges on row
    hy0, hy1 = col[col < scy].max(), col[col > scy].min()
    hw, hh = (hx1 - hx0) / 2, (hy1 - hy0) / 2
    rr_out_src = max((col.max() - col.min()) / 2 / hh, (row.max() - row.min()) / 2 / hw)

    yd, xd = np.mgrid[0:CH, 0:CW].astype(np.float32)
    ux = (xd - CW / 2) / (HOLE_W / 2)
    vy = (yd - CH / 2) / (HOLE_H / 2)
    rr = np.hypot(ux, vy)             # 1 = hole edge, OUT_RR = outer edge
    th = np.arctan2(vy, ux)
    feather = np.clip((OUT_RR - rr) / 0.03, 0, 1)
    alpha = np.where(rr <= OUT_RR - 0.012, 255.0 * feather, 0.0)
    alpha[rr < 1.0] = 0

    # inverse map cell -> circular source art (band stretch, hole->hole outer->outer;
    # sample radius clamped just inside the ref's outer AA halo to avoid white fringe)
    rr_cap = rr_out_src - 0.02
    rr_s = 1 + (rr - 1) * (rr_cap - 1) / (OUT_RR - 1)
    xs = scx + np.cos(th) * rr_s * hw
    ys = scy + np.sin(th) * rr_s * hh
    x0 = np.clip(np.floor(xs).astype(int), 0, Ws - 2)
    y0 = np.clip(np.floor(ys).astype(int), 0, Hs - 2)
    fx = np.clip(xs - x0, 0, 1)[..., None]
    fy = np.clip(ys - y0, 0, 1)[..., None]
    a = (src[y0, x0] * (1 - fx) * (1 - fy) + src[y0, x0 + 1] * fx * (1 - fy)
         + src[y0 + 1, x0] * (1 - fx) * fy + src[y0 + 1, x0 + 1] * fx * fy)
    band = alpha > 0

    # 1. far-side inner wall seen through the hole (tilt: far side = right)
    cth = np.cos(th)
    depth = 0.30 * np.clip(cth, 0, 1) ** 1.5
    wall = (rr < 1.0) & (rr > 1 - np.maximum(depth, 1e-6)) & (cth > 0.03)
    wgt = np.clip((1 - rr) / np.maximum(depth, 1e-6), 0, 1)[wall]
    ramp = 0.78 + 0.30 * np.sin(th[wall])              # darker top, lighter bottom
    a[wall] = np.array([128, 89, 26], np.float32) * ramp[..., None] * (0.85 + 0.35 * (1 - wgt))[..., None]
    rim = wall & (rr < 1 - depth * 0.90)               # dark line at the wall's far edge
    a[rim] *= 0.55
    alpha[wall] = 255
    band = alpha > 0

    # 2. near-side inner edge catches the light (bright rim, left of hole)
    near = band & (rr < 1.07) & (rr > 1.0) & (cth < -0.15)
    a[near] = np.clip(a[near] * 1.16 + 10, 0, 255)

    # 3. form shading from top-left, warm lit side / cool shade side
    thL = np.deg2rad(-135)
    c = np.cos(th - thL)
    wform = np.clip((rr - 1.06) / 0.16, 0, 1) * np.clip((OUT_RR * 1.02 - rr) / 0.10, 0, 1) * band
    for i, k in enumerate((0.12, 0.09, 0.04)):
        a[..., i] *= 1 + k * c * wform

    # 4. bevel: relief from the blurred luminance field, light top-left
    L = np.asarray(Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("L").filter(
        ImageFilter.GaussianBlur(1.6))).astype(np.float32)
    gy, gx = np.gradient(L)
    a += (24 * np.tanh((gx + gy) / 26))[..., None] * band[..., None]

    # 5. specular glints (main up-left, rim light lower-right)
    rmid = (1 + OUT_RR) / 2
    for tg, str_ in ((np.deg2rad(-118), 0.75), (np.deg2rad(52), 0.35)):
        g = np.exp(-((th - tg) / 0.42) ** 2 - ((rr - rmid) / 0.16) ** 2) * band
        a += (np.array([255, 246, 218]) * (g * str_)[..., None])

    rgba = np.dstack([a.clip(0, 255), alpha]).astype(np.uint8)
    Image.fromarray(rgba).save("images/ring-3d-v4.webp", quality=90, method=6)
    print(f"ring-3d-v4.webp {CW}x{CH} tilted torus, hole {int(HOLE_W)}x{int(HOLE_H)} "
          f"at ({CW//2},{CH//2}), band rr 1.0-{OUT_RR:.3f}")


if __name__ == "__main__":
    bosses()
    ring()
