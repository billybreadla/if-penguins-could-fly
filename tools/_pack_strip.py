#!/usr/bin/env python3
"""Pack a list of transparent PNGs into one horizontal WebP strip.

Usage:
  python3 tools/_pack_strip.py <cell_w> <cell_h> <out.webp> <frame0.png> [frame1.png ...]

Each frame is centered on a transparent cell_w x cell_h canvas (downscaled
to fit if larger), then concatenated left→right.
"""
import sys
from pathlib import Path

from PIL import Image


def pack(cell_w: int, cell_h: int, out: Path, frames: list[Path], quality: int = 88) -> None:
    strip = Image.new("RGBA", (cell_w * len(frames), cell_h), (0, 0, 0, 0))
    for i, fp in enumerate(frames):
        im = Image.open(fp).convert("RGBA")
        # fit inside cell, keep aspect
        im.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
        x = i * cell_w + (cell_w - im.width) // 2
        y = (cell_h - im.height) // 2
        strip.paste(im, (x, y), im)
    out.parent.mkdir(parents=True, exist_ok=True)
    strip.save(out, "WEBP", quality=quality, method=6)
    print(f"PACKED {out}  {strip.size[0]}x{strip.size[1]}  cells={len(frames)}@{cell_w}x{cell_h}")


def main():
    if len(sys.argv) < 5:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    cell_w = int(sys.argv[1])
    cell_h = int(sys.argv[2])
    out = Path(sys.argv[3])
    frames = [Path(p) for p in sys.argv[4:]]
    for f in frames:
        if not f.is_file():
            raise SystemExit(f"missing frame: {f}")
    pack(cell_w, cell_h, out, frames)


if __name__ == "__main__":
    main()
