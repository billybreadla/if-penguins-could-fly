#!/usr/bin/env python3
"""Fish v2: recolor the AI fish bake into the 7 original palettes.

Zone-based HSV recolor on the single TripoSR fish render:
  blue-hue pixels  -> variant body color (shading/value preserved)
  yellow-hue pixels-> variant fin color
  white belly/eye  -> untouched
Output stretched to each original fish_i canvas, same contract as
compose_props.py (identical footprint in drawFish).

Run from the repo root:  python3 tools/compose_fish_v2.py
"""
import colorsys
import numpy as np
from PIL import Image

BASE = "/tmp/opencode/i23d/fish_base_h3d.png"

# (body, fin) per variant, eyedropped from the painted originals
PALETTES = [
    ((30, 80, 200), (255, 194, 61)),    # 0 royal blue / yellow (as baked)
    ((255, 122, 30), (58, 58, 58)),     # 1 clownfish orange / dark fins
    ((63, 155, 34), (183, 211, 74)),    # 2 green / yellow-green
    ((247, 143, 167), (255, 210, 74)),  # 3 salmon pink / yellow
    ((74, 127, 155), (207, 212, 90)),   # 4 steel teal / yellow-green
    ((217, 201, 168), (242, 185, 59)),  # 5 sandy cream / yellow
    ((122, 75, 200), (255, 210, 74)),   # 6 purple / yellow
]


def recolor(im, body, fin):
    rgba = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
    rgb, a = rgba[..., :3], rgba[..., 3:]
    mx = rgb.max(-1); mn = rgb.min(-1)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    h = np.zeros_like(mx)
    m = mx == r
    h[m] = ((g - b)[m] / d[m]) % 6
    m = mx == g
    h[m] = (b - r)[m] / d[m] + 2
    m = mx == b
    h[m] = (r - g)[m] / d[m] + 4
    h = h * 60  # deg

    def tint(mask, target):
        _h, _s, _v = colorsys.rgb_to_hsv(*[c / 255.0 for c in target])
        th = _h * 6
        ts = _s
        # full-image arrays: masked pixels take target hue/sat, keep baked value
        hh = np.where(mask, th, h / 60)
        ss = np.where(mask, np.maximum(s * 0.0 + ts, 0), s)
        vv = v
        c = vv * ss
        x = c * (1 - np.abs(hh % 2 - 1))
        z = np.zeros_like(c)
        sector = np.floor(hh).astype(int) % 6
        s6 = [(sector == k)[..., None] for k in range(6)]
        conv = np.select(
            s6,
            [np.stack([c, x, z], -1), np.stack([x, c, z], -1), np.stack([z, c, x], -1),
             np.stack([z, x, c], -1), np.stack([x, z, c], -1), np.stack([c, z, x], -1)],
        ) + (vv - c)[..., None]
        return np.where(mask[..., None], conv, rgb)

    body_m = (h >= 190) & (h <= 265) & (s > 0.22) & (a[..., 0] > 0.3)
    fin_m = (h >= 25) & (h <= 75) & (s > 0.22) & (a[..., 0] > 0.3)
    rgb = tint(body_m, body)
    rgb = tint(fin_m, fin)
    out = np.concatenate([rgb, a], -1)
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


base = Image.open(BASE).convert("RGBA")
base = base.crop(base.getbbox())

for i, (body, fin) in enumerate(PALETTES):
    src = Image.open(f"images/fish_{i}.webp").convert("RGBA")
    W, H = src.size
    r = recolor(base, body, fin).resize((W, H), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(r, (0, 0), r)
    canvas.save(f"images/fish3d-v5_{i}.webp", quality=88, method=6)
    print(f"images/fish3d-v5_{i}.webp {W}x{H}")

# preview sheet
sheet = Image.new("RGBA", (240 * 7, 150), (255, 255, 255, 255))
for i in range(7):
    im = Image.open(f"images/fish3d-v5_{i}.webp")
    sheet.alpha_composite(im, (i * 240, (150 - im.height) // 2))
sheet.save("/tmp/opencode/i23d/fish_v5_sheet.png")
print("sheet /tmp/opencode/i23d/fish_v5_sheet.png")
