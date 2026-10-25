# Unit and item sidecars: ragdoll, blood, sockets, handling

## What it is

Every rigged unit ships its glTF plus small JSON sidecars that the runtime reads
instead of per-unit code: `<model>.ragdoll.json`, `<model>.blood.json`,
`<model>.sockets.json`, `<model>.locomotion.json` (see `in-place-locomotion.md`),
and every item ships `<ITEM>.handling.json`. Key values are mirrored in
`asset.extras`.

## Why

Canned death clips felt slow and identical; per-species blood flipbooks and
fixed chest-wound overlays did not scale; weapon placement was hard-coded per
unit and broke on every re-export. Sidecars let one shared runtime handle every
species and every weapon.

## ragdoll.json

- Bodies sized to the mesh (capsules axis Y, height including caps; spheres for
  big heads), `total_mass_kg`, per-body mass (cap the head, e.g. 20% of 38 kg),
  joint types/offsets/limits in degrees, settle/freeze rules, push/twist values,
  hand-off velocities.
- Fit by voxelising the mesh with ray parity per column (nearest-face-normal
  inside tests mark concave-region points as inside).
- Godot port: `PhysicalBoneSimulator3D` under Skeleton3D, one `PhysicalBone3D`
  per entry, parents first; set body_offset, shape, joint_type, joint_offset,
  joint_constraints before add_child; joints bind from the pose at add_child, so
  reset_bone_poses -> add -> restore. Exception between each body and its
  parent; keep pelvis-chest collision; floor on its own layer.
- Death (current XCOM system): no lead-in or turn; on a lethal ray hit release
  the physical skeleton at once, local impulse at the actual hit offset on the
  struck body plus a uniform mass-weighted push away from the attacker (default
  0.6 m/s). Living hits: critically damped angular spring on the exact skin bone
  in a post-animation SkeletonModifier3D.
- Settle: read velocities from the physics server (PhysicalBone3D.linear_velocity
  is stale); 0.05 m/s and 0.25 rad/s for 0.3 s, 3 s cap; settle-assist damping
  after 1 s. Freeze: compute bones from bodies, keep unsimulated bones' poses,
  free the simulator; lift by the deepest below-floor vertex (cap 5 cm).
- Gates (Jolt lab, 60 Hz): centre-of-mass displacement falls away from the shot;
  floor penetration <= 1 cm at settle; no shape under the floor at hand-off.

## blood.json

- Species colour `blood_color_srgb` read from the unit's own death frames.
  Textures are tint-neutral (RGB = thickness luminance 1.0 thin -> ~0.6 thick,
  A = coverage); colour is a per-unit parameter; shared particle spray (no
  per-species flipbook).
- Wound decals on a BoneAttachment3D at the ray hit on the VISIBLE skinned
  mesh (not hit capsules), cull mask = the unit's own layer; large; a small dark
  irregular entry hole (~21% of wound diameter, 25-40% of the blood value, never
  black); drips oriented world-down at hit time, growing over 1-2 s. Floor
  splatter/pool decals: floor layer only, pool clamped inside the tile.

## sockets.json (unit) vs handling.json (item)

- Unit sockets say WHERE: belt_0..5, holster_r, back_sling (barrel down),
  eye_r/eye_l, `weapon_r` (non-deforming bone: +Y barrel along the fingers,
  +Z weapon top, head at the palm grip point), plus alien aim blocks.
- Item handling says everything about the item: fire_style (eye / shoulder /
  hip / melee / throw / none), sight_rear/front, muzzle, grip, support_grip
  (point + palm normal), stock_butt, collider, carry_class, strap points,
  `model_sha256`. carry_class picks the slot (holster -> holster_r, back ->
  back_sling, belt -> next free belt_N). Handling `*_frame` transforms are a
  fallback only for units without sockets; never compose them on a socket basis.
- Re-export sockets whenever the body changes; re-run the handling generator
  (new folder) whenever an item model changes.
- Item glTF axes: +Z forward, +Y up, +X item left, origin on the grip axis.
  Godot mount: BoneAttachment3D('weapon_r') -> item root with
  Basis((-1,0,0),(0,0,1),(0,1,0)) (det +1).

## Gotchas

- Hinge sign: Bullet/Godot report hinge angle as negative right-hand rotation
  about joint Z; choose Z so flexion is positive or knees snap straight.
- Key kinematic rotations as continuous Euler (wrapped angles spin 360 deg in a
  substep); move constraint empties with any test transform.
- Palm-normal sign bug put sockets on the back of the hand; derive the palm
  normal by the finger-curl method.
- One baked two-hand clip cannot fit every gun; runtime fingers curl to the
  held weapon's grip_contact.
- glTF has no loop flag; name looping clips with a `-loop`/`loop_` convention or
  set it on import. Don't author clips the runtime never plays (deaths are
  ragdolls).
- Duplicate the skin material per unit before adding a wound `next_pass`.

## Source

- XCOM `art/team/ORCHESTRATION_OPUS55.md` (hits/death/blood, carried items)
- XCOM `xcom-3d-godot/unit-lab/docs/local-hit-reactions.md`
- XCOM `art/review/unit_lab/sectoid_opus-v2/REPORT.md`
- XCOM `art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md` 12b-12c
- XCOM `art/team/items_opus55/research.md`, `docs/UNIT_PREVIEWER.md`
- XCOM `art/review/opus_revision_queue.md` (weapon holds, socket rows)
