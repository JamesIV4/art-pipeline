# Rendering settings presets (Godot 4.7, Forward+)

Origin: `S:\Repos\trick-or-treat\game\scenes\main.tscn`, `S:\Repos\trick-or-treat\game\project.godot`,
`S:\Repos\trick-or-treat\game\scripts\post_fx.gd`, `S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\battlescape_view.gd`,
`...\battlescape-dev\oxp\debug\shipped_render_defaults.gd`, `...\battlescape-dev\oxp\debug\render_panel.gd`,
`...\battlescape-dev\project.godot` (imported 2026-10-25). This page collects their values; nothing here is new tuning.

History: the user tuned the XCOM battlescape live with its render panel (Ctrl+Alt+D) and shipped the preset
"Latest 2" (2026-10-07, quality raised 2026-10-16). trick-or-treat then ported "all the post processing effects and
main settings": it copied the SSAO / SSIL / glow / tonemap / AA / shadow-quality values verbatim, dropped film grain,
and replaced XCOM's daylight (sun + blue-grey ambient, black void) with its own moonlit night (sky shader, blue
ambient, SSR, fog, volumetric fog, toy-lens DOF).

Files: `env_night_storybook.tres` + `camera_toy_lens.tres` + `rig_night_storybook.tscn` (trick-or-treat),
`env_xcom_latest2.tres` + `rig_xcom_day.tscn` (XCOM), `project_rendering.cfg` (project.godot snippet),
`reference/xcom_shipped_render_defaults.gd` (the full XCOM preset record, every render-panel key).

## Project settings (project.godot)

| Setting | trick-or-treat | XCOM battlescape (shipped) | Notes |
|---|---|---|---|
| Renderer | Forward+ | Forward+ (Vulkan in LibGodot; D3D12 in viewer/labs) | contact_fx.gd, SSIL, SDFGI need Forward+ |
| `anti_aliasing/quality/msaa_3d` | 2 (4x) | 2 (4x; 8x before 2026-10-16) | TAA, FXAA, SMAA off in both |
| Directional shadow atlas | 8192 | 8192 | |
| Soft shadow filter | 5 (Ultra) | 5 (Ultra) | |
| SSAO quality / half size | 4 (Ultra) / false | Ultra / full res (set at runtime) | post_fx.gd forces Ultra + full res via RenderingServer |
| SSAO / SSIL fadeout | defaults (50 / 300 m) | 2000 / 4000 m | XCOM camera is orthographic, 250-359 m back |
| Global shader buffer | default | 524288 | XCOM per-tile globals |
| Cluster max elements | default | 4096 | many small lights |
| Clear colour | (0.04, 0.06, 0.15) | black | |
| `[shader_globals]` | cutout_from, cutout_to (vec3), cutout_radius (float) | n/a | required by toon.gdshader |
| Mesh LOD threshold | default 1.0 | default 1.0 | `review/controls/lod_control.gd` sets 0 for a full-detail comparison |

## Environment

| Property | trick-or-treat night | XCOM "Latest 2" | XCOM scene base (viewer calibration) |
|---|---|---|---|
| Background | Sky (night_sky.gdshader, radiance 128) | Colour black | Colour black |
| Ambient source / colour / energy | Colour (0.42, 0.48, 0.85) x 0.55 | Colour #4f6995 x 2.22 (sky contrib 0.26) | Colour (0.70, 0.78, 0.91) x 0.65 |
| Reflected light | Sky | Sky (neutral grey ProceduralSky, reflections only) | Sky (same) |
| Tonemap / exposure / white | Filmic / 1.0 / 1.0 | Filmic / 1.0 / 1.0 | Filmic |
| SSR | on: 48 steps, fade in 0.4, out 3.0, tolerance 0.3 | off (65 steps, tol 0.5 when on) | off |
| SSAO radius / intensity / power | 1.61 / 16.0 / 1.5 | 1.61 / 16.0 / 1.5 | 0.75 / 1.15 / default |
| SSAO detail / horizon / sharpness | 0.42 / 0.27 / 0.68 | 0.42 / 0.27 / 0.68 | defaults |
| SSAO light affect / AO channel | 0.35 / 0.06 | 0.35 / 0.06 | defaults |
| SSIL radius / intensity / sharpness / normal rej. | 10.87 / 1.6 / 0.98 / 1.0 | 10.87 / 1.6 / 0.98 / 1.0 | off |
| Glow levels 1-7 | 0, 0.8, 0.4, 0.1, 0, 0, 0 | same | off |
| Glow intensity / strength / bloom / threshold | 3.41 / 1.12 / 0.02 / 1.0 | same | |
| Glow blend | Soft light (2) | Soft light (2) | |
| Fog | on: colour (0.15, 0.19, 0.38) x 0.9, density 0.004, sky affect 0 | off | off |
| Volumetric fog | on: density 0.011, albedo (0.62, 0.68, 0.95), emission (0.02, 0.025, 0.06), anisotropy 0.35, length 80, ambient inject 0.35, sky affect 0 | off | off |
| SDFGI / VoxelGI / reflection probe | off | off (panel options) | off |
| Camera attributes | toy lens DOF: far 32 m (+22), near 4 m (+2.5), amount 0.06 | none | none |

## Key light

| | trick-or-treat Moon | XCOM sun "Latest 2" | XCOM scene base |
|---|---|---|---|
| Colour / energy | (0.6, 0.7, 1.0) x 0.62 | #897f6a x 3.44 (indirect 1.06, specular 1.0) | (1.0, 0.94, 0.83) x 1.65 |
| Direction | 52 deg elevation, from high and slightly behind the camera (runtime, per seed) | elevation 45.5, azimuth 149.5 (rotation -45.5, 149.5, 0) | rotation (-51, -28, 0) |
| Shadows | PSSM 4, max 70 m, opacity 0.78, bias 0.05, blur 1.5 | PSSM 4, max 515 m, opacity 1.0, bias 0.195, normal bias 1.8, blur 0.17 | on, defaults |
| Volumetric fog energy | 0.6 | n/a | n/a |
| Day / night | night only | sun energy lerps from the day value to 0.14 and ambient energy to 0.15 as OpenXcom's global shade goes 0..15 | |

Other XCOM built-in preset: "legacy battlescape" = scene base with sun white x 1.3 at elevation 55 / azimuth 30,
ambient (0.62, 0.64, 0.70) x 0.9, SSAO off, reflections from background, no reflection sky.

## Post (post_fx.gd + contact_fx.gd)

| | trick-or-treat | XCOM "Latest 2" |
|---|---|---|
| Sharpen | 0.27 | 0.27 |
| Vignette strength / radius / softness / colour | 0.5 / 1.0 / 0.45 / black | same |
| Film grain / size | none | 0.015 / 1.6 px, animated at 24 fps (`post_fx_grain.gdshader`) |
| Anti-banding dither | +-0.5 of an 8-bit step (IGN) | same, frame-offset |
| Depth AO (compositor) | on, radius 0.46 m, intensity 0.77, full res | same |
| Contact shadows (compositor) | off | off (length 0.05, thickness 0.16, intensity 0.66 when on) |

Recreate a rig in code instead of instancing the .tscn: set the Environment, the light values above, then add a Node
with `post_fx.gd` whose `environment_path` / `sun_path` point at them.
