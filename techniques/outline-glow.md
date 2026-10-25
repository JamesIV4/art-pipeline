# Outline glow (inflated back-face shell in the object's own colour)

## What it is

Collectibles get a thin glowing outline that hugs their silhouette: a second render pass of the
same mesh, inflated along a blend of its normal and radial direction, drawn with front faces
culled (so only the rim shows behind the object), unshaded and emissive in a per-instance tint,
pulsing softly. In trick-or-treat it is the `next_pass` of the candy material.

## Why

The user explicitly wanted "candy glow is an outline around each piece, not a halo". The earlier
additive camera-facing halo sprite behind each candy (halo.gdshader, still in the repo but no longer
wired) was replaced. An outline keeps the silhouette crisp, separates the piece from any background
at night, and carries a colour code (tier / kind) without covering the model.

## How

Shader (trick-or-treat game/shaders/candy_outline.gdshader):

- `render_mode cull_front, unshaded, shadows_disabled, fog_disabled`.
- Vertex: apply the same spin and bob as the main pass (rotation `TIME * 1.7 + phase` about Y,
  bob `sin(TIME * 2.3 + phase) * 0.09`) so the shell never slips off the piece.
- Inflate: `dir = normalize(mix(normalize(VERTEX), NORMAL, 0.35))`, `VERTEX += dir * thickness
  / object_scale` with `thickness = 0.03` m. The radial component keeps the shell closed on hard
  edges and flat faces where pure normal offset would crack.
- Fragment: `ALBEDO = tint`, `EMISSION = tint * 2.6 * (0.8 + 0.2 * sin(TIME * 3.2 + phase * 2))`.
- Tint per instance: MultiMesh custom data `(phase, r, g, b)`; pieces outside a MultiMesh (spilled
  or dropped candy) set an `instance uniform outline_tint`. Fallback tint is warm gold, never black.

Data: each collectible's outline colour lives in the asset catalog as `glow: "#rrggbb"` (84
candies), published to the engine catalog with `candy_tier`. Choose a saturated, slightly lighter
version of the body colour (berry #ff2f74, aqua #2ffff0, golden #ffd040).

The main candy pass helps the outline read: colour pushed 1.4x past palette saturation, self-glow
0.5-0.55 x albedo, and a rim term in the piece's own colour (not white) so pieces stay saturated
at distance.

## Gotchas

- The outline colour was catalog data only for a while; the shader still used a hard-coded
  9-entry kind table, so new kinds glowed the wrong colour until the game read `glow` from the
  catalog. Wire the data path in the same change as the art.
- Never a black outline on spilled candy: unset instance uniforms default to black; give the
  uniform a non-black default and set it explicitly.
- The shell inflates by world thickness divided by scale; scaled-up tiers (golden x1.25) need the
  division or their outline grows with them.
- Pieces with glow cells (golden apple, lolly jack) plus outline bloom heavily in studio light;
  fine at night, but judge glow at night.
- Flat pieces (coins, discs) go edge-on twice per spin and the outline becomes a line; chunkier
  shapes read better as collectibles.

## Source

trick-or-treat: game/shaders/candy_outline.gdshader, candy.gdshader, halo.gdshader (retired),
game/materials/candy.tres, native/src/play/candy_field.cpp and loose_candy.cpp,
art/team/candy_variety/batch03/CHECKPOINT.md, user memory art-direction.md.
