# Ground scatter driven by the tile field (grass, litter, clods, straw)

## What it is

A runtime layer that grows grass, flowers, litter, stones, clods and straw from
the map's tile ids instead of baking tufts into each tile model. Each scatter
type is driven by a smooth density field built from its source tiles and drawn
as one MultiMesh per (level, 8x8-tile chunk, type).

## Why

Per-tile tufts (120 cards baked into every lawn tile) showed the tile grid,
stopped dead at tile borders, and could not react to neighbours, destruction or
units. Bare soil matched sprite fine-noise in sun (53 vs 53.5) but went flat in
shade (21 vs 55) and had no relief.

## How

1. Manifest (`assets/shared_materials/vegetation.json`, generated per family by
   `build_ground_scatter.py`): each type lists source tile ids, kind, density,
   heights, tints and rules.
2. Field: 1 on source tiles, bilinear between tile centres; keep candidates by a
   smoothstep of the field so instances fade over ~0.5 m across a border.
   `spill_onto` limits which floors they may spread onto.
3. Height from the 3x3 mean of the field: taller inside a block (meadow 0.65x at
   a lone tile to 1.3x inside), `edge_height` at the border, `grow_near` (lawn
   rises into an uncut margin beside tall grass), `yield_to` (one type gives way
   where another is full).
4. `soft_edge {warp, warp_m, core}`: density from the 3x3-mean field, floored by
   `core` x raw field, sampled at a position warped by two noise octaves, so the
   falloff meanders instead of forming squares.
5. Patchiness: `cluster` world value-noise per type; `near` / `near_boost` for
   proximity (gutter litter only by curbs; leaves 3x denser under trees).
6. Kinds: `cards` (crossed alpha cards: grass, flowers, weeds), `rock` (displaced
   icosphere textured from above with the floor's own texture in world space,
   lighter tops, contact darkening), `flat` (quads on the ground: leaves, fronds,
   lichen, litter), `stick` (thin prisms ~1 cm, `pieces` 1-3, `pile` heaps of
   ~150 stalks). Rare types: density < 0.5 per tile is a per-tile chance (it
   used to round to zero).
7. Hide what the scatter replaces: `hide` strips named materials / `*` /
   `node:Details` from a cached copy of the tile mesh; `jitter` gives listed
   single-tile trees a seeded yaw and offset (seed by map x,y; never multi-tile).
8. Rebuild a chunk when a tile in or next to it changes (burning crops vanish).
   ~30,000 instances on a farm map built in ~0.25 s spread over frames.

## Shading rules

- Grass: lighting normal bent toward the ground normal; translucency; root-to-
  tip gradient, weaker where sparse (`root_dark_sparse`); `base_lift` raises
  near-black atlas bases; per-instance hue/value; `tip_tint` toward straw; sway.
- Lumps do not write depth, so strong SSAO does not ring every 5 cm clod with a
  dark halo; tall solid bits (cacti, tumbleweeds) do write depth or the fog
  overlay darkens them twice. Lumps shade partly like the ground (`normal_up`).
- Units: grass within 0.8 m of a unit's feet is pressed down and bent away.
- Visibility: scatter reads the tile visibility texture directly (never-seen =
  nothing, explored-unseen = darkened).
- Desert sand sparkle: a fraction of ~2 cm grains are glossy tilted facets.

## Readability measurement

`art/tools/measure_ground_readability.py`: fine noise = mean |value - blurred|
x1000, and unit contrast against the surrounding ground ring. Example (farm):
sprites lawn noise 36.7; 3D vegetation v1 41.4 made units harder to read
(far alien 1.52); v2/v3 (sparse low-contrast lawn, distinct taller yellower
meadow, blossoms lifted clear) 31.8-33.6 with far alien 1.84-1.88.

## Generated atlases

Pass every generated cutout atlas through `install_scatter_atlas.py`: harden
alpha and bleed edge colour outward so a generated fringe never shows as a halo.
Keep prompts in a versioned JSON beside the sources. Dead weeds get their own
atlas, never a recoloured green grass atlas.

## Gotchas

- Vertical cards alone cover too little ground from a high camera to carry a
  darker "dense grass" read; also darken the ground under it (`ground_shade` in
  the material map's blue channel, sampled at the wave-nudged position).
- The first pass filled the ground with dark tufts and reduced unit contrast;
  measure readability after every scatter change.
- Selection rings inside tall grass are partly covered; acceptable or lift.

## Source

- XCOM `docs/GROUND_MATERIALS.md` section 4-5
- XCOM `docs/screenshots/shared_materials_20261013/README.md` (vegetation v1-v3,
  dirt scatter)
- XCOM `art/tools/measure_ground_readability.py`, `build_ground_scatter.py`,
  `install_scatter_atlas.py`
