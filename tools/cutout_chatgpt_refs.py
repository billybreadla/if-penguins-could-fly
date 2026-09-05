#!/usr/bin/env python3
"""Background-remove ChatGPT refs with rembg and write game WebPs.

Cutout recipe per ref:
  1. open RGBA
  2. rembg remove (isnet-general-use when available)
  3. autocrop by alpha > 16 with ~5% pad
  4. max-dim 1600 thumbnail if needed
  5. save WebP quality=88 method=6

Also builds fish hue variants, panic copies, and a 4-cell hero strip.
Run from the repo root:  python3 tools/cutout_chatgpt_refs.py
"""
from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "images" / "generated-refs"
OUT = ROOT / "images"
MAX_DIM = 1600
ALPHA_THRESH = 16
PAD_FRAC = 0.05
WEBP_KW = dict(quality=88, method=6)

# src ref (under REFS) -> one or more output paths (under OUT)
BOSS_MAP = [
    # boss3D set
    ("boss1-cruiser-chatgpt-left.png", "boss3d-cruiser.webp"),
    ("boss1-cruiser-damaged-chatgpt-left.png", "boss3d-cruiser-damaged.webp"),
    ("boss1-cruiser-wrecked-chatgpt-left.png", "boss3d-cruiser-wrecked.webp"),
    ("boss2-gundeck-chatgpt-left.png", "boss3d-gundeck.webp"),
    ("boss2-gundeck-damaged-chatgpt-left.png", "boss3d-gundeck-damaged.webp"),
    ("boss2-gundeck-wrecked-chatgpt-left.png", "boss3d-gundeck-wrecked.webp"),
    ("boss3-dread-chatgpt-left.png", "boss3d-dread.webp"),
    ("boss3-dread-damaged-chatgpt-left.png", "boss3d-dread-damaged.webp"),
    ("boss3-dread-wrecked-chatgpt-left.png", "boss3d-dread-wrecked.webp"),
    # painted fallbacks (boss3D:false)
    ("boss1-cruiser-chatgpt-left.png", "boss.webp"),
    ("boss1-cruiser-damaged-chatgpt-left.png", "boss-damaged.webp"),
    ("boss1-cruiser-wrecked-chatgpt-left.png", "boss-wrecked.webp"),
    ("boss2-gundeck-chatgpt-left.png", "gun-deck-v4.webp"),
    ("boss2-gundeck-damaged-chatgpt-left.png", "gun-deck-damaged.webp"),
    ("boss2-gundeck-wrecked-chatgpt-left.png", "gun-deck-wrecked.webp"),
    ("boss3-dread-chatgpt-left.png", "boss2.webp"),
    ("boss3-dread-damaged-chatgpt-left.png", "dreadnought-damaged.webp"),
    ("boss3-dread-wrecked-chatgpt-left.png", "dreadnought-wrecked.webp"),
]

# Hue shifts (degrees) for fish3d-v5_0..6 — slot 0 is the unshifted cutout.
FISH_HUES = [0, 35, 70, 110, -35, -70, 145]


def make_session():
    try:
        return new_session("isnet-general-use")
    except Exception as e:
        print(f"isnet-general-use unavailable ({e}); using default session", flush=True)
        return new_session()


def autocrop(im: Image.Image, thresh: int = ALPHA_THRESH, pad_frac: float = PAD_FRAC) -> Image.Image:
    a = np.asarray(im.split()[-1])
    ys, xs = np.where(a > thresh)
    if len(xs) == 0:
        return im
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    w, h = x1 - x0, y1 - y0
    pad = int(round(max(w, h) * pad_frac))
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(im.width, x1 + pad)
    y1 = min(im.height, y1 + pad)
    return im.crop((x0, y0, x1, y1))


def fit_max(im: Image.Image, max_dim: int = MAX_DIM) -> Image.Image:
    if max(im.size) > max_dim:
        im = im.copy()
        im.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    return im


def cutout(path: Path, session) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    src.save(buf, format="PNG")
    out_bytes = remove(buf.getvalue(), session=session)
    im = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
    im = autocrop(im)
    im = fit_max(im)
    return im


