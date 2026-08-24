# HANDOFF — If Penguins Could Fly, 3D-look upgrade
_Updated 2026-08-23 ~12:00. The approved 6-item roadmap is COMPLETE. Nothing committed._

## State in one line
All six roadmap items shipped behind CONFIG flags: multiplane world 0 + all worlds 1–7,
3D hero strip, 3D ring, 3D fish ×7, 3D power-up atlas, 3D boss fleet (3 ships ×
fresh/damaged/wrecked), title-screen turntable. ASSET_VER 15, sw CACHE `ipcf-v7-toy-box`.
Every feature reverts with a one-line CONFIG flip.

## Config switches (index.html, CONFIG)
| Flag | Default | Reverts to |
|---|---|---|
| `hero3D` | true | painted flight strip |
| `ring3D` | true | painted rings.webp |
| `fish3D` | true | painted fish_0..6 |
| `powerup3D` | true | painted powerups-obstacle-v2 atlas |
| `boss3D` | true | painted boss/gun-deck/dreadnought set |
| `titleSpin3D` | true | no turntable on title |
| `haze` / `shadow` | 0.14 / 0.16 | 0 disables each |
| `bgMid` / `bgNear` | 2.2 / 3.8 | multiplane mid/near speeds (all worlds) |
| `decorClouds` / `contactBand` | true | depth clouds / shadow-plane sheen (0-style flags) |

## What was built (all verified in headless Chrome, zero uncaught errors)
- **Worlds 1–7 multiplane** (`tools/slice_world.py` → `images/bg{1..5,7}-{far,mid,near}.webp`):
  every painting split into three parallax planes like world 0 — far (sky + landforms, 1x),
  mid + near (feathered ground/sea strips at `bgMid`/`bgNear`). Per-world band fractions live
  in `WORLDS` (slicer) and `WORLD_BANDS` (runtime) and MUST stay in sync; the slicer also
  carries each world's sky/ground gradient stops. Paintings tile by repeat (matched edge
  columns), so the world path passes `mirror=false` to `drawBgBand` — world 0 keeps mirroring.
  `drawBackground` falls back to the plain painting if any plane fails to load.
- **Fish ×7** (`tools/model_props.py` + `compose_props.py` → `fish3d_0..6.webp`): one toy
  fish mesh, palettes sampled from the painted originals, canvases sized identical to
  fish_0..6 so `drawFish` math is untouched. Tutorial legend icon follows the same flag.
- **Power-ups** (`powerups-3d.webp`, 2172×724): star/magnet/stopwatch/shield rebaked and
  scaled into the OLD frame content bboxes (pixel-identical on-screen footprint); bird cell
  copied verbatim. `ADVENTURE_FRAMES` untouched.
- **Boss fleet** (`tools/model_bosses.py` + `compose_bosses.py` → `boss3d-{cruiser,gundeck,
  dread}{,-damaged,-wrecked}.webp`): brass steampunk builds. The tight crop is PADDED so the
  bore lands exactly on the existing `muzX/muzY` constants (verified ±0.001) — JS constants
  serve both art sets. Damage = seeded soot blobs + alpha-masked darken + ember glows.
  Entrance portrait cards unchanged (painted, by design).
- **Title turntable** (`tools/bake_spin.py` → `hero-spin-v1.webp`, 16×384 cells): toy spins
  at ~6fps top-left of the title, soft shadow, static under `reducedMotion`.

## Pipeline knowledge (hard-won — read before re-baking anything)
- **Blender 5.2 LTS** (`brew install --cask blender`): view_transform is `['NONE']` only —
  convert palette colors sRGB→linear (`v ** 2.2`) or renders go pastel; engine id
  `BLENDER_EEVEE` (scripts try `_NEXT` first); headless:
  `blender --background --python tools/<script>.py -- <args>`.
