# Changelog

Every change to `tools/`, `kits/` or `engine/` gets an entry: what, why, affected games, migration.
Knowledge-only changes (techniques, research) don't need one unless they change a rule in `docs/`.

## Unreleased

## 2026-10-25: initial import

Extracted from trick-or-treat (`S:\Repos\trick-or-treat`) and OpenXcom-Extended-3D
(`S:\Repos\OpenXcom-Extended-3D`); both source repos were only read.

### Added
- `tools/pipeline_paths.py` (new): game-root resolution (`ART_GAME_ROOT`, nearest `art/pipeline.json`,
  cwd) and per-game paths/settings; defaults reproduce trick-or-treat's layout.
- From trick-or-treat `art/tools/`, path-parameterised, logic unchanged: `gates.py`,
  `publish_catalog.py` (published fields = `publish_fields` setting), `make_palette.py` and
  `make_materials.py` (C++ header namespace = `cpp_namespace`, `null` paths skip outputs, generated
  `toon.tres` res:// paths are settings), `kits/lowpoly/lowpoly_kit.py` (scale-post height/colour and
  build-stamp key are settings), `tools/vfx/{make_vfx,make_fire,assemble_vfx}.py`,
  `tools/audio/{fm_synth,make_sfx,make_music}.py`, `tools/imagegen/codex_imagegen.ps1` (`-Root`,
  `-Codex`). `make_fire.py` is the 2026-10-25 procedural heat-field flame that replaced
  make_vfx.py's teardrop.
- Lane kits from trick-or-treat `art/team/*/batchNN/` into `kits/lowpoly/`: yard_common, farm_lib,
  dk_kit, foliage_common, cv_kit, mon_kit, lm_common, decor_common (decor_ground), vine_kit, car_kit.
  Imports now resolve within `kits/lowpoly`; cv_kit writes `results/` and `tiles/` next to the
  running build script instead of next to the kit.
- New generalised tools from lane scripts: `tools/set_palette_row.py`, `tools/catalog_register.py`,
  `tools/inspect_gltf.py`, `tools/review/distance_check.py` (concept image is a parameter).
- `tools/sync_engine_addon.ps1` (new): vendors `engine/godot` into a game as
  `res://addons/art_pipeline/` with a `VERSION.txt`; `-Diff` lists game-side edits to upstream.
- From XCOM: `kits/xcom/` (avenger_v2 common set, opus_lib, bl_lib, sdf_mesh, pose_lib, geometry,
  `xcom_kit_paths.py`), `tools/textures/` (materials, PBR derivation, WebP finalise, dedupe, import
  policies, CC0 fetch, with tests), `tools/vfx/{fx_sims,pack_atlases}.py`, `tools/review/` (asset
  reviewer, sheets, reference/catalog tools, independent checks, batch gate, validation, sealing,
  locks, glTF helpers; `publish_catalog.py` renamed `xcom_publish_catalog.py`). See each README for
  remaining XCOM assumptions.
- `engine/godot/`: toon, grass, sky, pickup, trail and XCOM fx/foliage/ui shaders; post_fx +
  contact_fx (constants exported, NodePaths); materials; night-storybook and XCOM-day environment
  presets and rigs; `project_rendering.cfg`; `review/` (GDScript asset previewer port of
  trick-or-treat's C++ preview mode, `asset_preview.ps1`, `review.ps1` with opt-in `-BuildNative`,
  `godot_lock.ps1`, `art_pipeline_paths.ps1`, `CaptureGodotReview.ps1`, render-control scripts).
- `docs/` (toolchain, game layout, asset conventions, quality contract, lane/batch workflow, review
  gates, catalog schema, team brief template), 51 `techniques/` notes, 22 dated `research/` notes,
  `examples/` (trick-or-treat build scripts, catalog sample, palette/material specs, brief,
  checkpoint; example `pipeline.json` files), `CLAUDE.md`, `AGENTS.md`.

### Not imported (deliberately)
- Generated outputs and binaries (models, renders, review sheets, `.blend`, audio, caches), the
  vendored three.js bundle (rebuild instructions in `tools/review/asset-review/vendor/README.md`;
  an earlier snapshot of it is in the first "Init" commit), XCOM web-archive deployment READMEs,
  staging/validation JSON dumps and logs, one-off stage/fix/trial/showcase scripts, superseded kits
  (`pumpkin_lib.py`, `cc_helpers.py`), game C++ code. Details in the folder READMEs.

### Verified
- `gates.py --all` against trick-or-treat (read-only): 184/184 PASS, same as the in-game copy.
- `make_palette.py` / `make_materials.py` into a scratch game: `palette.png` byte-identical and
  `toon.tres` identical to trick-or-treat's.
- Headless Blender 5.1 smoke build in a scratch game: all ten lane kits import; build, AO, export,
  review sheet, `gates.py` PASS and `publish_catalog.py` work end to end. `make_fire.py` writes its
  16 frames. `set_palette_row.py`, `catalog_register.py`, `sync_engine_addon.ps1` tested in scratch.
- Not run yet: Godot itself (shaders, presets and the GDScript previewer are untested in-engine).
