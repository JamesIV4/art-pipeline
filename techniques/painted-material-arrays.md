# Painted material layers as texture arrays

## What it is

A small library (28 in trick-or-treat) of seamless, hand-painted, near-grey tiling textures
("siding", "bark", "felt", "pumpkin", ...) packed into one Texture2DArray (albedo) plus a derived
normal-map array. Each face picks one layer by index (encoded in UV2, see palette-tint-uv.md);
the painting modulates the palette tint, so one texture serves every colour.

## Why

The user wanted hand-painted surfaces, not flat colours, but with a palette that stays global.
Neutral grey paintings tinted per face give painterly detail with one draw material and no
per-asset textures. The same layer indices are shared by Blender assets and C++ procedural meshes.

## How

- Spec `art/materials/materials.json`: a shared `style` prompt plus `layers[]` with
  `name`, `scale` (metres per repeat), `strength` (how much the painting modulates the tint),
  `normal` (normal-map strength) and `subject` (prompt text). Index = order; layer 0 is `flat`.
  Typical values: siding 2.0/0.9/0.8, wood 1.0/0.6/0.35, felt 0.6/0.55/0.5, metal 1.0/0.4/0.3,
  cloud 6.0/0.6/0.5.
- Sources: `art/materials/source/<name>.png` (AI-painted, see ai-texture-generation.md) with a
  `.provenance.json` sidecar. Missing sources fall back to tileable noise placeholders.
- `tools/make_materials.py` per layer: resize to 512; if `seam_ratio` (edge difference over
  interior difference) > 2.2, crossfade a 12% border band with a half-offset copy; neutralise each
  channel to mean 0.5; level luminance contrast toward `TARGET_STD = 0.13` with the gain capped
  at 2.5; derive a tangent-space normal (OpenGL, Y+) from blurred luminance x `7 * normal`.
  Outputs albedo/normal array strips, `game/materials/toon.tres` (per-layer scale/strength/normal
  arrays padded to 32), a C++ constants header and a tinted contact sheet `preview.png`.
- Shader: `tuv = UV / layer_scale`; `ALBEDO = tint * mix(1, detail * 2, strength)`;
  `NORMAL_MAP_DEPTH = layer_normal * 1.4`.
- Material choice by what the surface is: wood -> wood/planks, hay -> straw, pumpkin -> pumpkin,
  canopies -> leaves, bushes -> hedge, trunks -> bark, cloth -> felt/denim/burlap/fabric, metal
  -> metal, lanterns -> paper, inflatables -> vinyl, clouds -> cloud. Tiny parts, eyes, glow faces,
  candy wrappers and glossy toy paint: `flat`.
- Projection: `cyl` for upright round things, `sphere` for blobs, `box` for boards. Re-run
  `K.project()` after deforming or merging. Better: builders write their own seam-safe UVs
  (sweep-lathe-uvs.md).

## Gotchas

- The seam check fires on most structured textures even when they tile (flat interiors give a
  tiny denominator; at the old 1.6 threshold almost everything blended). The half-offset blend is
  harmless when the pattern period divides half the tile (brick, 7-row shingles, 4-rib pumpkin) but
  ghosts layouts that do not (3x3 paver grid, 3.3 ribs per tile). Fix: offset the source so its
  edges land in continuous content (`np.roll` by half a paver or rib) and record it as
  `postprocess` in the provenance.
- Low-contrast sources (wood, concrete, metal) were boosted 4-8x during the 2026-10-24 pass and
  turned streaky (wood knots became dark "eyes", faint metal became purple blotches). The current
  script caps the gain at 2.5.
- Material reads that failed in engine and were changed per asset: fabric (plaid) on ghost and
  mummy; paper on a skull (striped) -> concrete; metal on car bodies (hairline brush streaks even
  with UVs scaled down) -> flat glossy paint; hedge on a bush (read as pebbles); felt on a belly
  (read as burlap) -> flat; felt overall reads as fuzzy terrycloth at kid scale (material-level,
  not fixable from a lane).
- Sphere projection pinches at the poles (swirl on leaves and hedges): use world box UVs or put
  the pole where nobody looks.
- Candy uses its own shader that ignores the material layer; only palette, gloss and self-glow show.

## Source

trick-or-treat: art/materials/materials.json, art/materials/CHECKPOINT.md,
art/tools/make_materials.py, game/shaders/toon.gdshader, art/team/BRIEF.md, CHECKPOINTs of
monsters, vehicles, characters_candy batch02/03, foliage batch03, yard_street batch02.
Port: tools/make_materials.py. Normal derivation detail: see pbr-map-derivation.md.
