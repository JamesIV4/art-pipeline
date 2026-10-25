# Baked per-vertex ambient occlusion

## What it is

Every exported mesh carries per-vertex AO in a colour attribute named "AO" (glTF COLOR_0). The
toon shader multiplies it in (`AO = mix(1, COLOR.r, 0.85)`, `AO_LIGHT_AFFECT = 0.35`), on top
of screen-space AO in the engine.

## Why

Low-poly forms with flat tints read as cardboard without contact darkening: crevices between
parts, undersides, where a prop meets the ground. Vertex AO is free at runtime, works on every
platform and survives distance where SSAO fades.

## How

`K.bake_ao(objects, samples=32, radius=0.8, strength=0.9, ground=True)` in
kits/lowpoly/lowpoly_kit.py:

1. Build one BVH over every mesh of the asset (all parts and children, world space), so parts
   occlude each other.
2. For each vertex, cast `samples` golden-angle hemisphere rays around the vertex normal from
   `p + n * 0.006`. A hit at distance d adds `1 - 0.5 * d / radius`; rays heading below z = 0
   within the radius count as full ground hits (`ground=True`).
3. `ao = 1 - strength * occ / samples`; write it, make it the active and render colour.

Call it after the final merge and parenting, before export. `K.export` bakes automatically if no
mesh has AO yet. The gate fails exports with Tint UVs but no COLOR_0.

Variants lanes built on top (worth porting as options):

- Radius per asset size: 0.35 for monsters, 0.05 for a wand (no ground), 0.55-0.9 for big props
  and trees. Small assets with the default 0.8 m radius get uniformly dark.
- Joint bake, separate export (lm_common `export_many`): bake AO across several assets that sit
  together (gate base + lantern), then export each on its own.
- Bake without decals: bake the body without printed decals so the surface under a print does
  not darken, then give the prints their own pass (play_props trampoline mat prints).
- Separate bake for an emissive or pulsing part (vine heart inside its root cage; the cage would
  otherwise dim it).
- AO lift: `finish_car(ao_lift=...)` raises AO inside a pickup bed, which baked near-black. A
  12-quad plank floor was added so the bake has interior vertices to land on.
- Analytic AO for foliage cards: ray AO speckled hundreds of leaf cards, so foliage computes AO
  from position (lobe tops light, undersides about 0.45, crevices between lobes darker, crown base
  darker) and ray-casts only along custom shading normals (see foliage-crowns-lowpoly.md).
- Fixed AO for "shadow-only" filler cores (0.35) so they read as depth, never as lit balls.

## Gotchas

- Vertex AO needs vertices: big flat quads (car bed, mat tops) get one value per corner. Add
  interior loops or a grid where the darkening should vary.
- Per-face underside tints used instead of AO made stair-step lines on smooth tree clusters; they
  were removed in favour of AO.
- The review sheet colours are tint x AO; very dark AO in sheets is real and will show in game.
- AO baked on a combined review export (`--combined`) is missing in the real separate exports;
  rebuild without the flag.

## Source

trick-or-treat: art/tools/lowpoly_kit.py (`bake_ao`, `_hemisphere`), game/shaders/toon.gdshader,
art/team/foliage/batch03/foliage_common.py (`bake_ao_shade`), landmarks/batch03/lm_common.py,
vehicles/batch03/car_kit.py, play_props/batch03 and vines/batch03 CHECKPOINTs,
yard_street/batch02 CHECKPOINT.
