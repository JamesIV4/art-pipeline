# Adding thickness safely (Solidify and paired-shell checks)

## What it is

Rules for giving thin surfaces (garments, armour plates, leaf laminae, panels)
real wall thickness in Blender, and the checks that prove the result is a
closed outward wall rather than a crossed or spiked shell.

## Why

In XCOM's unit garment pilot a declared 3 mm Solidify produced shell vertices
at Z = 2.61 m on a model whose outer surface ended at 2.00 m: compensation
amplified 3 mm to ~1.84 m at two underarm vertices. The first guess (collar
topology) was wrong; measuring found neighbouring edges of 16-73 mm with
normals approaching 175.7 deg between adjacent faces.

## How

1. Use ordinary offset by default: `use_even_offset=False`,
   `use_quality_normals` off unless needed. Even offset / quality normals
   compensate sharp corners and are what amplify thin folded topology.
2. Thickness from the real part: garments ~3 mm, armour plates 6-10 mm inward,
   laminae ~2 mm. Choose clamps from the actual mesh, not a global magic value:
   `thickness_clamp` limits by neighbouring edge scale,
   `use_thickness_angle_clamp` also considers angles. A clamp does not fix a
   malformed fold or collapsed face; Complex mode is an option for topology that
   needs it, not an automatic cure.
3. Decimate the outer surface before solidifying, not after.
4. Diagnose on a NEW derivative, one localized diagnostic, not a matrix:
   identify the outer faces feeding the extreme shell vertices, check folded or
   sliver topology, adjacent edge lengths, winding and object scale, and first
   separate ordinary normal offsets from compensation amplification. A plain
   ordinary-offset diagnostic stayed at 2.99994-3.00005 mm.
5. Repair locally: restore the affected region against a verified helper surface
   with interpolated helper normals; remove sub-millimetre seam slivers; replace
   folded connectivity with a bounded patch (grid fill on edge-connected islands
   with simple boundaries; split degree-4 figure-eight boundaries into islands);
   bounded local fairing (smooth only the stored crossing neighbourhood). Never
   move/shrink the body or globally inflate the garment to hide spikes.
6. Thickness may vary by measured free space (vertex-group factor), but below
   ~0.35 mm is not a cure.

## Gates (on the final wall)

- Actual inner/outer offsets and shell extents measured.
- Paired shell direction per local face pair (no reversed pairs).
- Closed, contiguous, outward wall; zero non-manifold edges.
- Body clearance (no body-intersection pairs; minimum sample clearance) and
  nonadjacent self-intersection pairs counted.
- Re-run real shoulder/elbow/hip/knee bends on the corrected wall; earlier
  inward-wall bend images are not proof.
Positive sample clearance and zero non-manifold edges do NOT override reversed
pairs or intersections (v06: 0.673 mm clearance, still 21 reversed pairs, 10
body intersections, 232 self-intersections).

## Better alternative when possible

For skinned clothing, avoid a thick closed wall over a hidden body: derive the
garment from the body, delete the body under it, and only turn hems inward
(`garment-workflow.md`). That removed the whole failure class.

## Gotchas

- "Outside" for open cloth comes from nearest normals of the unchanged body,
  never from signed volume.
- Positive whole-component volume hides locally crossed folds; check pairs.
- A check run before a later construction step overwrites geometry is not a
  final-geometry check.
- Thin-feature closures (neck/wrist caps) must be explicit nondegenerate
  triangle fans built before masked decimation, with perimeter and neighbouring
  rings locked (weight 0); protecting a bad n-gon is insufficient.

## Source

- XCOM `art/review/units-solidify-spike-guide.md`
- XCOM `art/team/units_rebuild_max/research.md` (V05-V08 sections)
- XCOM `art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md` section 5
  ("Walls, edges, binding")
- XCOM `art/review/diagnostics/vegetation_shell_diagnosis_max/evidence.json`
- Blender Solidify manual / 5.1 API (cited in the guide)