- **Primitive scale traps** (each cost a re-bake):
  - default cube is 2×2×2 → cube scale = HALF edge; cylinder depth=1 → scale = FULL length
    along its axis; sphere/cone radius=1 → scale = radius.
  - object scale applies in LOCAL axes AFTER rotation: for `rot=(0,90,0)` cylinders
    (barrel along X) use `scale=(zRadius, yRadius, lengthX)`; for `rot=(90,0,0)` discs
    (facing camera) use `scale=(xR, zR, depthY)`.
  - mesh-data edits (magnet half-torus) need the rotation BAKED into the mesh
    (`data.transform(Matrix.Rotation(...)`) or face-center z is the tube axis, not height.
- **Camera convention**: ortho cam at (0,-D,0) rot (90,0,0) → world -X renders frame-LEFT
  (art faces left = nose -X), world +Z is up, +Y toward camera.
- **Metals need environment**: metallic surfaces reflect the world node — keep world
  strength ≥ 0.3 and a strong front AREA light or bosses go near-black.
- **Engine contracts**: ring hole frac == `RING.holeFrac`; hero strip 4 square cells
  nose-left, frames cruise/climb/bank/dive; power-up atlas cell boundaries == 
  `ADVENTURE_FRAMES`; boss bore fraction == `muzX/muzY` per level.
- **Any new/changed asset**: bump `ASSET_VER` AND add to `sw.js` CORE AND bump the CACHE
  string, or installed PWAs keep stale art.
- **Verification harness** (delete after use, never commit): copy index.html, inject before
  `</body>`:
  ```html
  <script>
  setTimeout(() => {
    CONFIG.maxFall = 99;
    state = STATE.PLAYING; holding = false; speed = 0.45; starT = 999;
    passed = 7;                       // force biome: world = floor(passed/7)%5
    // arena = 2 dusty / 3 storm; startBoss(1..3) for fights
    setInterval(() => { if (state === STATE.PLAYING) {
      player.y = H*0.45; player.vy = 0; player.angle = 0; hasShield = true; graceT = 0.5;
      passed = 7; bannerT = 0; mapT = 0;
    } }, 16);
  }, 300);
  </script>
  ```
  then: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless
  --disable-gpu --window-size=1280,720 --virtual-time-budget=4500 --screenshot=out.png
  "file://$PWD/_t.html"`. Gotchas: without `maxFall=99` the hover trips DIVE pose; the
  title screen needs `storyPage = 0; state = STATE.READY` to skip the story pages.
- Syntax check after JS edits:
  `python3 -c "import re;open('/tmp/s.js','w').write(re.search(r'<script>(.*)</script>', open('index.html').read(), re.S).group(1))" && node --check /tmp/s.js`
- Free HF image→3D Spaces were GPU-starved for anonymous users all night; TripoSR output
  (with correct `/preprocess`) was an unusable blob for the hero. Procedural Blender won.
  `/tmp/opencode/triposr_retry.py` has the retry-loop pattern (tmp — copy if keeping).

## Housekeeping
- **Nothing is committed.** Uncommitted: `index.html`, `sw.js`, `tools/model_hero.py`
  (hero v2 tweaks) + new: `HANDOFF.md`, `images/hero-strip-3d-v2.webp`,
  `images/ring-3d-v1.webp`, `images/w{1,2,3,4,5,7}-near.webp`, `images/fish3d_0..6.webp`,
  `images/powerups-3d.webp`, `images/boss3d-*.webp` (9), `images/hero-spin-v1.webp`,
  `tools/{slice_world,model_props,compose_props,model_bosses,compose_bosses,bake_ring,
  bake_spin}.py`, `tools/worlds-preview.png`.
- `images/dino-plush.webp`: appeared untracked, not agent-created, wired into the game by
  Billy's v13/v14 waves. Leave alone.
- Performance: only static review (added per-frame cost ≈ 1 extra tiled drawImage for world
  bands; sprites are same-count drawImages). No runtime/phone profiling yet.
- `hero-strip-3d-v1.webp` kept for A/B history (superseded by v2, still in sw CORE).
- `tools/bg0-preview.png` / `tools/worlds-preview.png` are dev artifacts, safe to delete.
