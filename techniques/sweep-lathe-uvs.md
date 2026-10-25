# Sweeps, lathes and seam-safe material UVs

## What it is

The workhorse builders behind most organic and turned assets (trunks, branches, ropes, tails,
vines, rockers, posts, pumpkins, lanterns, barrels), each writing its own material UVs so the
painted texture follows the form: around the circumference in metres and along the arc length,
aligned with geometric features where the texture has structure (ribs, planks, grain).

## Why

The kit's per-face box/cyl/sphere projection stretches on deformed and swept shapes, swirls at
poles and puts seams where they show. Texture structure that does not line up with geometry (a
painted rib across a geometric groove) reads as noise. Builder UVs fixed bark ridges on branches,
pole swirl on leaves, and pumpkin ribs.

## How

Core builders (trick-or-treat yard_street/batch02 `yard_common.py`, pumpkins_farm/batch02
`farm_lib.py`, characters_candy/batch02 `dk_kit.py`):

- `sweep(points, radii, sides, profile/shape)`: parallel-transport frames (no twisting flips),
  cyclic tangents for closed loops, per-ring radius and a `shape(i, angle)` multiplier (root
  flares, lobed ropes, flattened straps), optional twist (twisted rope), per-side stripes, and
  `rib=` texture alignment. UVs: u = circumference metres, v = arc length.
- `lathe(profile)`: revolve an (r, z) profile; r = 0 makes a clean pole (no degenerate tris); one
  colour/material per band; uneven `angles` plus band colours give pane columns with thin mullions;
  stave UVs map one plank per stave (barrels); wrapped-straw UVs for bales.
- `blob()`: smooth lumpy sphere with a selectable pole axis (hide the pinch) and `uvmode="box"`
  world planar UVs (removed pole swirl on leaves and hedges).
- `loft()`: closed cross-sections along an axis with per-face colours (car bodies, mailbox).
- `board()` / `slab()`: rounded-rect beams with grain along the length, hidden end caps skipped;
  `project_along(ob, "x")` sets grain direction after the fact; `scale_uv` densifies (bark on a
  wand shaft at 5x UV density, stems at a denser scale).
- `catmull()` / `bezier()` / `arc()` for smooth control paths.

Alignment recipes:

- Pumpkin: the `pumpkin` texture has exactly 4 ribs per tile with grooves at u = 0.125 + k/4; the
  body UVs give each geometric lobe exactly one rib, so painted grooves land in geometric grooves.
  Tube gourds needed half a rib per side (one rib per side read as flat panels).
- Planks: one plank per stave or board; straw strands along the bale length; circumferential straw
  on round-bale tops.
- Brick: world UVs x2.3 for about 8 cm courses on a planter.
- Every helper writes both UV maps in order: UVMap (TEXCOORD_0, metres) then Tint (TEXCOORD_1).

## Gotchas

- 3-4 sided twisted rope tubes catch pale highlights on single facets (pinkish streaks in studio).
- Low side counts show on silhouettes: 10-sided gourds, 12-segment wheels, 14-segment clusters.
  Spend sides on silhouette parts, not hidden ones.
- Re-project after any deform or merge if a builder did not set UVs itself.
- Culling bugs after squashing (holes in cloud undersides) come from culling against pre-squash
  ellipsoids; cull after the final deform.
- Painting stripes by face position on a sweep gives jagged edges; paint by sweep column index.

## Source

trick-or-treat: art/team/yard_street/batch02/yard_common.py and CHECKPOINT,
pumpkins_farm/batch02/farm_lib.py, CHECKPOINT and results.json, characters_candy/batch02/dk_kit.py,
decor_ground/batch03 CHECKPOINT, play_props/batch03 CHECKPOINT (wand).
