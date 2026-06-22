# Art Overhaul V5 — Asset Handoff

All final assets are in `images/`. Original generated sources are preserved in `images/_src/art-overhaul-v5/`.

## Painted worlds

Each background is 1400×933 RGB PNG. The first and last pixel columns are matched for horizontal tiling.

- `world-sunset-v5.png`
- `world-aurora-v5.png`
- `world-snowy-peaks-v5.png`
- `world-outer-space-v5.png`
- `world-dusty-hills-v5.png`
- `world-storm-v5.png`

## Start screen

- `title-hero-v5.png` — 1536×1024 RGB key art
- `title-wordmark-v5.png` — 1600×600 transparent title logo

## Flight-kit skins

All skins are 520×520 transparent PNGs with the same orientation and approximate footprint as `heropenguin.png`.

- `plane-classic-v5.png`
- `plane-sunset-v5.png`
- `plane-aurora-v5.png`
- `plane-midnight-v5.png`

## Storybook art

Each story inset is a 1024×768 RGB PNG.

- `story-determined-v5.png`
- `story-festival-v5.png`
- `story-captain-albatross-v5.png`

## Boss entrance portraits

Each portrait is a 768×768 transparent PNG.

- `boss-card-cruiser-v5.png`
- `boss-card-gun-deck-v5.png`
- `boss-card-dreadnought-v5.png`

## Flight animation

- `hero-flight-strip-v5.png` — 2080×520 transparent strip; four 520×520 frames from left to right
- `hero-flight-frame-0-v5.png` — neutral / strong propeller blur
- `hero-flight-frame-1-v5.png` — flipper-up climb
- `hero-flight-frame-2-v5.png` — bank left/up
- `hero-flight-frame-3-v5.png` — bank right/down

The strip cells use the same indexing as the individual filenames: `sourceX = frameIndex * 520`.
