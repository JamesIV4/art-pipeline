# Humanoid bodies and rigs: CC0 base retargeting, generated-mesh fitting, hands, head grafts

## What it is

How XCOM produced rig-compatible humanoid units that share one skeleton and
animation library: (a) authored units from a CC0 MPFB/MakeHuman base reshaped by
a custom per-bone skin before the rig is refitted; (b) generated meshes (Tripo
GLBs) normalised into the same frame, weighted by heat on a voxel proxy, with
finger chains placed on measured knuckles; (c) head and hand grafts between
variants; (d) a shared pose library re-solved per rig.

## Why

Primitive body parts and per-unit rigs made every unit a one-off and broke
animation sharing. Pose-bone scaling cannot separate length from thickness.
Projecting a human head onto an alien skull folded eyelids/mouth/ears into
slivers. Generated hands crumpled on grips because of OUR finger bone placement
and weights, not the mesh.

## How: authored base (MPFB)

1. `HumanService.create_human(macro_detail_dict=...)` (soldier: gender 1, age
   .5, muscle 1.0, weight .6; small aliens: child macro gender .5 age .19).
   Bake the macro shape, scale uniformly to contract height (soldier 22 voxels x
   sqrt(6)/24 = 2.2454 m; aliens use their own standHeight), rotate so front =
   facing 0.
2. Reshape with your own linear-blend skin per deform bone: separate length and
   lateral/anterior thickness factors, a mid-bone dip `1 - k*sin(pi*s)` for knobby
   joints, chained bone heads. Proportion changes belong here (stage 1); derive
   factors from a probe in the target stance (Sectoid arm chain x0.79).
3. Move MPFB joint cubes with the body, change no topology, delete the temp rig,
   then `add_builtin_rig(body, 'game_engine', import_weights=True)` again: same
   53-bone rig, CC0 weights, bone heads on landmarks (0.1 mm).
4. All topology edits after the rig (helper deletion, digit removal, head
   replacement); bmesh keeps vertex groups on survivors.
5. Alien head: cut at the head-weight 0.9 contour after diffusing the weight
   field (40 passes), keep the largest loop as the neck ring, build a ring grid
   on an implicit skull fitted to measured source rows (face-dense azimuth warp),
   zip to the neck ring, Taubin-smooth the junction band, new vertices 100% head.
   Flatten the face plane or eyes wrap out of 3/4 views. One field drives socket
   and lens.
6. Digits: delete faces > 0.5 weighted to removed finger bones, fill, poke,
   subdivide, smooth a dilated mask; keep the bones in the rig, unweighted.
7. Decimate with a vertex-group mask: 0 locked (face features, every cut
   boundary ring), ~0.1 hands/feet, ~0.18-0.6 cranium, 1.0 elsewhere. Hands were
   7.2k of 14.7k exposed-body triangles: they are the budget.

## How: generated meshes (Tripo)

- Generate for a good body: T/A-pose concept, open flat hands, fingers slightly
  apart, nothing held; leave the generator's quad/low-poly modes off.
- Normalise into the human frame; landmarks per model (override JSON with the
  geometry hash when auto-detection picks e.g. goggle rims for eyes).
- Body weights: bone heat on a voxel proxy (~11 mm voxels) that must cover >= 90%
  of body height and the torso, head and both legs (a sleeve-only proxy passed
  "no unweighted vertices" yet covered 10%: reject). Finger heat off on the proxy.
- Fingers: chains on the measured knuckles (centreline and creases), roll in the
  curl plane, per-finger weights from finger geometry (islands or geodesic
  distance), no bleed. A template-hand graft is the fallback for truly fused
  fingers: flood-fill cut at a clean forearm ring 3-6 cm above the wrist,
  length-ratio scale (keep near 1.0: S/M/L templates), radial blend, zipper
  strip, and blend wrist/forearm-twist weights over a 3-5 cm band (a hard twist
  change at the ring opens the wrist under rotation).
- Rigid plates: one bone each, helper bones at 30-50% for joint-crossing plates,
  edge-length change <= 2%. Metallic 0 except metal islands; recompute tangents.
- Animate hands like a mitten (four-finger curl + spread + independent thumb)
  on full 3-bone chains; a pose library (relaxed, fist, pistol grip, rifle grip,
  support cradle, two-hand pistol support, point, open) exported as named
  per-bone data shared by Blender and runtime.

## How: grafts and retiming

- Head graft between variants: transfer rest positions using the original glTF
  joint matrices weighted by existing influences (not Blender's imported bone-tail
  guesses); plane-cut the neck to a level rim, short neck sleeve inside the
  collar, fill small openings with matching-colour surfaces (broad flat caps
  poked through armour); recolour exposed skin per channel in linear light from
  the donor's cheek colour.
- Keep original animation bytes; append new clips by joint name into a new
  buffer and re-seal. Retime all actions to one fps (24/60/30 -> 60) including NLA
  strip timings; fix inherited exporter timelines by scaling only that clip's
  time accessors.

## Gotchas

- Weights normalised, <= 4 influences; join skinned parts only after weighting.
- Uniform-density ragdoll makes a big alien head ~60 kg; fix head mass.
- PowerShell: `R` is an alias (Invoke-History); empty-string args are dropped to
  native exes; Blender stderr becomes NativeCommandError (grep logs instead).
- EEVEE in background crashed after many renders of ~20k-tri units in one
  process: render 1-2 per Blender run.
- Glove/size mismatch distorts knuckles; graft reads smoother than the forearm:
  bake a forearm detail layer onto the hand atlas and fade over 2-3 cm.

## Source

- XCOM `art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md`, `ALIEN_HUMANOID_TIPS.md`
- XCOM `art/team/research/tripo_hands/GUIDE.md`
- XCOM `docs/HUMAN_RIGS_20261008.md`, `docs/HUMAN_HEAD_GRAFTS_20261008.md`
- XCOM `art/tools/fit_tripo_human.py`, `retime_gltf_clip.py`,
  `finalize_human_blend.py`, `graft_human_head_blender.py`
