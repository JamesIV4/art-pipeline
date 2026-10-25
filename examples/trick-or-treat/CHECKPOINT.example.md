# yard_street / batch02 checkpoint (v2: polished and textured)

I rebuilt all 21 yard_street catalog assets with painted materials and smooth or bevelled forms, and exported them. All 21 pass `python art/tools/gates.py --lane yard_street`. Every asset has a Workbench sheet in `art/review/sheets/` and an in-engine preview in `art/review/engine/`. Each asset went through at least two build, preview and revise passes. The trees and the car went through five or more.

## Scripts

Run each script with `blender --background --factory-startup --python <script> -- <id> ...`. A helper builds, gates and previews in one step: `powershell -NoProfile -File art\team\yard_street\batch02\run.ps1 <script> id1,id2 -Preview`.

| Script | Assets |
| --- | --- |
| `yard_common.py` | Shared helpers (see below) |
| `build_trees.py` | tree_maple_red, tree_maple_orange, tree_maple_gold |
| `build_bush_pot.py` | bush_round, flower_pot |
| `build_lights.py` | lamp_post, paper_lantern, porch_lantern, string_bulb |
| `build_furniture.py` | mailbox, bench, rocking_chair, swing_set |
| `build_inflatables.py` | inflatable_ghost, inflatable_cat, cauldron |
| `build_car.py` | parked_car |
| `build_sky.py` | cloud_a, cloud_b, cloud_c, bat |
| `view_gltf.py` | Renders an exported glTF from any yaw, pitch and zoom (tint x AO). I used it to check undersides, close-ups and floating assets, because the engine preview drops floating assets into the ground plane. |

## yard_common.py (v2)

Every builder writes its own seam-safe material UVs instead of relying on the kit's per-face projection:
- `sweep()`: a tube with parallel-transport frames, per-ring radius and a shape(i, angle) multiplier. Its UVs run around the circumference in metres and along the arc length, so bark ridges follow the trunk and branches. The trees, rods, ropes, rockers, seats and tails all use it.
- `lathe()`: per-band colour and material, continuous UVs, pane columns and flat-shaded bands.
- `blob()`: a smooth lumpy sphere with puffy lobes. The pole axis is selectable, and `uvmode="box"` gives world planar UVs, which removed the pole swirl on the leaves and hedge.
- `loft()`: closed cross-sections along Y with per-face colours. It builds the car body and the mailbox.
- `cull_hidden(zmin=)`, `flatten_below()`, `cut_below()`, `paint_world()`, `set_mat()`, `box()`. `box()` makes bevelled boxes with sharp edges around the flat panels, so they don't shade like pillows.

## What changed against v1

- Trees: chunkier curved trunk with a five-root flare, a visible fork of three limbs under the crown, and the low socket branch kept clear of foliage. The crown is 32 or more overlapping lobed leaf clusters with a darker filler core, leaves material and mixed tints. I removed the per-face underside tint because it made stair-step lines across the smooth clusters.
- Clouds: smooth lobed puffs with a squashed flat base and no cut caps. Seen from below they read as soft lumps, not geodesic domes. I fixed a culling bug that punched holes in the underside after the squash.
- Car: one bubbly loft body with tumblehome, round headlight eyes snapped to the surface, fender arches and chunky tyres.
- Inflatables: gored vinyl panels with pinched horizontal seams.

## Weak or unresolved

- **Canopies**: up close the clusters still read a little like a bunch of balloons or a cauliflower, partly because the toon specular shines on every cluster. The silhouette edges of the 14-segment clusters show faint facets. The gold tree's rust_leaf accents read as separate red blobs rather than blended accents.
- **Clouds**: the engine preview puts them half into the ground, so I checked them in Blender only (`view_gltf.py`), not in a sky context. They are still somewhat bead-like on cloud_c's long axis, and the roof_slate tint is dark and moody rather than bright and cute.
- **Car**: the side profile is still closer to a rounded compact or Beetle than a squat toy (the hood is fairly long). Hubs (10 sides) and tyres (14 sides) show facets in close-ups. 3972/4000 tris, so there is no room left.
- **Budgets**: several assets sit at the limit (string_bulb 80/80, inflatable_cat 1597/1600, rocking_chair 1392/1400, bench 1188/1200, lamp_post 1180/1200). Any future addition needs a trade.
- **Glow**: glow cells look right in the engine preview, but the cauldron's potion and bubbles bloom into one bright mass at night.
- **Small details**: the bat's eye glints read as a notch at close range. The flower-pot leaves look like pills from the side. The ghost's scalloped hem is barely visible. The mailbox number plate (cream) reads very bright at night.
- **Sockets** (checked in the exported nodes): socket_branch is at (1, 2.6, 0.04), which is Godot Y-up with the front at +Z, on the underside of the low branch. lamp_post socket_light is at the glass centre. paper_lantern socket_hang (0, 0, 0) and socket_light (0, -0.235, 0). porch_lantern socket_light (0, -0.02, 0.17). The bat's wing_l and wing_r origins are at the shoulders (±0.075).
