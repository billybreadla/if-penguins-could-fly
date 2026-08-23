#!/usr/bin/env python3
"""Fit the raw prop bakes (/tmp/opencode/props) into game-ready images.

- fish3d_0..6.webp: same canvas sizes as the painted fish_0..6 (240 x H), so
  drawFish's aspect math and on-screen footprint stay identical. The render is
  stretched to fill the canvas — cartoon props tolerate the ~10% squeeze, and
  it guarantees the collectible reads the same size as before.
- powerups-3d.webp: 2172x724 atlas matching ADVENTURE_FRAMES cell boundaries.
  Each baked prop is scaled into the OLD frame's content bbox, so on-screen
  size is pixel-identical to the painted art. The bird cell is copied
  verbatim from the original atlas (declared out of scope for 3D).

Run from the repo root:  python3 tools/compose_props.py
"""
from PIL import Image

ATLAS_W, ATLAS_H = 2172, 724
CELLS = {"star": (0, 434), "magnet": (434, 434), "slow": (868, 434),
         "shield": (1270, 345), "bird": (1640, 532)}
SRC = "/tmp/opencode/props"

old = Image.open("images/powerups-obstacle-v2.webp").convert("RGBA")
new = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
for key, (x, w) in CELLS.items():
    if key == "bird":
        new.paste(old.crop((x, 0, x + w, ATLAS_H)), (x, 0))
        continue
    r = Image.open(f"{SRC}/{key}.png").convert("RGBA")
    r = r.crop(r.getbbox())
    cell = old.crop((x, 0, x + w, ATLAS_H))
    bx = cell.getbbox()                       # old art's content bbox in this cell
    tw, th = bx[2] - bx[0], bx[3] - bx[1]
    rs = r.resize((tw, th), Image.LANCZOS)
    new.paste(rs, (x + bx[0], bx[1]), rs)
new.save("images/powerups-3d.webp", quality=88, method=6)
print("images/powerups-3d.webp", new.size)

for i in range(7):
    src = Image.open(f"images/fish_{i}.webp").convert("RGBA")
    W, H = src.size
    r = Image.open(f"{SRC}/fish_{i}.png").convert("RGBA")
    r = r.crop(r.getbbox()).resize((W, H), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(r, (0, 0), r)
    canvas.save(f"images/fish3d_{i}.webp", quality=88, method=6)
    print(f"images/fish3d_{i}.webp {W}x{H}")
