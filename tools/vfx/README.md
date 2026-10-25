# tools/vfx: Mantaflow VFX sims and flipbook atlas packing (from XCOM)

Imported 2026-10-25 from `S:/Repos/OpenXcom-Extended-3D/art/source/vfx/`. Only an `Origin:` / `Changed:`
comment was added. Both scripts already take every path as an argument. `make_vfx.py` /
`assemble_vfx.py` (trick-or-treat's procedural VFX) are a separate port and live beside these.

| File | Purpose | Origin (XCOM-relative) | Dependencies | Remaining game-specific assumptions |
|---|---|---|---|---|
| `fx_sims.py` | Blender Mantaflow sims + EEVEE renders: `fireball`, `smoke`, `fire` (loop), `scorch` (top-down decal source), `jet` (pressurised vent fire). Passes: E = emission over black, R/T/L = smoke lit from right/top/left, alpha with every pass. `blender --background --factory-startup --python fx_sims.py -- <sim> <out_dir> [bake\|render\|all]` | `art/source/vfx/fx_sims.py` | bpy, mathutils | sim table (domain sizes, frame ranges, camera elevation 20-25 deg / 90 for scorch, 512 px) is tuned for XCOM's battlescape camera; env knobs `FX_QUICK`, `FX_QUICK_RES`, `FX_QUICK_FRAMES`, `FX_JET_BURN`, `FX_JET_WIND`, `FX_LOBES`, `FX_DENSITY` |
| `pack_atlases.py` | Pack the 16-bit renders into 8x8 flipbook atlases (2048 px, 256 px cells, lossless WebP): emission atlases (rgb = sqrt(linear light), a = opacity), light-map atlases (r/g/b = lit from right/top/left), scorch decal maps (512). `python pack_atlases.py <renders root> <textures out> [fireball smoke fire scorch dirs]` | `art/source/vfx/pack_atlases.py` | numpy, cv2, PIL | output names `fx_*_8x8.webp` and the encoding expected by XCOM's effect shaders (the shaders are engine side, not ported here) |

No other XCOM VFX generators exist: the other `*atlas*.py` scripts under `art/team/` are foliage/hair/
material atlases, not effects.
