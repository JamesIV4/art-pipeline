# Post-processing stack (Godot 4.7 Forward+)

## What it is

The environment + post chain both games ship: Godot's built-in tonemap / SSAO / SSIL / glow (and, at night, SSR,
fog, volumetric fog, DOF) plus two things Godot 4.7 lacks, added by `engine/godot/post_fx/post_fx.gd`:

1. `contact_fx.gd`, a CompositorEffect after the transparent pass: depth-only small-radius AO (and optional
   screen-space contact shadows; Godot gets those natively in 4.8);
2. `post_fx.gdshader`, a full-screen canvas pass over the 3D view and under the HUD: sharpen, vignette, an
   anti-banding dither, and (XCOM variant `post_fx_grain.gdshader`) film grain.

## Why

- The user tuned the XCOM battlescape live in its render panel and shipped "Latest 2" (2026-10-07, quality raised
  2026-10-16); trick-or-treat adopted it wholesale ("all the post processing effects and main settings preset")
  and only changed the scene's light and atmosphere. Reusing the stack keeps games consistent and skips re-tuning.
- SSAO at radius 1.61 m shades room-scale creases; small gaps (grass blades, props on the ground, window frames)
  need a second, 0.46 m AO that works from the depth buffer only, because grass shading normals point up.
- Glow starts at HDR 1.0 (before Filmic), so in the night scene it is mostly palette glow (x 2.6) and VFX that
  bloom; under XCOM's 3.44 sun, bright lit faces bloom softly too.

## How

Environment (values identical in both games):

- Tonemap Filmic, exposure 1.0, white 1.0.
- SSAO: radius 1.61, intensity 16, power 1.5, detail 0.42, horizon 0.27, sharpness 0.68, light affect 0.35,
  AO channel affect 0.06; quality Ultra at full resolution (`environment/ssao/quality=4`, `half_size=false`, and
  `post_fx.gd` re-applies it through `RenderingServer.environment_set_ssao_quality`).
- SSIL: radius 10.87, intensity 1.6, sharpness 0.98, normal rejection 1.0.
- Glow: levels 1-7 = 0, 0.8, 0.4, 0.1, 0, 0, 0; intensity 3.41, strength 1.12, bloom 0.02, HDR threshold 1.0,
  blend Soft light.
- Project: MSAA 4x (`msaa_3d=2`), no TAA / FXAA / SMAA, directional shadow atlas 8192, soft filter Ultra (5).

Per game:

- trick-or-treat night: sky background (night_sky.gdshader), ambient colour (0.42, 0.48, 0.85) x 0.55, reflections
  from the sky, SSR 48 steps (fade 0.4 / 3.0, tolerance 0.3), fog (0.15, 0.19, 0.38) x 0.9 density 0.004, volumetric
  fog 0.011 (albedo (0.62, 0.68, 0.95), anisotropy 0.35, length 80 m, ambient inject 0.35), toy-lens DOF (far 32 m
  + 22, near 4 m + 2.5, amount 0.06), no grain.
- XCOM day: black background, ambient #4f6995 x 2.22, neutral grey ProceduralSky for reflections only, no SSR / fog,
  grain 0.015 at 1.6 px, SSAO / SSIL fadeout 2000 / 4000 m (orthographic camera 250-359 m away).

Post values (both): sharpen 0.27 (`c += (c - 4-tap blur) * 0.27`), vignette strength 0.5, radius 1.0, softness
0.45, black, aspect-correct (1.0 = the corners); dither +-0.5/255 interleaved gradient noise. Depth AO: radius
0.46 m, intensity 0.77, bias 0.1, full resolution, 6 directions x 4 steps, depth-aware 2x2 / box upsample, applied
as `colour *= (1 - AO)`, skipped where depth = sky / void.

Wiring: instance `engine/godot/presets/rig_night_storybook.tscn` or `rig_xcom_day.tscn`, or add a Node with
`post_fx.gd` next to the WorldEnvironment and set `sun_path`. All values are exports. Layer order: 3D view, post
rect (canvas layer 0), HUD (layer 1+).

## Gotchas

- contact_fx reads the RD camera projection: reversed-Z, y flipped. An earlier `1 - 2d` depth remap mirrored the
  geometry and darkened convex edges instead of creases (fixed 2026-10-07); keep the shader's `view_pos` as is.
- The compositor pass needs Forward+; on Mobile / Compatibility `post_fx.gd` silently skips it.
- Full-resolution SSAO costs about 4x the half-size buffer; it is what keeps AO on small props from washing out.
- SSAO / SSIL fade out at 50 / 300 m by default: a far or orthographic camera must raise the fadeout settings.
- The post rect samples `hint_screen_texture`: anything drawn on the same or a lower canvas layer gets sharpened
  and vignetted. Keep the HUD on a higher layer.
- Old grain (`fract(sin())` hash) banded and crawled; the shipped grain uses a pcg3d integer hash at 24 fps.
- Review captures: drop the camera attributes (DOF) for close-ups; the asset previewer does.

## Source

- trick-or-treat: `game/scripts/post_fx.gd`, `game/scripts/contact_fx.gd`, `game/shaders/post_fx.gdshader`,
  `game/scenes/main.tscn` (NightEnv, ToyLens, Moon), `game/project.godot`.
- XCOM: `xcom-3d-godot/battlescape-dev/oxp/debug/shipped_render_defaults.gd`, `.../oxp/debug/render_panel.gd`,
  `.../oxp/debug/post_fx.gdshader`, `.../oxp/contact_fx.gd`, `.../oxp/battlescape_view.gd`, `.../project.godot`.
- Ported: `engine/godot/post_fx/`, `engine/godot/presets/` (full value tables in `project_settings_rendering.md`).
- Related: `lighting-calibration.md`, `glow-cells-and-bloom.md`, `reflections.md`, `lod-and-render-cost.md`.
