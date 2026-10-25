# XCOM 2026-10-01: first unit checked at runtime (Sectoid opus-v2 unit lab)

## Setup

Isolated Godot 4.7 project (Forward+, D3D12, Jolt at 60 Hz like the main
project); main project never opened. Lab asset copies byte-identical to the
deliverables (21 files, SHA-256). One script runs import -> checks + headless
drop tests -> off-screen capture at fixed 60 fps -> contact sheet (~1 min).

## Measured

- Import: 20,423 triangles = glTF (skin 20,138, eyes 285); 4 weights/vertex;
  tangents present; 53 bones, rest height 1.633 m; ORM bound correctly; 7 clips
  (41 tracks each).
- Ragdoll: 16 bodies from JSON; rest centres and joint origins match to 0.01 mm;
  limits read back exactly.
- Death: falls exactly along the shot (alignment 1.00) in all six directions;
  peak 4.9 m/s (Blender predicted 4.8); no NaN; settled on threshold (1.28-2.58 s),
  never the 3 s cap. Visible skinned mesh past the tile edge: 0.40-0.41 m on
  straight falls, 0.12 m diagonal.
- Physics variants: Jolt default best balance; penetration slop 5 mm tighter
  (0.7 cm pelvis-chest); Jolt 120 Hz and Godot Physics hit the 3 s cap more;
  removing pelvis-chest collision worse.
- Blood colour space verified (linearised 0.25 vs expected 0.26; 0.80 if not).

## Problems found (by severity)

Medium: head 0.40 m past tile on straight falls (geometry of a 1.63 m body with a
0.54 m cranium); no armed low hold / no right-hand socket in Idle/Walk; hit spray
3-6 px at battlescape zoom. Low: identical spread-eagle corpses; clavicles 2.9 cm
off at hand-off; pelvis/chest boxes 1.7-2.0 cm into each other; mesh 1.2-1.6 cm
under floor; brief joint-limit overshoot (hands spin to 40 rad/s); snap-turn on
lethal frame; glTF has no loop flag; headless imports left textures without
mipmaps; skin read lighter/pinker than the sprite mid-tone #8a6c64.

## Decisions that followed

- 2026-10-02: snappy death (0.1-0.15 s directional hit reaction, immediate
  ragdoll, small push, later a whole-body twist); then 2026-10-03 overhaul: no
  lead-in at all, local impulse at the real hit point plus uniform push (current
  system; see `unit-sidecars.md`).
- Per-asset albedo darkening after calibration was reverted (lighting rule).
- Porting notes became the runtime spec: PhysicalBoneSimulator3D setup order,
  physics-server velocities for settle, Jolt slop 0.005, AnimationPlayer in
  physics callback mode, floor-only decal cull, per-unit material copy.
- Unit work paused 2026-10-07 pending new generated (Tripo) models.

## Sources

XCOM `art/review/unit_lab/sectoid_opus-v2/REPORT.md`,
`art/review/opus_revision_queue.md` (SECTOID rows),
`art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md` 12b-12c.
