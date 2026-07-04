# 🐧 If Penguins Could Fly — Art Handoff V6 ("Battle Damage & Polish")

For Codex. Match the existing painted V5 style (see `images/boss.webp`,
`images/title-hero-v5.webp`). Deliver PNG with transparency where noted;
masters can go in `images/_src/art-v6/`; final cutouts go straight in
`images/` with the exact names below. Do NOT edit index.html — Claude wires.

## 1. Boss damage states (highest priority)
The three boss ships never look hurt while you fight them. For EACH of the
three existing boss sprites, paint 2 damage variants at the SAME pixel
dimensions as the original (same silhouette and position, so the game can
swap frames without any layout shift):

- `boss-damaged.png` / `boss-wrecked.png`
  (variants of `images/boss.png` — the World 1 cruiser gun)
- `gun-deck-damaged.png` / `gun-deck-wrecked.png`
  (variants of `images/_src`… source for `gun-deck-v4.webp`; original PNG is
  `images/gun-deck-v4.png`)
- `dreadnought-damaged.png` / `dreadnought-wrecked.png`
  (variants of `images/boss2.png`)

"Damaged" = scorch marks, a few dents and cracks, small smoke wisps.
"Wrecked" = heavy cracks, missing plating chunks, glowing ember gaps,
more smoke. Keep the brass/steampunk look.

## 2. PWA app icons
The game is becoming an installable home-screen app like Dino Bob.
Penguin pilot face close-up (helmet + goggles), bold and readable at
small sizes, on a solid deep-sky-blue background (#1c66b8 or similar):

- `icon-192.png` (192x192, square, NO transparency)
- `icon-512.png` (512x512, same art)
- `icon-maskable-512.png` (512x512, art safely inside the middle 80%
  so Android's circle mask doesn't crop the face)

## 3. Run medals
Small trophy medals for end-of-run ranks, transparent PNG ~256x256,
same toy-like painted finish as the power-ups:

- `medal-bronze.png`, `medal-silver.png`, `medal-gold.png`
  (winged medal with a little penguin silhouette stamped in the center)

## 4. (Stretch) World-clear celebration art
- `victory-penguin-v6.png` — the penguin pilot doing a loop with a trail of
  stars/confetti, transparent, ~800px wide. Used on the "WORLD CLEARED!"
  screen. Only if time allows.

Priority order: 1, 2, 3, 4.
