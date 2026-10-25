# Tangent and normal integrity through glTF export

## What it is

The set of export practices and checks that guarantee every exported vertex
has a finite unit normal, a finite unit tangent orthogonal to it with w = +/-1,
and consistent handedness, including on morph targets and grafted meshes.

## Why

Tangent failures were XCOM's most frequent silent export defect: the glTF
exporter dropped TANGENT entirely for n-gon/quad caps; MikkTSpace produced zero
tangents on sub-micron bevel slivers and acute clipped rims despite non-zero UV
area; morph-target tangents came out non-orthogonal (N.T up to 0.19); raw
generated meshes (Tripo GLBs) had no tangents at all. Normal maps then shade
wrong or Godot recomputes something different from the baker.

## How

1. Finalise topology and UVs, then triangulate explicitly (Triangulate modifier,
   Fixed/Clip, `keep_custom_normals=True`) BEFORE baking normal maps and before
   export. Quads/n-gons make the exporter print "Could not calculate tangents"
   and silently omit TANGENT.
2. Clean degenerate tessellation: `bmesh.ops.dissolve_degenerate(dist=1e-7)`,
   re-triangulate, recalc normals; repair zero-determinant UV triangles by a
   local dominant-axis planar projection that stays near the authored crop
   (XCOM `art/tools/export_health.py::prepare_static_mesh`, port `kits/xcom/`);
   then Weighted Normal (face area, keep sharp). Assert no face area <= 1e-12.
3. For small faces in big charts, use local face-plane UV charts with
   orthonormal geometric axes at metre scale (large absolute UVs cancel
   numerically on tiny faces).
4. Recompute MikkTSpace tangents after any graft or UV edit, and export them so
   the baker and engine agree. Raw generator meshes: compute in Blender.
5. Validate on the exported buffers (not the Blender mesh): finite; |N| and
   |T.xyz| within 0.01 of 1; |w| = 1; |N.T| < 1e-3; all corners of a triangle
   share handedness; zero-area geometry and UV triangles = fail. See
   `independent-review-gates.md`.
6. Morph targets (water, faces): compute each posed mesh's actual MikkTSpace
   basis (`Mesh.calc_tangents` on the posed mesh, matching exported corners),
   derive target N/T from real positions + same UVs, normalise/project numeric
   error only, then encode delta = posed - base. glTF morph deltas are additive
   XYZ with unchanged handedness. Gate every distinct pose and intermediate
   blends.
7. Scoped fallback (only with explicit approval): for a zero-length Mikk
   tangent on a newly clipped flat rim whose geometry/UV are non-degenerate,
   derive dP/du, dP/dv in float64 from the actual triangle, project dP/du onto
   the corner normal's plane, normalise, w = sign(dot(cross(N, T), dP/dv)); must
   agree with the other corners. Never for bad normals, degenerate UVs, inward
   shells or as a general patch. Preserve all healthy Mikk values.

## Conventions to keep straight

- glTF B = cross(N, T) * w; normal maps +Y (OpenGL).
- Exported UV V = 1 - Blender V; convert back before comparing gradients.
- Blender's Z-up -> Y-up export is a proper rotation; it does not flip w. Do not
  flip normal maps or infer a w flip from the V flip.
- MeshLoop tangents are derived/read-only; if you author an explicit tangent,
  keep it as a CORNER attribute in the source and record why.

## Gotchas

- Installed Blender 5.1 `primitive_extract.py` rotates the morph target normal
  back toward the base normal to form target tangents (a TODO-marked routine);
  do not trust exported morph tangents without checking.
- A single 0.000000119 m bevel edge produced a zero tangent; fix by removing that
  face (export-health), then re-render the four-angle sheet.
- Fused or n-gon caps on item models: triangulate before export or TANGENT
  vanishes for the whole primitive.
- Tangents present is not tangents valid; check unit length and w.

## Source

- XCOM `art/team/vegetation_anatomy_max/coverage_batch06/shared_live_form_v3/tangent_research_and_decision.md`
- XCOM `art/team/terrain_rebuild/research/polar-water-edge-animation.md`,
  `research/mesoscopic-material-pilots.md`
- XCOM `art/team/environment_replacement/root_gate_feedback.md`,
  `worker_visual_review.md`, `research.md`
- XCOM `art/team/items_opus55/research.md`,
  `art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md` 12c
- XCOM `art/team/research/tripo_hands/GUIDE.md` section 8
- XCOM `art/tools/export_health.py`, `root_independent_checks.py`
