# XCOM 2026-10-01: POLAR063 water-edge morph animation pilot

## Question

Can animated shoreline water be shipped as glTF morph targets on a static tile
mesh, and does the native viewer play it correctly?

## Source facts

Ten water-edge records (063-072), all floor parts with noFloor set by the
standard patches (no walking collider may be invented). Terrain objects advance
8 slots at 100 ms; the arrays repeat slots 0-3 at 4-7 (400 ms visible cycle).
White/lavender shoreline is phase-static; navy/blue wave marks and glints move
(they are not floating white chips).

## Iterations

- v1: real STEP morph clip but named generic `Animation`; woven close-view
  ripple weak.
- v2: explicit clip name; one bounded packet/roughness refinement.
- v3: `export_anim_slide_to_zero=True` did not remove the 33.3 ms buffer prefix.
- v4: keys shifted to start at 0 in the source; `loop_` prefix for Godot import
  looping. Mechanical failure: weighted target N.T reached 0.1936 because the
  installed exporter rotates target normals toward the base normal to form target
  tangents.
- v5: per-pose MikkTSpace basis computed from posed meshes; deltas = posed - base;
  sealed before hashing.

## Native method gate (root)

Unchanged C++ viewer in a test launcher; confirmed it started the imported Idle
clip, then manual sampling. Declared bounds (position 1e-4 m, UV 5e-4, N/T 4e-4;
unit/orthogonal 1e-4; handedness 1e-6), never loosened after results. Result:
startup, normalized imported pose arrays, strict N/T gates, STEP interiors and
loop continuation pass. Samples 1 us before key changes resolve to the next key
(engine approx-equal search); a 50 us control matched all slots. Four ordinary
native angles revealed a reverse-angle corrugated ripple: art held for a local
material fix, not a model redo.

## Rejected / out of scope

- Animated shader nodes or material animation pointers in glTF (not core).
- Claiming MultiMesh support: blend shapes are ignored by MultiMesh and the
  static instancer drops the AnimationPlayer.
- Measuring wave displacement from palette brightness.
Later the project moved to a static mesh + shared animated water shader method.

## Sources

XCOM `art/team/terrain_rebuild/research/polar-water-edge-animation.md`,
`art/review/polar063-native-method-plan.md`, `art/review/opus_revision_queue.md`.
