# Shared world-projected ground materials and wavy borders

## What it is

At runtime, every ground surface on a map is drawn with ONE layered
ShaderMaterial sampled in world XZ (not tile UVs). Each ground type is a layer
(slice of shared albedo/normal/ORM arrays + tint/roughness/variation scalars).
A per-level material map (one texel per tile) plus world-space noise produces
continuous wavy borders between grounds. A slope-relief term restores the
light/dark read of hills.

## Why

Per-tile ground models with one texture repeat per 2 m tile showed a visible
grid, straight seams at every material change, no large-scale variation, and
features (1-2 cm clods/blades) that averaged out in mips at game zoom (~2.6 cm
per screen pixel) while the sprites' grit was 5-8 cm per pixel. Merging tiles
into chunk meshes and re-UVing was rejected: rebuild on every destruction,
breaks per-part visibility overlays, does not help object tiles. World
projection needs no geometry change.

## How

1. Manifest (`assets/shared_materials/manifest.json`): named layers (textures,
   tint, roughness, repeat in metres, macro/grit settings) and bindings from
   catalog asset id + glTF material name (or surface index) to a layer. The
   presenter swaps the surface override when placing a tile; imported assets are
   untouched. Manifests are generated (`build_ground_manifest.py`).
2. Shader (`assets/shaders/shared_ground.gdshader`):
   - Hex tiling (Heitz & Neyret 2018): three samples on a triangle grid with
     random per-vertex offsets, blended, so even large repeats never show.
   - Variation from one tileable 3-band noise texture (spectral synthesis):
     R macro (~30 m) mixes dark/moist and light/dry tints and moistens
     roughness; G mottle; B grit at 4 m per repeat (2-10 cm features = 1-4 px
     at game zoom; finer grit vanishes in mips).
   - Shading reproduces StandardMaterial3D (ORM R/G/B); normals in a world-
     projected basis because projected UVs do not follow mesh tangents.
3. Material map: R8-ish texture per level, layer index + 1 and walking level,
   updated from tile records (destruction changes it).
4. Wavy borders, one rule for every pair: each pixel reads the map at its
   position nudged by world noise; both sides compute the same nudge, so the
   border is one line. A neighbour lends its layer only if it is shared ground at
   the same walking level (roads, craft floors, steps stay crisp). Default nudge
   stack (tiles): lobes ~3.5 m / 0.20, undulation 2.5 per tile / 0.13, wiggle
   ~0.35 m / 0.08, ragged ~0.12 m / 0.02, fringe 12-60 cm / 0.20, grain 5-20 mm
   / 0.05. Optional soft blend within ~0.1 tile of the line.
5. Natural-to-paved verge: paved overlays read the same map with a calm nudge
   (~0.06 tile at ~0.9 m); one-way, nature overgrows the paving edge.
6. Overlay shader for tiles that keep their own painted texture (craters, road
   markings): reproduce the authored material exactly, add the same macro /
   mottle / grit and "grime" on paving.
7. Slope relief (`slope_relief.gdshaderinc`): scale albedo by lean toward the
   real sun direction (light 0.8, dark 1.4, side 0.2); flat ground unchanged.
   Needed because sprites bake strong light/dark into slopes and 3D ambient
   flattens them.

## Rules

- Never merge distinct grounds. If tiles differ only by things drawn on top
  (rocks, litter, craters), share one layer and make the feature a detail,
  scatter or overlay. If the base ground itself differs in colour/texture, it is
  its own layer with wavy borders. Audit on an enlarged floor-sprite sheet with
  median/palette colours per diamond.
- A layer needs a material shared by >= 2 tiles; one-tile materials stay baked.
- Texture scale: grass and sand repeat at ~3x physical size so features read at
  game zoom; countable pebbles keep natural scale (~3 m) or they become cobbles;
  snow with painted per-tile marks keeps one-tile scale.
- Family presets tuned against sprite captures: sand warmer, rock cooler,
  jungle more saturated, Mars heavier speckle.

## Gotchas

- A nudge layer deeper than ~1/4 of its wavelength folds the lookup and makes
  detached islands (except the deliberate fringe). Keep total depth < ~0.5 tile
  or a lone tile vanishes into its neighbours.
- Godot 4.7 transparent border strips cannot receive SSAO/SSIL; draw natural-
  natural borders inside the opaque ground shader.
- A float hash lost precision and drew straight seams; use an exact integer hash.
- Natural assets authored with their own ground slab double-draw on tiles that
  already have a floor (dark squares). Hide the slab only when its top lies at
  the floor; hiding every slab removed real rock blocks and ramps.
- Cost: whole border stack ~0.05-0.15 ms game view, 0.13-0.3 ms close-up;
  per-map layered material build ~0.2 s (arrays at 1024 px, 1-4 layers per map,
  max 32).

## Source

- XCOM `docs/GROUND_MATERIALS.md` sections 1-3, 5
- XCOM `docs/screenshots/shared_materials_20261013/README.md`
- XCOM `art/review/opus_revision_queue.md` ("Natural terrain border blend")
