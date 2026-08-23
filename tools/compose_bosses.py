#!/usr/bin/env python3
"""Turn the raw boss bakes into game-ready sprites with damage states.

For each ship the tight crop is PADDED so the cannon bore lands exactly on the
muzzle fractions the engine uses (startBoss muzX/muzY — same constants serve
the painted art), then damaged/wrecked variants are generated with soot blobs,
scorch darkening and ember glows (seeded, reproducible).

Run from the repo root:  python3 tools/compose_bosses.py
"""
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import random

# name -> (target (muzX, muzY) as fractions of the sprite, bore world pos,
#          ortho scale, render px) — bore/scale/px mirror the BORE lines the
#          blender script printed for this bake.
SHIPS = {
    "cruiser": ((-0.24, -0.18), -0.94, 0.0, 3.8110, 1136),
    "gundeck": ((-0.34, 0.04), -1.24, 0.0, 4.2230, 1264),
    "dread":   ((-0.42, 0.08), -2.04, 0.0, 5.7680, 1728),
}
SRC = "/tmp/opencode/bosses"
MAXW = 1500


def pad_to_bore(im, fx, fy, bx, bz, s, res):
    """Pad the tight crop so the bore sits at (0.5+fx, 0.5+fy) of the canvas."""
    px = (bx / s + 0.5) * res
    py = (0.5 - bz / s) * res
    l, t, r, b = im.getbbox()
    im = im.crop((l, t, r, b))
    cpx, cpy = px - l, py - t
    W0, H0 = im.size
    a = 0.5 + fx
    padL = (a * W0 - cpx) / (1 - a)
    if padL < 0:
        padL = 0
        padR = cpx / a - W0
    else:
        padR = 0
    bb = 0.5 + fy
    padT = (bb * H0 - cpy) / (1 - bb)
    if padT < 0:
        padT = 0
        padB = cpy / bb - H0
    else:
        padB = 0
    out = Image.new("RGBA", (int(W0 + padL + padR + 0.5), int(H0 + padT + padB + 0.5)),
                    (0, 0, 0, 0))
    out.paste(im, (int(padL + 0.5), int(padT + 0.5)))
    return out, (cpx + padL, cpy + padT)


def soot(im, centers, seed, darken, embers):
    """Scorch the ship: soft dark blobs + optional ember glows."""
    rng = random.Random(seed)
    W, H = im.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (cx, cy) in centers:
        for _ in range(9):
            ox, oy = rng.randint(-int(W * 0.05), int(W * 0.05)), rng.randint(-int(H * 0.08), int(H * 0.08))
            r = rng.randint(int(W * 0.02), int(W * 0.055))
            d.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r],
                      fill=(22, 14, 8, rng.randint(70, 130)))
    layer = layer.filter(ImageFilter.GaussianBlur(int(W * 0.008)))
    out = Image.alpha_composite(im, layer)
    if darken:
        # veil only where the ship is opaque — a full-canvas darken would show
        # as a rectangle over the transparent padding
        veil = Image.new("RGBA", (W, H), (10, 6, 4, 0))
        veil.putalpha(ImageChops.multiply(im.getchannel("A"),
                                          Image.new("L", (W, H), int(255 * darken))))
        out = Image.alpha_composite(out, veil)
    for (cx, cy) in embers:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dg = ImageDraw.Draw(glow)
        r = int(W * 0.018)
        dg.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 140, 40, 200))
        glow = glow.filter(ImageFilter.GaussianBlur(int(W * 0.006)))
        out = Image.alpha_composite(out, glow)
        core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dc = ImageDraw.Draw(core)
        dc.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], fill=(255, 220, 140, 255))
        out = Image.alpha_composite(out, core)
    return out


def main():
    for name, ((fx, fy), bx, bz, s, res) in SHIPS.items():
        im = Image.open(f"{SRC}/boss3d-{name}.png").convert("RGBA")
        im, bore_px = pad_to_bore(im, fx, fy, bx, bz, s, res)
        if im.width > MAXW:
            k = MAXW / im.width
            im = im.resize((MAXW, int(im.height * k)), Image.LANCZOS)
            bore_px = (bore_px[0] * k, bore_px[1] * k)
        W, H = im.size
        # scorch clusters: hull mid + tower + tail (fractions of the canvas)
        spots = [(0.42, 0.55), (0.62, 0.38), (0.30, 0.42), (0.72, 0.62), (0.52, 0.70)]
        dmg = soot(im, [(W * a, H * b) for a, b in spots[:4]], seed=hash(name) & 0xffff,
                   darken=0.05, embers=[(W * 0.45, H * 0.5)])
        wrk = soot(im, [(W * a, H * b) for a, b in spots], seed=hash(name) & 0xffff,
                   darken=0.12, embers=[(W * 0.45, H * 0.5), (W * 0.66, H * 0.35),
                                        (W * 0.30, H * 0.45), (W * 0.55, H * 0.66)])
        im.save(f"images/boss3d-{name}.webp", quality=88, method=6)
        dmg.save(f"images/boss3d-{name}-damaged.webp", quality=88, method=6)
        wrk.save(f"images/boss3d-{name}-wrecked.webp", quality=88, method=6)
        afx = bore_px[0] / W - 0.5
        afy = bore_px[1] / H - 0.5
        print(f"boss3d-{name}.webp {W}x{H} bore frac ({afx:+.3f}, {afy:+.3f}) target ({fx:+.3f}, {fy:+.3f})")


if __name__ == "__main__":
    main()
