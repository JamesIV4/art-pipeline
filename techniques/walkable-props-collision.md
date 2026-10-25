# Walkable props and the collision contract

## What it is

Props the player can stand or bounce on (bales, crates, barrels, giant pumpkin, planters, pillars,
car roofs, trampolines) declare simple collision in the catalog, and the art is shaped so the
visible top matches the collision top. The generator uses `walkable` tops for traversal and candy
runs, so a wrong top height breaks platforming, not just looks.

## Why

Platforming candy is planned along real jump arcs onto prop tops. A top that is domed, cluttered
or taller than its collider makes landings feel wrong (feet sinking into pads, standing on air above
plants), and a stem at the centre of a walkable top blocks the most natural landing spot.

## How

Catalog fields (see the schema in docs): `collision` = `none | box | cylinder | trunk`, `radius`
and `height` (cylinder/trunk at the origin), `walkable` (top is a platform), `collision_top`
(explicit top height for walkable boxes), `bounce` (launch speed, m/s, trampolines 17.0 and 14.0).
Box collision defaults to the mesh AABB.

Shaping rules:

1. Flat tops on walkables, within about 1-2 cm: hay bale flake bulge about 1 cm, round bale dome
   2 cm with 1.4 cm spiral relief, crate boards flush, barrel lid recessed 4 cm below the chime,
   giant pumpkin `flat_top`.
2. Keep decoration below the walk height or out of the AABB: the straw fringe on the rebuilt hay
   bale stays below 0.562 m so the walk height barely moved, but it widened the AABB from
   1.1 x 0.6 to 1.29 x 0.76 m.
3. State the walk height in the brief and verify it in the glTF (trampoline mat top 0.850 and
   0.280 measured, matching `collision_top`).
4. Keep landing centres clear: a 0.36-0.4 m stem in the middle of the giant pumpkin's top is the
   first thing a centred landing hits.
5. Report integration facts in the CHECKPOINT: collider suggestions in game coordinates (post at
   (-1.08, 0, 0) r 0.32 h 3.4), light positions that moved, label positions, decorative parts
   outside the collider.

## Gotchas

- AABB box colliders include everything: plants on a planter put the player at 0.86 m instead of
  the 0.55 m cap; roof cargo lifted a wagon's box 0.22 m above the roof; mirrors widened a car box
  0.1 m per side; a ladder pushed a trampoline AABB to +2.06 m. Either add a collision-height
  override in the catalog/engine, provide a plant-free variant, or keep extras inside the body.
- Pads that rise above `collision_top` (trampoline pad 6 cm above the mat) let feet sink on the rim.
- `height` was only read for `trunk` colliders in trick-or-treat; check what the engine actually
  reads before relying on a field.
- Long-axis orientation matters for placement (hay wagon long axis X, tongue to -X); document it.

## Source

trick-or-treat: art/asset_catalog.json (comment and entries), art/tools/publish_catalog.py,
CHECKPOINTs of pumpkins_farm batch01/02, decor_ground/batch03, play_props/batch03, vehicles/batch03,
landmarks/batch03; README "Platforming design" (trampolines, ledge grab).
