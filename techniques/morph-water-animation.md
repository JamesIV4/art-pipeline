# Animated surfaces via glTF morph targets (water shore pilot)

## What it is

Conservative surface animation (water undulation at a shoreline) exported as
glTF morph targets (shape keys) on one static mesh, with fine ripples in normal
/ORM maps, plus the method gate that proves the engine actually plays the
imported morphs.

## Why

glTF core animation exports transforms, bone poses and morph weights, not
animated shader nodes. Sprite water showed moving wave marks over a static
shoreline; earlier attempts modelled moving white "chips" as rigid geometry.

## How

1. Finalise topology, triangles, winding and UV charts BEFORE adding keys; keys
   keep identical vertex order; no modifier/dissolve/validation afterwards (the
   static exporter needed a non-mutating route).
2. Surface motion: a bounded sum of directional waves (GPU Gems ch. 1), resolved
   undulation in the mesh, finer ripples as ordinary +Y normal/ORM maps; one
   connected opaque closed shallow volume with two PBR surfaces; snow bank and
   tile boundary fixed.
3. Map source phases explicitly: XCOM terrain animated 8 slots at 100 ms; many
   arrays repeat slots 0-3 at 4-7 (400 ms visible cycle). Identical-pixel phases
   share one authored pose; record phase labels and timing in a key manifest.
4. Export one named clip with a loop convention (`loop_<ID>_Idle`; Godot imports
   clips starting/ending with `loop`/`cycle` as looping). Shift keys to start at
   frame 0 explicitly; check actual buffer times.
5. Morph normals/tangents: compute per posed mesh (see `tangent-integrity.md`).
6. Engine proof (one bounded method gate): load the unchanged viewer with the
   exact catalog in a test launcher; confirm it selected and started the clip;
   switch to manual sampling (`seek(t, true)`, manual `advance` for loop
   continuation); dump imported base/morph arrays, key paths/times/interpolation,
   slot interiors and boundaries. Compare to the sealed glTF with declared
   bounds: position 1e-4 m, UV 5e-4, N/T 4e-4; unit/orthogonal 1e-4, handedness
   1e-6. Never loosen a failed bound after seeing results. Account for Godot
   storing full target positions (normalized) vs glTF additive deltas, and
   importer vertex reordering.
7. Then the usual four native angles + source sheet; extra phase screenshots only
   for a visible discrepancy.

## Gotchas

- Godot MultiMesh ignores blend shapes; a static instancer that extracts meshes
  also drops the AnimationPlayer. Standalone preview and instanced rendering
  are different certifications; animated tiles need their own node path or a
  shader-based alternative.
- Blender ACTIVE_ACTIONS exported a real clip named generic `Animation`; the
  merged-animation-name setting is what names it.
- Buffer timing began at 1/30 s; `export_anim_slide_to_zero=True` did not remove
  the prefix in that mode; shift keys in the source.
- STEP keys sampled within 1 us of a key change resolve to the next key in
  Godot (approx-equal search); do not claim exact edge timing.
- A reverse-angle woven/corrugated ripple only showed in the four normal native
  angles: a material fix, not a model redo.
- Alternative adopted later at map scale: a shared animated water shader on a
  static mesh, which also instances.

## Source

- XCOM `art/team/terrain_rebuild/research/polar-water-edge-animation.md`
- XCOM `art/review/polar063-native-method-plan.md`
- XCOM `art/review/opus_revision_queue.md` (POLAR 063 row)
