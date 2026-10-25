# tools/review: review, QA, validation, gating and catalog tools (from XCOM)

Imported 2026-10-25 from `S:/Repos/OpenXcom-Extended-3D` ("XCOM"). Every file starts with an
`Origin:` / `Changed:` comment. `ROOT = Path(__file__).parents[2]` was replaced with
`pipeline_paths.GAME_ROOT`. Direct reads of `art/asset_catalog.json` now use
`pipeline_paths.path("catalog")`. The Godot project is `pipeline_paths.path("godot_project")`, so
XCOM's `art/pipeline.json` must set `"godot_project": "xcom-3d-godot/x-com--ufo-defense-3d"`. These
tools expect XCOM's catalog schema (`assets[]` with `id`, `category`, `set`, `model`, `blend`,
`reference_image`, `review_image`, `godot_reviews`, `metrics`, `quality_review`...), which is not
trick-or-treat's schema.

Name collisions with trick-or-treat: `publish_catalog.py` was renamed `xcom_publish_catalog.py`.
No XCOM `gates.py` was ported. `root_independent_checks.py` is XCOM's gate. XCOM's
`codex_imagegen.ps1` is byte-identical to trick-or-treat's, so it was not copied.

| File | Purpose | Origin (XCOM-relative) | Dependencies | Remaining game-specific assumptions |
|---|---|---|---|---|
| `asset-review/asset_review.py` (+ `app.js`, `index.html`, `style.css`, `asset_review.bat`, `vendor/three_entry.js`) | Local web reviewer: every published asset in a live three.js view; per-asset revision notes in `art/asset_revisions/revisions.json`; zip export for outside contributors | `art/tools/asset-review/` | stdlib + browser; three.js r186 ESM bundle (MIT) built from `vendor/three_entry.js`; not committed, see `vendor/README.md` | reads `<godot_project>/assets/catalog.json` and `assets/shared_natural_terrain/manifest.json` (required); sprites from `<game>/art/reference/{units,items}`; XCOM night-shade lighting, tile sizes, `PLAYER_UNITS`, port of `natural_terrain.gd` in `app.js` |
| `review_contact_sheet.py` | Source sprite next to the four Godot review captures (`art/review/godot/<id>[/<tag>]`), written to `art/review/verified_sheets/<name>.png` | `art/tools/review_contact_sheet.py` | PIL (+ catalog_reference.save_png) | `art/review/...` layout; consola.ttf |
| `blender_review_sheet.py` | Source next to four Blender views per id | `art/tools/blender_review_sheet.py` | PIL | `reference_image` / `review_views` fields; consola.ttf |
| `material_trial_review_sheet.py` | One model + its sprite per `trial_manifest.json` | `art/tools/material_trial_review_sheet.py` | PIL | trial manifest schema; consola.ttf |
| `source_dossier_sheet.py` | Enlarged labelled source-only sheets before modelling | `art/tools/source_dossier_sheet.py` | PIL | writes `art/review/source_dossiers/`; consola.ttf |
| `catalog_reference.py` | Decode the UFO reference (PCK framing, palettes, 62-byte MCD) into identified references, build/refresh `asset_catalog.json`; `save_png`, `palette`, `decode_pck` helpers used by the sheets and kits | `art/tools/catalog_reference.py` | PIL, yaml | entirely X-COM data formats: `<game>/reference`, `bin/standard/xcom1/*.rul`, output `art/reference/verified-v2` |
| `renderer_reference.py` | Standing-unit sprite assembly transcribed from OXCE `UnitSprite.cpp` (facings, part order) | `art/tools/renderer_reference.py` | PIL | X-COM unit sprites only (dependency of catalog/audit_reference) |
| `audit_reference.py` | Audit catalog identities and assembly against the renderer source and raw bytes | `art/tools/audit_reference.py` | PIL, yaml | reads `<game>/src/Battlescape/UnitSprite.cpp`, `reference/`, `bin/standard/xcom1/items.rul` |
| `xcom_publish_catalog.py` | Publish modelled identities to `<godot_project>/assets/catalog.json` (res:// paths, variants, metrics; game-vs-original MCD record remap) and optional family review sheets | `art/tools/publish_catalog.py` | PIL (+ catalog_reference, game-side `natural_terrain.py`) | `bin/standard/xcom1/TERRAIN`, `reference/TERRAIN`, `GAME_RECORD_EMPTY`; appends `<game>/art/tools` to sys.path for `natural_terrain.py` (not ported) |
| `root_independent_checks.py` | Independent cheap gate on exported glTFs: sealed deps, triangle prims, POSITION/NORMAL/TEXCOORD_0/TANGENT, finite/unit normals and tangents, zero-area geometry/UV, COLOR_0 bounds, budgets, materials, extras, .blend presence, Godot import settings | `art/tools/root_independent_checks.py` | numpy | budgets (terrain 4000, vegetation 6000, items 12000, units 24000), `VEGETATION` families, `.blend` at `art/source/<sub>/<family>/<stem>.blend`, required import settings |
| `validate_rebuilt_models.py` | Validate rebuilt exports and references (accessors, UVs, tangents, images, .blend, review images, Godot import settings); writes `art/review/rebuilt_validation.json` | `art/tools/validate_rebuilt_models.py` | PIL | catalog must live under `<game>/art`, report under `art/review` |
| `quarantine_failed_validation.py` | Withdraw approval for catalog entries failing `rebuilt_validation.json` | `art/tools/quarantine_failed_validation.py` | stdlib | XCOM status strings |
| `record_visual_review.py` | Record an explicit completed manual review into the catalog (after validate) | `art/tools/record_visual_review.py` | stdlib | heavily XCOM-specific evidence checks: `art/review/quality_safety_holds.json`, raw-opacity proofs, `native/src/tactical_level_viewer.cpp` hash |
| `seal_model_versions.py` | Bind external glTF buffers/images (sha256) into the scene so Godot re-imports on change | `art/tools/seal_model_versions.py` | stdlib | default model path `<godot_project>/assets/models/<id>.gltf` |
| `root_gate_batch.py` | Batch gate: stage diagnostic catalog, Godot `--import`, texture policy, independent checks, capture four angles, contact sheets, under the main-project lock | `art/tools/root_gate_batch.py` | stdlib (+ Godot, PowerShell) | capture script `$XCOM_CAPTURE_REVIEW_PS1` (default `<game>/art/tools/CaptureGodotReview.ps1`, engine side); Godot exe = `pipeline_paths.setting("godot_exe")` (was the non-console `Godot_v4.7-stable_win64.exe`); `assets/review_diagnostics/<batch>` |
| `godot_main_lock.py` | Exclusive file lock for running Godot on the main project (CLI + `with main_lock(...)`) | `art/tools/godot_main_lock.py` | stdlib | lock file `<godot_project>/../.godot_main_project.lock` (same file as before for XCOM) |
| `export_health.py` | Blender: triangulate keeping custom normals, drop collapsed bevel faces, repair degenerate UV bases | `art/tools/export_health.py` | bpy, bmesh (+ kits/xcom/geometry.py) | none beyond geometry.py's materials import |
| `retime_gltf_clip.py` | Scale one glTF animation clip's time accessors without touching poses | `art/tools/retime_gltf_clip.py` | stdlib | writes an extras note naming AttackPsi |
| `gltf_io.py` | Minimal glTF accessor reader (numpy) | `art/team/guns_v2/lib/gltf_io.py` (byte-identical in `items_opus55/lib`) | numpy | none |
| `iou.py` | Silhouette IoU of a render against a sprite, plus a tinted overlay | `art/team/guns_v2/lib/iou.py` | numpy, PIL | sprite-matched render scale convention |

Not taken: `sweep_render_cost.py` (imports the XCOM `capture_*` showcase scripts by absolute path, drives
the in-game `OXP_RENDER_STEPS` panel), `test_client_lock.py` (the same lock pattern for
`OpenXcom3D.exe`), `promote_opus_models.py` (Opus variant naming rules), `review_actual_assembly_sheet.py`,
`source_metric_comparison.py`, `measure_*`, `compare_masonry_trials.py`, `grass_review_sheets.py`
(one-off sheets with fixed ids/paths), `modular_fit.py` (XCOM tile volume rules), `build_models.py` /
`model_*.py` / `reviewed_*.py` (XCOM catalog builds), the `capture_*` / `*showcase*` / `*web_archive*` /
`model_studio` scripts, and all `.gd` / `.ps1` engine-side scripts (owned by the engine port).

## From trick-or-treat

| File | Purpose | Origin | Dependencies | Remaining game-specific assumptions |
|---|---|---|---|---|
| `distance_check.py` | Shrinks a 2x2 engine preview sheet so the subject is ~N px tall (gameplay distance), nearest-neighbour enlarged, optional concept crop alongside | `S:/Repos/trick-or-treat/art/team/characters_candy/batch03/distance_check.py` | PIL | none (concept image is `--concept-image`; default `--px 70` is trick-or-treat's hero at 15 m) |