def save_webp(im: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", **WEBP_KW)
    print(f"  -> {dest.relative_to(ROOT)}  {im.size[0]}x{im.size[1]}", flush=True)


def hue_shift(im: Image.Image, degrees: float) -> Image.Image:
    """Rotate hue of non-transparent pixels by `degrees` (keep alpha/value/sat)."""
    if degrees == 0:
        return im
    rgba = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
    rgb, a = rgba[..., :3], rgba[..., 3]
    # vectorized RGB->HSV
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    d = np.maximum(mx - mn, 1e-6)
    v = mx
    s = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    m = mx == r
    h[m] = ((g - b)[m] / d[m]) % 6
    m = mx == g
    h[m] = (b - r)[m] / d[m] + 2
    m = mx == b
    h[m] = (r - g)[m] / d[m] + 4
    h = (h / 6.0 + degrees / 360.0) % 1.0

    hh = h * 6.0
    c = v * s
    x = c * (1 - np.abs(hh % 2 - 1))
    z = np.zeros_like(c)
    sector = np.floor(hh).astype(int) % 6
    s6 = [(sector == k)[..., None] for k in range(6)]
    rgb2 = np.select(
        s6,
        [
            np.stack([c, x, z], -1),
            np.stack([x, c, z], -1),
            np.stack([z, c, x], -1),
            np.stack([z, x, c], -1),
            np.stack([x, z, c], -1),
            np.stack([c, z, x], -1),
        ],
    ) + (v - c)[..., None]
    mask = a > 0.01
    out = np.concatenate([np.where(mask[..., None], rgb2, rgb), a[..., None]], -1)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA")


def pack_hero_strip(hero: Image.Image, cell: int = 520, n: int = 4) -> Image.Image:
    """Horizontal strip of n identical cell×cell frames centered from hero cutout."""
    frame = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
    h = hero.copy()
    h.thumbnail((cell, cell), Image.Resampling.LANCZOS)
    frame.paste(h, ((cell - h.width) // 2, (cell - h.height) // 2), h)
    strip = Image.new("RGBA", (cell * n, cell), (0, 0, 0, 0))
    for i in range(n):
        strip.paste(frame, (i * cell, 0), frame)
    return strip


def ring_frame_hint(im: Image.Image) -> str:
    """Estimate RING3D_FRAME constants from a cutout (centered hole assumption)."""
    w, h = im.size
    hole_frac = 0.578
    hole_h = int(round(h * hole_frac))
    hole_cx, hole_cy = w / 2.0, h / 2.0
    out_rx, out_ry = w / 2.0, h / 2.0
    # Preserve the prior hole/outer radius ratio from the v23 tilted torus.
    hole_rx = out_rx * (82.5 / 143.5)
    hole_ry = out_ry * (150.5 / 260.0)
    return (
        f"RING3D_FRAME ≈ {{ src: {{ x: 0, y: 0, w: {w}, h: {h} }}, "
        f"holeCX: {hole_cx:.1f}, holeCY: {hole_cy:.1f}, holeH: {hole_h}, "
        f"outRX: {out_rx:.1f}, outRY: {out_ry:.1f}, "
        f"holeRX: {hole_rx:.1f}, holeRY: {hole_ry:.1f} }}"
    )


def main() -> int:
    session = make_session()
    failures: list[str] = []
    cut_cache: dict[str, Image.Image] = {}

    def get_cut(name: str) -> Image.Image | None:
        if name in cut_cache:
            return cut_cache[name]
        src = REFS / name
        if not src.is_file():
            print(f"MISSING {src}", flush=True)
            failures.append(name)
            return None
        print(f"cutout {name} ...", flush=True)
        try:
            im = cutout(src, session)
        except Exception as e:
            print(f"FAIL {name}: {e}", flush=True)
            failures.append(name)
            return None
        cut_cache[name] = im
        return im

    # --- bosses (shared cutouts written to multiple destinations) ---
    for src_name, dest_name in BOSS_MAP:
        im = get_cut(src_name)
        if im is None:
            continue
        save_webp(im, OUT / dest_name)

    # --- ring ---
    ring = get_cut("ring-chatgpt.png")
    if ring is not None:
        save_webp(ring, OUT / "ring-3d-v5.webp")
        print(ring_frame_hint(ring), flush=True)

    # --- mine ---
    mine = get_cut("mine-chatgpt.png")
    if mine is not None:
        save_webp(mine, OUT / "mine-3d-v1.webp")

    # --- fish: keep nose-LEFT (matches drawFish; world scroll = swim-left) + hue variants ---
    fish = get_cut("fish-chatgpt-left.png")
    if fish is not None:
        for i, deg in enumerate(FISH_HUES):
            variant = hue_shift(fish, deg)
            save_webp(variant, OUT / f"fish3d-v5_{i}.webp")

    # --- panic: base cutout + slight brightness/warm variants (not identical copies) ---
    panic = get_cut("penguin-panic-chatgpt-left.png")
    if panic is not None:
        from PIL import ImageEnhance
        save_webp(panic, OUT / "penguin_panic_0.webp")
        v1 = ImageEnhance.Contrast(ImageEnhance.Brightness(panic).enhance(1.08)).enhance(1.06)
        save_webp(v1, OUT / "penguin_panic_1.webp")
        # warm shift for slot 2
        arr = np.asarray(panic).copy()
        a = arr[..., 3:4] > 8
        arr[..., 0] = np.where(a[..., 0], np.clip(arr[..., 0] * 1.06 + 4, 0, 255), arr[..., 0])
        arr[..., 1] = np.where(a[..., 0], np.clip(arr[..., 1] * 0.98, 0, 255), arr[..., 1])
        arr[..., 2] = np.where(a[..., 0], np.clip(arr[..., 2] * 0.94, 0, 255), arr[..., 2])
        v2 = ImageEnhance.Contrast(Image.fromarray(arr, "RGBA")).enhance(1.1)
        save_webp(v2, OUT / "penguin_panic_2.webp")

    # --- hero + strip ---
    hero = get_cut("penguin-hero-chatgpt-left.png")
    if hero is not None:
        save_webp(hero, OUT / "heropenguin.webp")
        strip = pack_hero_strip(hero, cell=520, n=4)
        save_webp(strip, OUT / "hero-strip-3d-v8.webp")

    print("\nDone.", flush=True)
    if failures:
        print("Failures:", ", ".join(failures), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
