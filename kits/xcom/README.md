# kits/xcom: Blender-side helper libraries from OpenXcom-Extended-3D

Imported 2026-10-25 from `S:/Repos/OpenXcom-Extended-3D` ("XCOM"). Filenames are unchanged. Every file
starts with an `Origin:` / `Changed:` comment.

**How paths work now.** `xcom_kit_paths.py` (new) puts this folder, `tools/`, `tools/review/` and
`tools/textures/` on `sys.path`. It also exposes `ROOT` (= `pipeline_paths.GAME_ROOT`) and the lane
working folders: `WORK` for AVENGER (`$XCOM_AVENGER_WORK`, default `<game>/art/team/avenger_v2/common`)
and `OPUS_WORK` (`$XCOM_OPUS_WORK`, default `<game>/art/team/terrain_rebuild/opus_batch04`). Run
Blender or Python with the XCOM repo as the working directory, or set `ART_GAME_ROOT`. The lane data
(`sources/records.json`, `notes/*.json`, `textures/gen_*.png`, `refs/`, `prompts/`) was **not** copied.
It stays in the game repo.

| File | Purpose | Origin (XCOM-relative) | Dependencies | Remaining game-specific assumptions |
|---|---|---|---|---|
| `xcom_kit_paths.py` | sys.path glue, game root, lane work folders | new | stdlib | default work folders are the old XCOM lane paths |
| `avgeo.py` | Convex-solid geometry kernel: clipping, caps, lathe/extrude/prism, UV modes ('world', 'rect', 'pre') | `art/team/avenger_v2/common/avgeo.py` | none (pure Python; works inside Blender too) | `H = sqrt(6)` level pitch (XCOM tile height) |
| `meshdata.py` | Solids to per-material triangle buffers: clip to tile box, dedupe faces, UVs, normals, tangents | `.../common/meshdata.py` | none | AVENGER material table (`WORLD`, `SWATCH`, `DECAL`), 2048 atlas, 2 m tiles |
| `gltf_writer.py` | Minimal GLTF_SEPARATE writer (Y-up, tangents, EXT_texture_webp fallback, render_dependency_sha256) | `.../common/gltf_writer.py` | stdlib | generator string names AVENGER; otherwise generic |
| `craft.py` | AVENGER v1/v2 craft solids per MAP record | `.../common/craft.py` | none | reads `WORK/sources/records.json` and `ROOT/reference/MAPS/AVENGER.MAP`, `reference/TERRAIN/BLANKS.MCD` |
| `master.py` | AVENGER v2b complete-craft master (hull, nose, canopy, gear...) | `.../common/master.py` | none | AVENGER-only content |
| `blender_build.py` | Per-record Blender build: solids to mesh, PBR materials, .blend + glTF, game-camera/orbit renders | `.../common/blender_build.py` | bpy, mathutils | `--final` writes to `ROOT/xcom-3d-godot/x-com--ufo-defense-3d/assets/models/terrain/AVENGER`, `.../assets/textures/avenger_v2`, `ROOT/art/source/terrain/AVENGER`; XCOM game camera (ortho az -45, el 30, 32x40 sprite) |
| `master_render.py` | Render the whole master from the game camera plus close-ups | `.../common/master_render.py` | bpy, mathutils | AVENGER framing constants |
| `assembly.py` | Place exported glTFs at their MAP positions and render | `.../common/assembly.py` | bpy, mathutils | `ROOT/reference/MAPS/AVENGER.MAP`; models under `ROOT/xcom-3d-godot/.../terrain/AVENGER` |
| `atlas.py` | 2048 trim atlas (decals + paint swatches) with derived normal/ORM/emissive | `.../common/atlas.py` | numpy, PIL | reads/writes `WORK/textures`, `WORK/textures/out`; AVENGER swatches |
| `textures.py` | image_gen texture processing: seam heal, regrade, normal/ORM | `.../common/textures.py` | numpy, PIL | `SETS` table is AVENGER-specific; `WORK/textures` |
| `extras.py` | asset.extras per record (MCD fields, mcdPatches, PCK frames, notes) | `.../common/extras.py` | yaml | `ROOT/reference/TERRAIN/AVENGER.MCD`, `ROOT/bin/standard/xcom1/mcdPatches.rul`, `WORK/notes` |
| `finalize.py` | Batch gates, results.json and root_gate_models.json | `.../common/finalize.py` | stdlib (+ tools/review/root_independent_checks) | hard-coded `xcom-3d-godot/.../terrain/AVENGER/<rec>.<variant>.gltf` and `art/source/terrain/AVENGER` strings |
| `inspect_v2.py` | Read-only source inspection: per-record sprite sheets, full-craft composite, SPK decode | `.../common/inspect_v2.py` | PIL (+ catalog_reference) | XCOM `reference/` layout (TERRAIN, MAPS, GEODATA, GEOGRAPH); writes `WORK/sources` |
| `make_refs.py` | Enlarged sprite crops for image_gen references | `.../common/make_refs.py` | PIL (+ catalog_reference) | AVENGER.PCK; writes `WORK/refs` |
| `measure_window.py` | Back-project windscreen sprite pixels onto planes | `.../common/measure_window.py` | numpy, PIL (+ catalog_reference) | AVENGER frames P024/P025 |
| `sheets.py` | Per-record review sheet: 8x sprite next to game-camera render + 4 angles | `.../common/sheets.py` | PIL (+ catalog_reference) | AVENGER.PCK, `WORK/sources/records.json`; Windows font `C:/Windows/Fonts/consola.ttf` |
| `master_sheet.py` | Full-craft sheet: composite vs master + views | `.../common/master_sheet.py` | PIL | `WORK/sources/*`; consola.ttf |
| `closeup_sheet.py` | Close-ups next to enlarged sprite crops | `.../common/closeup_sheet.py` | PIL (+ catalog_reference) | AVENGER frames; consola.ttf |
| `assembly_sheet.py` | Assembly vs sprite composite side by side | `.../common/assembly_sheet.py` | PIL | `WORK/sources/composite_*`; fixed crop box; consola.ttf |
| `run_gen_chain.ps1` | Sequential image_gen jobs ("prompt\|out\|ref1;ref2") | `.../common/run_gen_chain.ps1` | PowerShell, `tools/imagegen/codex_imagegen.ps1` | `-Work` default `art/team/avenger_v2/common` (relative to the cwd) |
| `opus_lib.py` | General Blender helpers for terrain lanes: sprite projection, tubes, closed-mesh checks, booleans, UV (metric/smart/atlas/repair/density), Cycles bakes, noise/fbm, review stage + cameras, render_four, glTF export, tangent orthonormalisation, finalize_gltf, MCD record read | `art/team/terrain_rebuild/opus_batch04/opus_lib.py` (the original; the `ufo_opus55/*/lib/opus_lib.py` copies only change `TEX_DIR`) | bpy, bmesh, mathutils, numpy | `PROJECT = ROOT/xcom-3d-godot/x-com--ufo-defense-3d`, `TEX_DIR` `.../assets/textures/terrain_opus_batch04`, scans under `ROOT/art/team/terrain_rebuild/texture_trials/scans`, `ROOT/reference/TERRAIN/*.MCD`; XCOM pixel constants |
| `bl_lib.py` | Blender authoring helpers: ellipsoid/box/tube (Catmull-Rom), boolean, join, remesh, decimate, degenerate-UV fix, world/metric UV, PBR material, dirt AO, save_and_export | `art/team/natural_details_opus55/tools/bl_lib.py` | bpy, bmesh, mathutils | `PROJECT` constant (unused by the helpers) |
| `sdf_mesh.py` | Implicit smooth-union capsule field + sparse surface nets + non-manifold repair (one-surface trees/roots) | `art/team/jungle_opus55/scripts/sdf_mesh.py` | numpy | lattice pitch chosen to divide 2 m (XCOM tile) exactly |
| `pose_lib.py` | World-space FK posing for the MPFB game_engine rig (`Poser`, aim_to) | `art/team/units_opus55/pose_lib.py` | bpy, mathutils | MPFB bone names; +Y front |
| `geometry.py` | Economical smooth modelling helpers (box, cylinder, ellipsoid, lathe, tube, card, world UV projection) | `art/tools/geometry.py` | bpy, mathutils (+ tools/textures/materials.py) | uses `materials.material()` presets (XCOM PBR library) |

Not taken from other lanes (deliberately): the lane `common*.py` / `jcommon.py` / `bcommon.py` /
`common04.py` copies (absolute `S:/Repos/...` roots and worker scratch paths, export/install code tied
to their batches), `craft_opus55/lightnin_lib/*` (LIGHTNIN/plane builds, `seam_proof_lib.py` only works
on XBASE2 tile seams), `guns_v2`/`items_opus55` builders and gates (item-specific socket and budget
rules), the `ufo_opus55/*/lib` copies (same as opus_lib plus UFO hull builders), `units_opus55/common.py`
(MPFB/sectoid paths), and the `*_snapshot_*` files.
