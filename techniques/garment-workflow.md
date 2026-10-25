# Garment workflow: body-derived undersuit, delete groups, iso-contour armour

## What it is

How to dress a skinned humanoid so clothing deforms with the body without
intersections: the garment is derived from the fitted body surface and keeps
the body's own skin weights, the body under it is deleted (MakeClothes "delete
group" convention), and rigid armour plates are zero-contour cuts of a smoothed,
offset body surface with real walls.

## Why

XCOM's first unit lane kept the full body under a separately eased (9-12 mm),
solidified 3 mm suit. Versions v04-v11 were spent on wall reversals, metre-
scale solidify spikes, and body/suit intersections in arm-raise, shoulder and
hip poses. Earlier drafts were worse: disconnected primitive tubes, or the body
itself recoloured as cloth. The delete-group approach solved it in one pilot.

## How: undersuit

1. Fit natural body/head/neck proportions first (MPFB/MakeHuman CC0 base at
   uniform contract scale). Never shrink anatomy to fit a legacy outfit.
2. Copy the body faces the suit covers; Taubin-smooth lightly (extra on
   genital/nipple masks); offset ~5.5 mm along normals. The suit keeps the
   body's own weights, so under linear-blend skinning it follows at near-constant
   offset.
3. Delete the body faces hidden under the suit (keep ~22 mm overlap at openings).
   Nothing remains underneath to collide with.
4. Garment features: sparse joint compression folds (local ridges curving around
   the limb), panel seams as iso-contour edge loops (centre front/back, side,
   underarm, armhole, inseam, waist) marked as UV seams and pressed ~1.1 mm, hems
   extruded ~3.5 mm inward at every opening; UV by garment panel.
5. Under rigid armour delete suit faces > 28 mm inside a plate's outline AND
   >= 85% weighted to that plate's bone (no relative motion).
6. Tint near-black joins as dark lavender/colour, not black: joins then read as
   shading lines like the source, not holes.
7. Fold detail: restrained resting folds (sculpt or optional offline cloth sim);
   major silhouette folds in mesh, weave/stitch in normal/roughness. No runtime
   cloth, no film-scale corrective shape system.

## How: rigid armour plates

- Region = zero contour of a smooth scalar field evaluated on the actual mesh
  (`geo.iso_cut`): split edges at the zero crossing, delete the negative side, so
  outlines are clean curves, not stair-stepped face selections.
- Fields in bone-local coordinates (s along bone, radius r, angle 0 = front,
  +90 lateral) combined with smooth minimum (5-8 mm corners). Neighbouring
  plates' angular windows must abut, never overlap (check arithmetically).
- "Muscle armour": band-pass gain, base = heavily smoothed body (40 Taubin),
  detail = light - heavy, plate = base + detail x 3; then sculpted relief
  functions (superellipse domes ~19-26 mm, narrow Gaussian grooves). 1 cm bumps
  read flat; go bigger. Use grooves, not real splits, where the source shows a
  line.
- Rolled rims from distance-to-boundary. Decimate the cut surface BEFORE
  solidify; solidify with ordinary offset (see `solidify-thickness.md`), 6-10 mm
  inward; chamfer only the outer rim edge.
- Binding: rigid plates 100% to one bone. Joint-crossing plates (pauldrons,
  cops): a constant 2-bone blend or, better, a helper bone following the joint at
  30-50% rotation. Gate: plate edge-length change <= 2% across all clips.

## Accessories

- Straps: ribbons along a control path ray-projected onto the actual outer armour
  (BVH of armour/cloth only), ~4 cm wide, weights transferred; ends tuck under.
- Boots: cut foot, cap, voxel remesh (6 mm), smooth, offset ~17 mm, clamp z >= 0
  for a flat sole, open the top, inverse-distance weight transfer.
- Gorget/collar: flexible (body weights), height by angle around the neck.

## Validation

Pose-check every frame of every clip: count self-intersecting triangle pairs
by body region (BVH overlap, vertex-sharing pairs excluded) and ground
penetration. Check arm raise, elbow, knee, hip bends before propagating the
outfit method to other variants. Crease feathering fixes knee/elbow folds:
smoothstep weight band wide on the flexion side (10 cm knee, 5 cm elbow), tight
over the joint point. Accept residual deep-flexion contact as soft tissue but
reduce it with the pose.

## Gotchas

- Only deform-bone vertex groups may label regions (MPFB's `body` group is
  weight 1 everywhere).
- bmesh: creating/removing custom-data layers invalidates held element
  references; create layers before poke/subdivide/fill.
- Contour surgery needs a star-shaped ring around the sort axis; diffuse the
  weight field first (40 averaging passes) or extra loops leave holes.
- Remove genuinely hidden body only after fit and deformation succeed.

## Source

- XCOM `art/review/units-garment-workflow-guide.md` (MPFB Creating Clothes,
  MakeClothes, Blender Studio clothing references)
- XCOM `art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md` sections 3-6, 12c
- XCOM `art/team/units_opus55/research.md` ("how the garment avoids the body")
- XCOM `art/team/units_rebuild_max/research.md` (v04-v08 failure history)
- XCOM `art/team/research/tripo_hands/GUIDE.md` section 7 (plates)
