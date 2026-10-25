# In-place locomotion clips with distance-driven playback and ground IK

## What it is

Locomotion clips authored strictly in place (no root motion) and played back by
distance travelled rather than time, with hand-rolled blending, foot locking and
ground-conforming leg IK. Built for a host game that owns unit position and
timing, but the method applies to any game where gameplay code moves the unit.

## Why

The host (OpenXcom) moves a unit one 2 m tile in 8 walk phases at a user-set
speed (30 ms per phase default: ~0.25 s per tile, about 7-8 m/s, i.e. running),
turns in place at corners, and stands units at one height per tile. Time-driven
walk loops slid, snapped at stops and popped on stairs.

## How: authoring (Blender)

- One shared clip definition (`run_poses.py`) solved on each rig with the pose
  library: rigs share bone names but not rest poses (hip 1.08-1.21 m), so each
  rig gets its own bake and its own `<model>.locomotion.json` (loop_ground_m,
  nominal speed, contact phases, mid-stance entry points).
- A run is a gait per creature (heavy charge, low lope, slither waves, hover
  surge), not a faster walk.
- Loop of ~5 s: 18 steps (9 strides) at nominal 7.2 m/s; step = 1.8 x hip
  height; contact 40% of a step (a flight phase every step); trunk lean ~12 deg
  (9 armed). Periodic variation across the loop: step length +-3.5%, arm
  amplitude +-12%, pelvis yaw +-15%, foot placement +-1.2 cm, toe-out 3-7 deg,
  heel lift +-8%. The stance ball moves back at exactly nominal speed (within
  0.65 mm).
- Variants share holds: armed runs keep the idle-armed grip relative to the chest
  so sockets match. Append to the published glTF by joint name (existing
  animations byte-identical), new .bin, re-seal.

## How: runtime (Godot, SkeletonModifier3D first in the stack)

- Phase += horizontal distance moved / loop_ground_m (not 3D length on ramps).
  Cadence cap 1.6x nominal with a 0.6 m carry so uneven per-frame jumps are paid
  back, not dropped. Enter a fresh move at the next mid-stance after the last
  stop.
- Blend by hand: slerp each bone from the AnimationPlayer pose by
  vis = smoothstep(weight); keep `influence` at 1 (influence did not attenuate
  the modifier in this stack); the standing clip plays underneath the whole time.
  In 0.22 s, out 0.28 s, from any loop point; clip switches crossfade 0.25 s.
- Hysteresis: a corner hold of 0.20 s after a turn; anything still for 0.25 s
  has stopped; the stride runs on while fading out (never a held stride). At a
  corner a planted foot waits and pivots while the host turns the unit.
- Foot lock: pin the ball where it landed; never pull more than 0.22 m (beyond
  that it slides); release over 0.08 s; pelvis drops up to 12 cm when a leg cannot
  reach.
- Leg IK writes LOCAL ROTATIONS only (composed from model-space rotations), knee
  keeps the clip's pole. Writing global poses popped thighs 25-50 deg at blend
  ends.
- Ground IK: sample the drawn top surface per tile from its rendered meshes
  (up-facing triangles in 25 cm buckets; highest surface <= floor + 0.62 m and
  >= floor - 1.0 m); each sole point samples its own position; foot tilts to the
  averaged normal (clamp 28 deg); pelvis to the lower foot; smoothed 0.08 s,
  rate-limited 0.9 m/s. Stack order: Locomotion, GroundIK, AimIK, Recoil,
  LocalHitReaction.

## Gotchas

- "Snaps only on some rigs": stride length vs the 2 m tile decides whether
  stops land in contact (male step 2.002 m always stopped in flight; female
  2.181 m drifted into contact and showed the lock snap). Fix the mechanism, not
  the stride.
- The host's walking phase was published modulo 8, but diagonal steps last 16
  phases: units jumped back half a step mid-diagonal. Use full phase.
- Test at host speed settings 1, 30 and 60.
- Residual: corner contacts slide 6-18 cm; diagonal stairs 4-8 cm.

## Source

- XCOM `art/team/units_opus55/run_humans_v1/DESIGN_NOTE.md`
- XCOM `art/review/opus_revision_queue.md` ("walk -> run cycle" requirements row)
- XCOM `docs/BATTLESCAPE_3D_INTEGRATION.md` ("Unit placement while walking",
  "Unit grounding")
