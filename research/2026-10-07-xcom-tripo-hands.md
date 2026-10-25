# XCOM 2026-10-07: hands on generated (Tripo) characters

## Question

Tripo-generated humans had half-fist hands that crumpled on weapon grips. How do
studios rig and animate hands on unrigged generated models?

## Findings (research only, nothing installed)

- No generator or auto-rigger reviewed reliably produces game-ready fingers.
  Tripo's auto-rig documents no finger bones; Mixamo, AccuRIG and Cascadeur need
  open separated fingers.
- Industry pattern: replace bad hands with a rigged template hand; keep hand
  poses as a small pose library; pin the support hand to a weapon socket with
  two-bone IK at runtime; bind rigid plates to one bone each.
- Bone heat fails or bleeds on thin touching digits; voxel heat fuses fingers
  unless the grid is fine. Best free weights: Data Transfer (Nearest Face
  Interpolated, masked) from a template hand, or the Robust Weight Transfer
  add-on (SIGGRAPH Asia 2023); then limit to 4 and normalise.
- Seam: a hard change in wrist/forearm-twist weights at the graft ring opens the
  wrist under rotation (a 0.142 m lethal-hit gap was a symptom); blend over 3-5 cm.
- Animate fingers as a mitten (curl + spread + thumb) on full 3-bone chains; at
  game zoom the readable silhouette is a closed hand with a visible thumb.
- Support-hand shortfall (4-5 cm): yaw the chest toward the gun, protract the
  clavicle up to ~15 deg, pull the gun in 2-3 cm, only then accept a gap; never
  stretch the arm. Gate: support palm within 1 cm of `support_grip`.
- Plates: 100% one bone; joint-crossing plates on a 30-50% helper bone; gate
  plate edge change <= 2%.
- Materials: metallic 0 except real metal (Tripo face metallic up to 0.34 made
  faces silvery); raw GLBs have no tangents: compute MikkTSpace after the graft.

## User correction (same day, overrides the graft-first recommendation)

Our Tripo meshes DO have separated fingers: the fault was our finger bone
placement, animation and weights. Default: put each finger chain on measured
knuckles with roll in the curl plane, weight per finger from its own geometry,
verify against the grip pose library. The graft is a fallback only for truly
fused fingers.

## Generation brief for future characters

T/A-pose concept, open flat hands, fingers slightly apart, thumbs out, palms
down, nothing held; generator quad / smart-low-poly off (caps faces at 10-20k
and forces FBX); regenerate only for broken wrists/forearms or hands fused to
the body.

## Sources

XCOM `art/team/research/tripo_hands/GUIDE.md`, `art/review/opus_revision_queue.md`
("Tripo hands pipeline changes", Tripo humans/aliens rows).
