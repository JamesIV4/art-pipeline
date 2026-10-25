# tools/vfx: particle art generators

Two families: trick-or-treat's stylised sprites/flipbooks (Blender EEVEE shapes + numpy fire,
128 px cells, 4x4 atlases, drawn additively by billboard particles) and XCOM's physically simulated
effects (Mantaflow, 8x8 atlases with light maps, for the `fx_*` shaders in
`engine/godot/shaders/vfx/`). See `techniques/flame-flipbooks.md` and
`techniques/procedural-fire-flipbook.md`.

## From trick-or-treat (paths via `tools/pipeline_paths.py`: `vfx_frames`, `vfx_out`)

| File | Purpose | Origin | Dependencies | Remaining game-specific assumptions |
|---|---|---|---|---|
| `make_vfx.py` | Blender: `sparkle`, `glow`, `ring` sprites, `smoke_4x4` and `swirl_4x4` flipbooks (16 frames), little 3D particle meshes (star, heart, candy corn, confetti) as JSON triangle lists -> `<vfx_out>/particle_meshes.json`. `blender --background --factory-startup --python make_vfx.py` from the game root | `art/tools/make_vfx.py` | bpy | the effect set, colours (lilac smoke, magic swirl) and the particle mesh shapes are trick-or-treat's; the retired teardrop `flame()` is still in the file but no longer called |
| `make_fire.py` | numpy heat-field flame: soft envelope narrowing upward, coarse-noise sway, fine-noise erosion growing toward the top and with age, fire ramp, alpha from heat; noise slides down a tall field (no seams) -> `flame_00..15.png` | `art/tools/make_fire.py` (2026-10-25) | numpy, PIL | ramp colours and life curve tuned for trick-or-treat's wand/torch flames; seed 23 |
| `assemble_vfx.py` | Packs frames: singles to 128 px, flipbooks to 4x4 atlases of 128 px; transparent pixels set to white (no dark fringes) | `art/tools/assemble_vfx.py` | PIL | `SINGLES` / `SHEETS` name lists at the top are trick-or-treat's set |

## From XCOM (every path is an argument)

| File | Purpose | Origin (XCOM-relative) | Dependencies | Remaining game-specific assumptions |
|---|---|---|---|---|
| `fx_sims.py` | Blender Mantaflow sims + EEVEE renders: `fireball`, `smoke`, `fire` (loop), `scorch` (top-down decal source), `jet` (pressurised vent fire). Passes: E = emission over black, R/T/L = smoke lit from right/top/left, alpha with every pass. `blender --background --factory-startup --python fx_sims.py -- <sim> <out_dir> [bake\|render\|all]` | `art/source/vfx/fx_sims.py` | bpy, mathutils | sim table (domain sizes, frame ranges, camera elevation 20-25 deg / 90 for scorch, 512 px) is tuned for XCOM's battlescape camera; env knobs `FX_QUICK`, `FX_QUICK_RES`, `FX_QUICK_FRAMES`, `FX_JET_BURN`, `FX_JET_WIND`, `FX_LOBES`, `FX_DENSITY` |
| `pack_atlases.py` | Pack the 16-bit renders into 8x8 flipbook atlases (2048 px, 256 px cells, lossless WebP): emission atlases (rgb = sqrt(linear light), a = opacity), light-map atlases (r/g/b = lit from right/top/left), scorch decal maps (512). `python pack_atlases.py <renders root> <textures out> [fireball smoke fire scorch dirs]` | `art/source/vfx/pack_atlases.py` | numpy, cv2, PIL | output names `fx_*_8x8.webp` and the encoding expected by `engine/godot/shaders/vfx/fx_smoke` / `fx_fireball` (their host, XCOM's `fx_director.gd`, is not ported) |

No other XCOM VFX generators exist: the other `*atlas*.py` scripts under `art/team/` are foliage/hair/
material atlases, not effects.
