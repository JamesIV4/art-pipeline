# Vegetation structure: continuous wood shells, thickened laminae, orientation gates

## What it is

The geometry side of realistic (non-stylised) plants: a wood skeleton that is
ONE closed surface flaring from trunk into roots and limbs, optional thickened
leaf/frond laminae built as paired top/bottom shells, and the mechanical gates
that catch inverted, detached or inward-wound parts. Leaf foliage itself is
cards; see `foliage-cards.md`.

## Why

XCOM's first vegetation passes failed on: thick trunks, limbs as separate
cylinders pushed into the trunk with a visible crease, dead fronds modelled as
sawn wooden limbs ("brown is not bark"), leaves upside down, coplanar fans that
only work from the source camera, and "positive volume" checks that passed
models with locally reversed folds.

## How: one continuous wood surface (implicit field)

1. Skeleton: tapered capsule chains per branch (roots flattened, z-scale 1.35).
2. Smooth-union each subtree into its parent with a per-level fillet k
   (polynomial smooth minimum, Quilez `smin`): trunk->roots 0.30,
   trunk->co-stem 0.22, trunk->limbs 0.15-0.16, limb->branches <= 0.07,
   ->twigs 0.028.
3. Polygonise with naive surface nets: sparse 16^3 blocks culled by branch
   AABBs, one Newton step onto the zero set, quad orientation from the inside->
   outside sign change. Choose lattice pitch that divides the tile (1/64 m
   horizontally, sqrt(6)/157 vertically for 2 m tiles) so a column duplicated by
   2 m is bit-identical (max error 2e-14 m). Twigs >= 1.6 lattice cells radius.
4. Repair non-manifold edges where thin twigs graze lattice faces (remove the
   triangles around them, fan-close, verify every edge used twice).
5. Normals from the field gradient (identical on both sides of cut rings).
6. Bark UVs flow across joins: per-branch chart (u = k*theta/2pi with
   rotation-minimising frames, v = arc length / 0.8 m); a child chart starts at
   the parent's u/v; blend charts across the flare by capsule-distance
   difference (w = 0.5 at the crotch). Let v keep growing past branch ends (twig
   tip poles were UV-degenerate).
7. Clip the field flat below the deepest root (z = -0.45 m) so no slivers.
Alternatives rejected: voxel remesh of unioned tubes (no fillet, not
translation-exact), Skin modifier (junction artefacts). Simpler fallback when an
implicit pipeline is overkill: loft the trunk cross-section into lobes, or
remesh-union then smooth/retopologise, with bark UVs flowing across the join.

## How: multi-tile trees

Assign every skeleton segment an owner tile; bisect perpendicular to the branch
at owner changes; simplify the cut ring once with a canonical start/direction so
both neighbours get the identical ring; decimate each piece with ring vertices
locked (vertex-group weight 0, factor 1000; also lock a 2.2 cm band). Caps are
fans with reversed winding and procedural end grain; back-to-back caps are
invisible when assembled.

## How: thickened laminae and tubes

- Build fronds/leaves with an explicit physical frame: minimum-transport frame
  along the midrib; world-gravity curvature applied separately from texture/
  profile roll. Never bend in a rolled local "up" frame: at roll 1.8 rad,
  cos(roll) < 0 and a "downward" bend curves upward.
- Petiole/rachis tubes: test basis handedness, radial outward winding and cap
  orientation explicitly.
- Single-surface masked leaves are allowed (6 triangles per gently curved
  leaf); mark paired-shell checks N/A for them explicitly rather than waiving.

## Gates (run on the FINAL exported geometry)

- Wood closed, positive volume, generalized winding number per face (Jacobson
  et al. 2013), caps outward.
- Thickened laminae: local paired top/bottom shell direction per organ, not
  whole-component volume (a positive total hid a crossed fold).
- Attachment: card/leaf bases lie inside the ACTUAL exported wood (winding
  number), with actual opaque texel contact, not inside a declared capsule or
  "equal route arrays".
- Multi-tile: every cap meets an identical opposite cap; no record's wood enters
  another's.
- Orientation: upper/lower face, base-to-tip UV registration, growth/gravity
  direction, four angles. Hanging leaves can be right; inversion is not droop.

## Gotchas

- A check computed mid-construction then invalidated by a later overwrite
  (lower shell rebuilt from averaged top normals) left a manifest claiming a
  positive minimum while the final shell was crossed (JUNGLE009 v13).
- Hard XY/Z box clipping leaves floating opaque tips and rectangular panels; a
  sprite crop edge is not a physical cut.
- Double-sided use of one photo does not tell you which face is upper.
- Atlas orientation registration by "lowest opaque band" is not an anatomical
  landmark.
- Unknown species stay unknown; damage records are often the same plant
  damaged (MCD Die links), not new burnt trees or log piles.
- Manifold boolean in Blender 5.1.2 dropped the second operand's material
  indices (UVs survive); carry region tags in a temporary UV layer.

## Source

- XCOM `art/team/vegetation_anatomy_max/opus_batch03/research.md`
- XCOM `art/team/vegetation_rebuild/orientation_anatomy_audit_v13/confirmed_findings.md`
- XCOM `art/review/anatomy-dense005-v5-workflow-note.md`,
  `art/team/vegetation_anatomy_max/dense_crown005_pilot/*.md`
- XCOM `art/review/diagnostics/vegetation_shell_diagnosis_max/evidence.json`
- XCOM `art/TEAM_REQUIREMENTS.md` ("Vegetation-specific quality gate")
- XCOM `art/team/terrain_rebuild/opus_batch01/research.md` (Manifold boolean)
