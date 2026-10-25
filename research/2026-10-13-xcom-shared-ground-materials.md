# XCOM 2026-10-13: shared world-projected ground and scatter (farm test pass)

## Problem

Per-tile ground models each repeated their texture once per 2 m tile: visible
grid, straight seams, no macro variation, and 1-2 cm features averaging out at
game zoom (~2.6 cm/px) while sprite grit is 5-8 cm per pixel.

## Trials

1. Shared world-projected material: one ShaderMaterial per manifest material,
   world XZ sampling (grass repeat 6 m = 3 tiles, soil 8 m), hex tiling, 3-band
   variation texture (macro ~30 m, mottle, 5-8 cm grit). Captured with
   `capture_shared_materials.py` against the original renderer in the same run.
2. Scatter vegetation from the tile field (v1-v3):
   | Capture | Lawn fine noise | Tall grass value | Far alien contrast |
   | --- | --- | --- | --- |
   | Sprites | 36.7 | 0.243 | - |
   | Shared materials | 33.5 | 0.169 | 1.77 |
   | Vegetation v1 | 41.4 | 0.150 | 1.52 |
   | Vegetation v2 | 33.6 | 0.174 | 1.84 |
   | Vegetation v3 | 31.8 | 0.186 | 1.88 |
   v1 made tall grass read like lawn and filled the ground with dark tufts (units
   harder to see). v2: sparse low lawn, distinct ~1 m yellower meadow, trample
   within 0.8 m of units. v3: separate red/blue blossom types ~2x size lifted
   clear, `base_lift`, sparse-aware root darkening.
3. Dirt scatter: soil matched sprite fine noise in sun (53 vs 53.5) but not in
   shade (21 vs 55); clods/stones/dead weeds added; solid bits do not write
   depth (strong SSAO ringed every clod).
4. Wavy borders: per-level material map + world-noise nudged lookup, same field
   on both sides. Cost (OXP_GROUND_BENCH, 4x110 frames, medians): square 5.604 ms
   -> full stack 5.653 (game view), 4.403 -> 4.531 close-up; adding fringe and
   grain (restored micro variation the user missed) 5.780 / 4.636.

## Decisions

- One layered material per map; world projection over chunk-mesh merging
  (merging needs rebuilds on destruction, breaks per-part overlays, does not help
  object tiles).
- All grass is grown by the scatter (user); per-tile tufts hidden via cached
  mesh copies; imported assets untouched.
- Never merge distinct grounds (user rule): drawn-on-top differences share a
  layer; base-ground differences get their own layer and wavy borders.
- Measure readability (fine noise, unit contrast) after every scatter change.
- 2026-10-16 addition: slope relief term following the real sun, because sprites
  bake strong slope shading.

## Open at the time

Soil darker than sprite in clod shadows; lawn smoother than sprite at game zoom;
tall grass darker in shadow (SSAO on dense cards); maize still per-tile; other
families bound later the same day via generated manifests (13 layers).

## Sources

XCOM `docs/screenshots/shared_materials_20261013/README.md`,
`docs/GROUND_MATERIALS.md`.
