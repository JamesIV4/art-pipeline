# engine/godot: the Godot 4.7 side of the art pipeline

Shaders, post-processing, lighting / environment presets and review-capture tools shared by every game that uses
this pipeline. Ported 2026-10-25 from trick-or-treat (primary: where it adapted something from XCOM, its version is
the one here) and from OpenXcom-Extended-3D (XCOM originals and XCOM-only extras). Every file carries an
`Origin:` header (absolute source path + what changed); `.tres` / `.tscn` / `.cfg` hold it as `;` comment lines,
which the Godot editor drops when it re-saves the file, so the table below is the durable record.

Target: Godot 4.7, Forward+ (the compositor depth AO, SSIL and the toon shader's tuning assume it), Windows tools.

## Install in a game

1. Copy (or junction: `mklink /J game\addons\art_pipeline S:\Repos\art-pipeline\engine\godot`) this folder to
   `res://addons/art_pipeline/`. There is no plugin.cfg; nothing needs enabling. The `.ps1` / `.md` files inside are
   harmless to Godot. `.tres` / `.tscn` files reference `res://addons/art_pipeline/...`; shaders and GDScript
   reference each other relatively (`#include "fx_common.gdshaderinc"`, `preload("contact_fx.gd")`), so only the
   resources need editing if you install elsewhere.
2. Paste `presets/project_rendering.cfg` into `project.godot` (at least the `[shader_globals]` block: toon.gdshader
   does not compile without `cutout_from`, `cutout_to`, `cutout_radius`).
3. Instance `presets/rig_night_storybook.tscn` (or `rig_xcom_day.tscn`) in the main scene, or copy its values; the
   PostFX node needs a sibling `WorldEnvironment` and a light at `sun_path` (default `../Moon`).
4. Point the material generator at the addon shader: in `<game>/art/pipeline.json` set
   `settings.toon_shader_res = "res://addons/art_pipeline/shaders/surface/toon.gdshader"` (the default
   `res://shaders/toon.gdshader` is trick-or-treat's own copy). Keep `palette_res`, `palette_emit_res`,
   `albedo_array_res`, `normal_array_res` pointing at the game's generated textures.

## Files

Paths relative to this folder. ToT = `S:\Repos\trick-or-treat`, OXP = `S:\Repos\OpenXcom-Extended-3D`.

| File | What | Origin |
|---|---|---|
| `shaders/surface/toon.gdshader` | Textured toon surface: palette tint (UV2) x painted texture-array detail (UV), normal arrays, vertex AO, two-band light ramp with blue shadow fill, palette glow + flicker, rim / flash / hit glow, wind sway, dithered camera-to-player occluder cutout | ToT `game\shaders\toon.gdshader` |
| `shaders/surface/grass.gdshader` | MultiMesh lawn blades: root-tip gradient x instance colour, wind, backlight | ToT `game\shaders\grass.gdshader` |
| `shaders/surface/scatter_vegetation.gdshader` | Alpha-scissor foliage cards (atlas cells, per-instance hue/value, bent normals, translucency, wind gusts, trample, burn). `use_visibility` added (default off) for the XCOM tile-visibility block | OXP `xcom-3d-godot\x-com--ufo-defense-3d\assets\shaders\scatter_vegetation.gdshader` |
| `shaders/surface/floor_grid.gdshader` | Neutral review floor: 2 m tiles, 0.5 m sub-grid, one highlighted tile | OXP `xcom-3d-godot\unit-lab\shaders\floor_grid.gdshader` |
| `shaders/sky/night_sky.gdshader` | Storybook night sky: navy-violet gradient, twinkling stars, cratered moon + halo, drifting painterly clouds with silver lining, `lightning` flash | ToT `game\shaders\sky.gdshader` (renamed) |
| `shaders/pickup/candy.gdshader` | Spinning, bobbing collectible (INSTANCE_CUSTOM.r phase), vivid palette colour, self glow, coloured rim | ToT `game\shaders\candy.gdshader` |
| `shaders/pickup/candy_outline.gdshader` | `next_pass` glow outline: inflated back-face shell, same spin/bob, pulsing tint | ToT `game\shaders\candy_outline.gdshader` |
| `shaders/pickup/candy_beam.gdshader` | Additive soft light column under a pickup, Y-axis billboard, depth-soft base | ToT `game\shaders\candy_beam.gdshader` |
| `shaders/pickup/halo.gdshader` | Additive camera-facing glow disc behind a pickup | ToT `game\shaders\halo.gdshader` |
| `shaders/vfx/magic_trail.gdshader` | Guide trail: three swirling camera-facing smoke sheets along a centreline mesh, depth-soft | ToT `game\shaders\magic_trail.gdshader` |
| `shaders/vfx/fire_trail.gdshader` | Additive flame ribbon (UV.x along, UV.y across), fbm licks, heat ramp | ToT `game\shaders\fire_trail.gdshader` |
| `shaders/vfx/fx_common.gdshaderinc` | Shared VFX helpers: soft particles, virtual floor fade, flipbook sampling (blend / bias / loop), smoke light-map lighting, billboarding | OXP `xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_common.gdshaderinc` |
| `shaders/vfx/fx_glow.gdshader` | Additive HDR glow sprite for GPUParticles3D (computed shape, no texture) | OXP `...\oxp\fx\shaders\fx_glow.gdshader` |
| `shaders/vfx/fx_spark.gdshader` | Velocity-stretched spark streak | OXP `...\fx_spark.gdshader` |
| `shaders/vfx/fx_ribbon.gdshader` | Streak between two world points (tracers, bolts, exhaust), round caps or comet taper | OXP `...\fx_ribbon.gdshader` |
| `shaders/vfx/fx_smoke.gdshader` | Lit smoke / dust flipbook sprite (Mantaflow light-map flipbook), erosion wisps | OXP `...\fx_smoke.gdshader` |
| `shaders/vfx/fx_fireball.gdshader` | Fireball MultiMesh: emission + light-map flipbooks driven by `age` | OXP `...\fx_fireball.gdshader` |
| `shaders/vfx/fx_shock.gdshader` | Expanding screen-distortion shock ring with a hot rim | OXP `...\fx_shock.gdshader` |
| `shaders/vfx/fx_haze.gdshader` | Heat-haze distortion quads | OXP `...\fx_haze.gdshader` |
| `shaders/ui/sharp_shimmerless.gdshader` | canvas_item: shimmer-free sharp scaling of pixel art (CC0, Woohyun Kang); host sets `output_size` | OXP `...\oxp\hud\sharp_shimmerless.gdshader` |
| `post_fx/post_fx.gd` | Post stack host: adds the compositor depth AO, the sharpen / vignette (optionally grain) canvas pass, forces SSAO Ultra full-res, feeds the sun direction | ToT `game\scripts\post_fx.gd` (constants -> exports, NodePaths, optional grain) |
| `post_fx/post_fx.gdshader` | Sharpen + vignette + anti-banding dither | ToT `game\shaders\post_fx.gdshader` (from OXP `...\oxp\debug\post_fx.gdshader`, grain removed) |
| `post_fx/post_fx_grain.gdshader` | The XCOM original with pcg3d film grain | OXP `xcom-3d-godot\battlescape-dev\oxp\debug\post_fx.gdshader` (renamed) |
| `post_fx/contact_fx.gd` | CompositorEffect: depth-only small-radius AO + optional screen-space contact shadows (two compute passes) | ToT `game\scripts\contact_fx.gd` (= OXP `...\battlescape-dev\oxp\contact_fx.gd`) |
| `materials/toon.tres` | Toon material with trick-or-treat's 32-layer `layer_scale/strength/normal` arrays | ToT `game\materials\toon.tres` (normally generated by the material tool) |
| `materials/candy.tres`, `grass.tres`, `halo.tres`, `magic_trail.tres` | Ready materials (candy has the outline `next_pass`; halo / trail render priorities 1 / 2) | ToT `game\materials\*.tres` |
| `presets/env_night_storybook.tres` | Night Environment + sky (SSR, SSAO, SSIL, glow, fog, volumetric fog) | ToT `game\scenes\main.tscn` (NightEnv) |
| `presets/camera_toy_lens.tres` | Near + far DOF "toy lens" | ToT `main.tscn` (ToyLens) |
| `presets/rig_night_storybook.tscn` | WorldEnvironment + Moon + PostFX | ToT `main.tscn` + moon direction from `native\src\play\festival_game.cpp` |
| `presets/env_xcom_latest2.tres` | XCOM shipped daylight Environment (black void, neutral reflection sky) | OXP `...\oxp\battlescape_view.gd` + `...\oxp\debug\shipped_render_defaults.gd` |
| `presets/rig_xcom_day.tscn` | WorldEnvironment + Sun + PostFX (with grain) at "Latest 2" | same |
| `presets/project_rendering.cfg` | project.godot snippet: AA, shadows, SSAO quality, shader globals (+ XCOM alternatives) | ToT `game\project.godot`, OXP `...\battlescape-dev\project.godot` |
| `presets/project_settings_rendering.md` | Every environment / light / post / project value of both games side by side | (compiled) |
| `presets/reference/xcom_shipped_render_defaults.gd` | The complete XCOM "Latest 2" render-panel record (reference only) | OXP `...\oxp\debug\shipped_render_defaults.gd` |
| `review/asset_preview.gd` + `.tscn` | Four-view review sheet of one asset (night + studio), 1600x900 PNG | GDScript port of ToT C++ preview mode (`native\src\play\festival_game.cpp`) |
| `review/asset_preview.ps1` | Catalog id -> import -> preview sheet, under the Godot lock | ToT `tools\asset_preview.ps1` |
| `review/review.ps1` | Seed x view captures through the game's own `--capture` mode; optional native build | ToT `tools\review.ps1` |
| `review/godot_lock.ps1` | One Godot per project at a time (lock file `<game root>\.godot_lock`) | ToT `tools\godot_lock.ps1` |
| `review/art_pipeline_paths.ps1` | Game-root / pipeline.json path resolution for the scripts (twin of `tools/pipeline_paths.py`) | art-pipeline original |
| `review/CaptureGodotReview.ps1` | Sealed, import-verified per-asset captures against a review viewer's stdout contract | OXP `art\tools\CaptureGodotReview.ps1` |
| `review/controls/*.gd` | Single-variable render diagnostics (`--script`): shadows off, SSAO off, LOD full detail, shadow distance 24 m, shadow distance fitted to the scene | OXP `art\tools\{shadow,ssao,lod,shadow_distance,shadow_scene_aware_control_v2}*.gd` |

## What the toon shader expects (palette / material tools contract)

Mesh attributes (written by the Blender kit and the C++ mesh builder alike, see `techniques/palette-tint-uv.md`,
`painted-material-arrays.md`, `vertex-ao-bake.md`):

- `UV` (TEXCOORD_0, "UVMap"): material tiling coordinates in metres.
- `UV2` (TEXCOORD_1, "Tint"): `x = material layer index + palette cell u` (the integer part is the layer, the
  fraction the cell u), `y = palette cell v`. UV2 = (0, 0) means "no UV2": the shader then uses UV as the palette
  cell (flat palette path, layer 0).
- `COLOR_0`: `.r` = baked ambient occlusion (1 = open). Tangents for the normal arrays.

Uniforms (material, set by the generated `toon.tres`):

| Uniform | Type | Meaning |
|---|---|---|
| `palette` | sampler2D, nearest | `palette.png`, 16x16 cells of 16 px (cell centre UVs) |
| `palette_emit` | sampler2D, nearest | `palette_emit.png`: glow RGB, alpha = flicker 0..1 |
| `albedo_array` | sampler2DArray, linear mip aniso, repeat | painted detail per layer, neutral grey = 0.5 (shader uses `det * 2`) |
| `normal_array` | sampler2DArray (hint_normal) | normal maps per layer (used for layer > 0 only) |
| `layer_scale[32]` | float | tiling size in metres per layer (UV / scale) |
| `layer_strength[32]` | float | 0 = flat palette colour, 1 = full detail modulation |
| `layer_normal[32]` | float | normal strength (x 1.4 = NORMAL_MAP_DEPTH) |
| `emit_strength` | 2.6 | palette glow multiplier |
| `ramp_soft` | 0.2 | half-width of the N.L light ramp |
| `shadow_tint` | (0.55, 0.65, 1.0) | colour of the unlit side's faint fill (x 0.12) |
| `ao_strength` | 0.85 | vertex AO mix |
| `cast_shadow_tint` / `cast_shadow_fill` | (0.42, 0.58, 1.0) / 0.32 | blue fill inside directional cast shadows |

Instance uniforms (per GeometryInstance3D, defaults in brackets): `rim_strength` [0], `rim_color`
[(0.62, 0.76, 1.0)], `glow_boost` [1], `flash` [0], `hit_flash` [black], `wind` [0, sway grows with height^2],
`keep_visible` [0; 1 = never cut out]. Globals (project.godot `[shader_globals]`): `cutout_from` (camera),
`cutout_to` (player feet), `cutout_radius` (0 = off); the game updates them every frame.

Material arrays have 32 slots; the material tool writes the values per layer. `materials/toon.tres` holds
trick-or-treat's values and texture paths as an example only.

## What the adopting game must provide or adjust

- `res://assets/palette/palette.png`, `palette_emit.png`, `res://assets/materials/albedo_array.png`,
  `normal_array.png` (imported as Texture2DArray): referenced by `materials/toon.tres` and `candy.tres`.
  Generate them with the pipeline (paths: `pipeline.json` `palette_out`, `materials_out`).
- `[shader_globals]` cutout_* (above) and code that sets them, or leave `cutout_radius` 0.
- Sky: the game sets `moon_dir` (and `cloud_cover`, `lightning`) on the sky ShaderMaterial; trick-or-treat does it per
  seed from C++. Point the key light to match (see the rig).
- Candy shaders: INSTANCE_CUSTOM.r = phase (+ .gba = outline tint) per MultiMesh instance, MultiMesh instance colour
  for halo / beam; `outline_tint` / `beam_tint` instance uniforms for loose pieces.
- Magic trail: a centreline mesh in the encoding described in the shader header (VERTEX centre, TANGENT path
  direction, NORMAL perpendicular, UV.x metres along, UV.y side, UV2.x sheet 0..2, UV2.y fraction along).
- `fx_*` shaders: the host sets `sun_dir_view`, `sun_radiance`, `ambient_radiance` and `fx_time` on each material every
  frame (XCOM's `fx_director.gd`, not ported); `fx_smoke` / `fx_fireball` need Mantaflow light-map / emission
  flipbooks (8x8), `fx_haze` / `fx_smoke` a tiling `noise_tex`. `void_floor_y` is XCOM's floor for sprites over
  never-drawn areas; leave 0 or set the ground height.
- `scatter_vegetation`: an atlas (`atlas_grid` cells), INSTANCE_CUSTOM (x cell, y colour variation, z sway phase,
  w neighbourhood density), optional `actors[48]` / `actor_count` for trample.
- Review: `review.ps1` needs the game's main scene to implement `--seed= --capture= --capture-frames= --capture-view=`
  (trick-or-treat: C++ `FestivalGame::parse_cmdline`); `asset_preview.ps1 -Scene main` needs `--preview=`;
  `CaptureGodotReview.ps1` needs an XCOM-style review viewer (see its header). `asset_preview.ps1` (default
  `-Scene addon`) needs nothing from the game beyond the catalog and the exported glTF.

## Remaining game-specific assumptions

- Hard-wired look values: the night rig's moon / fog / ambient colours, the toon shader's blue shadow fill, the
  preview's warm porch light and moon colour (asset_preview.gd), `emit_strength` 2.6. Tune per game.
- `toon.gdshader` cutout assumes a third-person camera and a player position (`cutout_to.y - 0.25` floor rule).
- `post_fx.gd` assumes Forward+ for the compositor pass (it silently skips it otherwise) and a HUD on canvas layer 1+.
- `asset_preview.gd` lifts assets whose bounds go below y = 0 (floating props) to 0.25 m, as trick-or-treat did.
- `review.ps1 -BuildNative` defaults: `<root>\native`, `C:\msys64\mingw64\bin`, trick-or-treat's scons arguments.
- `CaptureGodotReview.ps1` keeps XCOM defaults (`-Asset terrain/CULTIVAT/014`, `-Catalog assets/catalog.json`,
  corner ids) and its stdout contract; `review/controls` print `TACTICAL_*` lines for it. Each control asserts the
  scene has exactly one DirectionalLight3D (and one WorldEnvironment where relevant).
- `presets/reference/xcom_shipped_render_defaults.gd` keys (`ul_*`, `vis_*`, `nsfog_*`, `fx_*`, `ls_*`) belong to XCOM
  systems that are not here.

## Deliberately left out

- trick-or-treat C++ (GDExtension) code: the CPU particle VFX library (`native\src\play\vfx.cpp`: sparkles, smoke
  poofs, rings, confetti), StormSky clouds / lightning, the generator, camera, review bot and `--capture-view` modes.
  Only the preview mode was small and generic enough to translate (review/asset_preview.gd).
- trick-or-treat `hud.gd`, `audio.gd`, `boot.gd`: gameplay / UI / input, not art.
- XCOM `oxp/debug/render_panel.gd` (58 KB live render-tuning panel, Ctrl+Alt+D) and the unit-lab copy
  (`unit-lab/scripts/render_lab/`): valuable but bound to OpenXcom's feed, terrain visibility, unit lights and HUD
  input routing. Its preset keys are documented in `presets/project_settings_rendering.md`; port it as its own
  task if a game wants live tuning.
- XCOM ground / water / rock / terrain shaders (`authored_ground`, `shared_ground`, `natural_shore`,
  `polar_water_opus`, `scatter_rock*`, `layered_terrain*`, `ground_border`, `blast_scar`), sprite billboards, the
  visibility overlay, psi / tile fire / tile smoke / blast scar FX, blood shaders, vehicle band: all depend on
  OpenXcom tile maps, the per-tile visibility texture or unit systems. See `techniques/ground-materials.md`,
  `reflections.md`, `layered-merges.md` for the methods.
- XCOM `fx_director.gd` / `fx_lib.gd` (the FX host that feeds `fx_common` uniforms), `render_model_studio.gd`
  (Blender-vs-Godot studio comparison for skinned units), calibration labs (`labs/renderer_calibration`; see
  `techniques/lighting-calibration.md`), `godot_main_lock.py` (referenced in godot_lock.ps1's header; the PowerShell
  lock replaces it), the v1 `shadow_scene_aware_control.gd` (superseded by v2).
- `.godot` caches, imports, textures, models, audio, binaries, `.uid` files (Godot regenerates them).
