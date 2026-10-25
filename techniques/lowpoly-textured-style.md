# Polished textured low poly (kit v2 contract)

## What it is

The house style for props, characters and creatures: toy-like low poly with soft rounded forms,
bevelled hard edges and a hand-painted tiling material on every face, tinted per face by a shared
palette, with baked vertex AO. Reference points the user gave: Animal Crossing: New Horizons,
A Short Hike, Super Mario 3D World props. Cute, never scary or realistic.

## Why

The first trick-or-treat slice used flat palette colours only (kit v1). On 2026-10-24 the user
saw it and asked for "polished, toy-like 3D with hand-painted textures" instead. Every lane was
then rebuilt (batch01 -> batch02) with the same budgets roughly tripled. Low poly stays, but it is
"generous": detail goes where the eye lands (rims, seams, stitching, handles, caps).

## How

Conventions every asset follows (kits/lowpoly/lowpoly_kit.py enforces most of them):

- 1 Blender unit = 1 m, Z up. Front faces Blender -Y (glTF/Godot +Z, `Node3D.MODEL_FRONT`).
- Origin at the ground contact point. Floating assets (candy, clouds, hanging lanterns) use
  their centre or hang point and set `"floating": true` in the catalog.
- Scale reference: hero character 1.1 m, door 2.2 m, porch step 0.2 m. Review sheets include a
  1.1 m scale post.
- Sockets are empties named `socket_<anchor>`; character parts are named child objects with the
  origin at the joint (see character-kit-lowpoly.md).
- Export glTF separate (.gltf + .bin), Y up, no materials, AO in COLOR_0, UVMap in TEXCOORD_0,
  Tint in TEXCOORD_1. The engine applies one shared toon material to everything.

Kit v2 API: every primitive (`box`, `cylinder`, `sphere`, `ico`, `torus`, `tube`,
`polygon_prism`) takes `color=` (palette cell), `mat=` (painted layer) and `project=`
(`box`, `cyl`, `sphere`). Shaping: `K.paint(ob, color, where, mat=)`, `K.project(ob, mode,
where)`, `K.deform`, `K.merge`, `K.set_parent`, `K.socket`, `K.bake_ao`, `K.export`,
`K.review_sheet`.

Form rules that produced the polished look:

1. Smooth shading on organic forms (lathes, ellipsoids, sweeps); bevel hard edges (1-2
   segments reads as "toy"). Flat panels keep sharp edges so they do not shade like pillows
   (yard_common `box()` marks big flat faces sharp).
2. Weighted normals on hard-surface assets: farm_lib `finish()` adds a WeightedNormal modifier
   (crisp bevels, soft rounds).
3. Bottom-heavy, chunky proportions. Thin rods (chair frames, wheelbarrow handles, 1 cm
   springs) read as wrong at gameplay distance; thicken them.
4. Spend the triangle budget on silhouette and rims; drop detail the camera cannot see (the
   mailbox lost 180 tris of embossed ribs that were invisible at 15 m).
5. At least two build -> engine preview -> revise passes per asset, hero assets four or more.
   Passing gates earns a review, not an approval.

Per-asset loop: build, `K.export` + `K.review_sheet`, engine preview, look at night and studio
rows (stretching, busy, too dark at night, too flat in studio), revise, `gates.py` must PASS.

## Gotchas

- Blender 5.1 `ico(subdiv=1)` is the bare 20-tri icosahedron, not 80 (subdiv 2 = 80, 3 = 320).
  Lanes budgeted from the wrong docstring.
- Bevelled kit boxes with 2 segments produced 32 degenerate triangles on a hay bale. Every lane
  helper ended up with a `clean()`/`cleanup()` that triangulates and drops zero-area slivers.
- Newly created bmesh faces have no normal; ear-clip triangulation then fills concave notches
  (leaf lobes). Call `normal_update()` before triangulating.
- `set_parent` read a stale `matrix_world` until the view layer was updated: sockets and wing
  parts exported at the origin. Fixed in the kit; verify node translations in the glTF.
- Godot re-imports a glTF only when the .gltf JSON changes; geometry lives in the .bin. A rebuild
  that keeps counts and bounds silently showed the old model. `K.export` stamps a build id into
  scene extras (`tot_build`) to force re-import.
- `--lift` / `--combined` review exports (candy standing on the ground, gate base+lantern merged)
  must be rebuilt without the flag before hand-off; they fail gates.
- Budgets near 100% (string_bulb 80/80, dragon 8930/9000) mean any later fix needs a trade.

## Source

trick-or-treat: art/README.md, art/team/BRIEF.md, art/tools/lowpoly_kit.py, CHECKPOINTs of
yard_street batch01/02, pumpkins_farm batch01/02, characters_candy batch01/02, landmarks
batch03; user memory art-direction.md.
