# Hair cards from a Blender Curves groom

## What it is

Standard real-time hair: a groomed Blender Curves object is the editable source
of truth; its strands are rendered orthographically into a clump atlas; low-
poly alpha-tested cards are laid along the groom in layers over an opaque hair
cap that hides the scalp.

## Why

XCOM tried and rejected: a groom-baked "dome" as visible outer hair (read as a
coloured helmet), shell texturing (fur technique; a shiny ball head), unique-
cell per-card bakes (neighbouring cards never matched, shingles), and real
strand ribbons (great looking, ~30k triangles for 5k ribbons, more than the
whole character; instancing saves draws, not triangles).

## How

1. Groom: guides by farthest-point sampling on the cap, grown along a flow field
   read from the source art (swept back, lifted front, temple flare, sides and
   nape down), held to a height profile by nearest-surface projection; ~30k
   strands interpolated from the 3 nearest guides, tip-clumped, light frizz.
   Blender 5.1 ships the procedural hair node groups (Clump, Frizz, Curl,
   Interpolate, Set Hair Curve Profile, Shrinkwrap) in
   `datafiles/assets/nodes/procedural_hair_node_assets.blend`.
2. Clump atlas: render real strands orthographically in Cycles at 4096 (albedo
   via emission, camera-space normal, layer-depth AO), downsample to 2048.
   Islands: 0 opaque base, 1-2 breakup, 3 short wispy hairline. Root alpha fades
   over the first 15%. Colour is the final hair colour (no engine tint).
3. Cap: scalp region of the body offset 3-10 mm; root-tone texture (groom bake
   just above the scalp, pulled ~55% toward root colour); vertex-alpha hairline
   fade over ~12 mm; delete the scalp skin under it.
4. Cards: few, wide, low-poly (2 segments = 4 triangles). XCOM male soldier:
   80 base cards 6.5 cm wide (vertex AO .55, seated at 55% of groom height),
   220 breakup cards 3.8 cm (AO .82, at 88%), 35 hairline cards 2.4 cm (AO 1.0).
   Width axis = strand tangent x scalp normal; custom normals = scalp normal; UVs
   into shared islands with random mirroring; layers lifted 1.2 mm apart; roots
   sink into the cap. Total 335 cards = 1,340 triangles + 259-triangle cap.
5. Runtime material: alpha test 0.5 (glTF MASK -> Godot alpha scissor),
   double-sided, its own material; cards do not cast shadows (card-on-card
   contact shadows made dark "dash" artefacts, unlike a game shadow map).

## Gotchas

- Cycles camera space is +Z forward: negate Z when converting strand normals to
  +Z-out tangent space (verify X/Y from strand-edge gradients).
- Preview hair with the runtime alpha test, not blended alpha, or judgements are
  wrong.
- Several options were indistinguishable at game distance; always include a
  30 deg ~5 m crop.
- Bright saturated hair tips desaturate in AgX; use natural tip colours and
  slight negative exposure.
- Layer bands show on the side/back when layers are lifted too far; scalp dots
  show between sparse clumps (review hair close-ups at side and back).
- MPFB's hair editor exists, but its groom presets are a separate download.
- Generated character models (Tripo) bake hair into the mesh; this technique is
  for authored characters.

## Source

- XCOM `art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md` section 8
- XCOM `art/team/units_opus55/research.md` ("Hair research", "Hair coverage
  research"; Epic Hair Card Generator, StraySpark pipeline, Bystedt add-on,
  Godot BaseMaterial3D)
- XCOM `art/review/opus_revision_queue.md` (HUMAN opus-v3 hair row)
