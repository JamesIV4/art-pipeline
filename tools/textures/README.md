# tools/textures: texture, material, PBR, compression and import-policy tools (from XCOM)

Imported 2026-10-25 from `S:/Repos/OpenXcom-Extended-3D` ("XCOM"). Every file starts with an
`Origin:` / `Changed:` comment. `ROOT = Path(__file__).parents[2]` was replaced with
`pipeline_paths.GAME_ROOT`. The XCOM Godot project folder now comes from
`pipeline_paths.path("godot_project")`, so XCOM's `art/pipeline.json` must set
`"godot_project": "xcom-3d-godot/x-com--ufo-defense-3d"` (the default is `game`).

| File | Purpose | Origin (XCOM-relative) | Dependencies | Remaining game-specific assumptions |
|---|---|---|---|---|
| `materials.py` | Procedural seamless PBR library generated inside Blender (albedo/normal/ORM PNGs + Principled material) | `art/tools/materials.py` | bpy, numpy | `PRESETS` are XCOM surfaces; writes `<godot_project>/assets/textures/<key>_{albedo,normal,orm}.png` |
| `derive_pbr_maps.py` | Normal/roughness/ORM from an albedo, using UV-island masks from a glb/gltf (push-pull fill, DoG height, Sobel normal) | `art/tools/derive_pbr_maps.py` | numpy, cv2 | none (paths are CLI args); writes lossless WebP |
| `derive_maps.py` | Image-only variant: tiling albedo + normal(+Y) + ORM from one generated albedo, with seam heal and seam metrics | `art/team/natural_details_opus55/tools/derive_maps.py` | numpy, PIL | none (CLI) |
| `to_webp.py` | PNG to 8-bit lossless WebP with exact pixel verification, never overwrites | `art/team/guns_v2/lib/to_webp.py` | numpy, PIL | none |
| `gltf_opacity.py` | glTF alpha sampling (wrap/filter modes, top-left convention), material alpha, mask visibility | `art/tools/gltf_opacity.py` | stdlib (PIL image in) | none |
| `test_gltf_opacity.py` | unittest for the above | `art/tools/test_gltf_opacity.py` | PIL | none |
| `compress_project_textures.py` | Migrate a Godot project's runtime PNGs to lossless WebP and rewrite .gltf/.tres/.tscn/.import references, keeping UIDs; backups outside the repo; 16-bit PNGs are decoded through Godot | `art/tools/compress_project_textures.py` | PIL (+ Godot for 16-bit) | repo-relative references are recognised only with the `xcom-3d-godot/` prefix; Godot is found via `$GODOT`, PATH or `C:/GameDev/Godot*/*console.exe` (not `pipeline_paths.setting("godot_exe")`); backup dir `%LOCALAPPDATA%/Xcom3D/texture-backups`; takes `tools/review/godot_main_lock.py` |
| `test_compress_project_textures.py` | unittest (alpha pixels, references, seals, backups) | `art/tools/test_compress_project_textures.py` | PIL | run with a game root that does **not** contain `%TEMP%` (e.g. `ART_GAME_ROOT=S:\Repos\OpenXcom-Extended-3D`), because backups inside the game root are refused |
| `deduplicate_project_textures.py` | Share byte-identical textures with identical import settings under `assets/textures/shared/<hash>/`; relinks references and Godot's import cache | `art/tools/deduplicate_project_textures.py` | stdlib | `xcom-3d-godot/` prefix for repo-relative refs; `assets/texture_aliases.json` |
| `test_deduplicate_project_textures.py` | unittest | `art/tools/test_deduplicate_project_textures.py` | stdlib | same `%TEMP%` note as above |
| `runtime_texture_save.py` | Blender-side finaliser: run compress + deduplicate after an export, relink in-memory images | `art/tools/runtime_texture_save.py` | bpy | env var `XCOM_TEXTURE_PYTHON` (host Python with Pillow) |
| `texture_import_policy.py` | Enforce/check the lossless texture `.import` policy (mipmaps, normal-map detection, no VRAM compression) | `art/tools/texture_import_policy.py` | stdlib | `<godot_project>/assets` |
| `scene_import_policy.py` | Enforce/check glTF scene import params (`generate_lods=false` for tile-cut terrain, shadow meshes on) | `art/tools/scene_import_policy.py` | stdlib | `FAMILIES` (XBASE1, XBASE2, U_EXT02, U_BITS, UFO1) and `assets/models/terrain/<family>` layout are XCOM's |
| `fetch_cc0.py` | Download ambientCG / Poly Haven CC0 PBR sets with provenance.json and index.json | `art/tools/fetch_cc0.py` | stdlib (network) | library at `<game>/art/source/cc0_library`; User-Agent names OpenXcom-3D |
| `texture-requirements.txt` | `Pillow>=12.2,<13` | `art/tools/texture-requirements.txt` | - | - |

Run the tests: `python -m unittest discover -s tools/textures -p "test_*.py"` (14 tests, pass with
`ART_GAME_ROOT` set to the XCOM repo). Not taken: `verify_texture_conversion.gd` (Godot side, owned by
the engine port), the `*_trials.py` / `stage_*` / `fix_*` texture one-offs, and `copy_human_pbr_variant.py`
and `texture_human_hands.py` (specific to the human unit graft).
