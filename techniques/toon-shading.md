# Toon shading (textured low-poly, Godot 4.7)

## What it is

One spatial shader (`engine/godot/shaders/surface/toon.gdshader`) for every static mesh in a game: buildings,
props, ground, foliage, even the C++ procedural meshes. Colour comes from the shared palette (UV2), surface detail
from a painted texture array (UV), occlusion from vertex colour, and the lighting model is a soft two-band toon ramp
whose shadows stay coloured instead of going dark. Companion shaders for pickups (candy + outline shell + halo +
beam), lawn grass and the sky share the same palette.

## Why

- One material means one draw-state for the whole world, global palette edits, and props and procedural geometry
  that always match.
- The painted material (texture-array slice) modulates the palette tint, so one siding texture serves every house
  colour; the art direction is polished textured low-poly, not flat colour.
- A soft two-band diffuse makes shadows read as the blue night ambient and lantern light as orange; moon cast
  shadows stay a soft blue instead of going dark (the shader's own design notes).

## How

Surface (fragment):

- Palette: `layer = floor(UV2.x)`, `cell = (fract(UV2.x), UV2.y)`; UV2 = (0, 0) falls back to `cell = UV` (old flat
  meshes). `tint = texture(palette, cell)` (nearest).
- Detail: `tuv = UV / layer_scale[layer]`; `ALBEDO = tint * mix(1, albedo_array[layer] * 2, layer_strength[layer])`,
  so a texture authored around 50 % grey keeps the palette value on average.
- Normals: layer > 0 only; `NORMAL_MAP_DEPTH = layer_normal[layer] * 1.4`.
- AO: `AO = mix(1, COLOR.r, 0.85)`, `AO_LIGHT_AFFECT = 0.35` (vertex AO also darkens direct light a little).
- Glow: `EMISSION = palette_emit.rgb * 2.6 * flicker * glow_boost`, flicker from the emit alpha:
  `1 - a * (0.3 + 0.3 * sin(9 t + seed) * sin(5.3 t + seed))`, seed = hash of the object origin.
- Extras: rim `pow(1 - N.V, 3) * rim_strength`, `flash` (lilac), `hit_flash`; `ROUGHNESS 0.8`, `SPECULAR 0.3`.

Light (per light):

- `ramp = smoothstep(-0.2, 0.2, N.L)` (ramp_soft 0.2); `lit = ramp * ATTENUATION`.
- Unlit-side fill: `LIGHT_COLOR * (0.55, 0.65, 1.0) * 0.12 * (1 - ramp) * clamp(ATTENUATION + 0.4)`.
- Cast-shadow fill (directional only): `LIGHT_COLOR * (0.42, 0.58, 1.0) * 0.32 * ramp * (1 - ATTENUATION)`.
- `DIFFUSE_LIGHT += (LIGHT_COLOR * lit + fills) / PI`.
- Painterly highlight: Blinn-Phong power 24 x 0.18 x ATTENUATION.

Vertex: optional wind (`wind` instance uniform): sway `~ wind * h^2 * 0.012` in x, `0.008` in z, two sines per object.

Occluder cutout: globals `cutout_from` (camera), `cutout_to` (player feet), `cutout_radius`. Fragments above the
player's feet - 0.25 m, inside a cone around the camera-player segment (radius grows 0.22 m per metre toward the
camera, ends 1.1 m before the player) or within 2.2-3.6 m of the camera, are discarded through a 4x4 Bayer dither.
`keep_visible = 1` exempts monsters.

Lighting it was tuned under (trick-or-treat night): moon (0.6, 0.7, 1.0) x 0.62 at 52 deg elevation from behind the
camera, ambient colour (0.42, 0.48, 0.85) x 0.55, Filmic, glow threshold 1.0 (palette glow x 2.6 blooms, albedo does
not). See `post-processing-stack.md` and `engine/godot/presets/project_settings_rendering.md`.

Pickups: `candy.gdshader` saturates the palette colour 1.4x, emits `vivid * 0.5` plus a coloured rim (0.7), spins
1.7 rad/s and bobs 0.09 m; `candy_outline.gdshader` is its `next_pass`: back faces pushed out 0.03 m along a
normal / radial mix, unshaded, emission x 2.6 pulsing 0.8-1.0. The outline glow pass and the beam are covered in
`outline-glow.md` and `candy-beam-column.md`.

## Gotchas

- The three `[shader_globals]` must exist in project.godot or the shader does not compile (paste
  `engine/godot/presets/project_rendering.cfg`).
- UV2 exactly (0, 0) means "no UV2". A real cell at u = 0, v = 0 on layer 0 would hit the fallback; cell centres
  (0.5 / 16) never do.
- Layer arrays are fixed at 32; a 33rd material layer silently clamps to 31.
- Normal maps only on layer > 0: layer 0 is the flat "no material" layer by convention.
- The blue fills scale with LIGHT_COLOR: under a warm lantern the "blue" fill turns warm-grey, which is intended.
- `AO_LIGHT_AFFECT 0.35` plus SSAO plus the compositor depth AO stack; bake vertex AO softly (see `vertex-ao-bake.md`).
- Workbench / Blender sheets never show the ramp, fills or glow: judge in the engine (asset_preview.ps1).
- Instance uniforms (`wind`, `rim_strength`, ...) are per GeometryInstance3D: on a MultiMeshInstance3D every
  instance shares one value; per-instance variation there goes through INSTANCE_CUSTOM / instance colour.

## Source

- trick-or-treat: `game/shaders/toon.gdshader`, `candy.gdshader`, `candy_outline.gdshader`, `game/materials/toon.tres`,
  `game/project.godot` ([shader_globals]), `game/scenes/main.tscn` (lighting), `native/src/play/festival_game.cpp`
  (moon direction), `native/src/mesh/mesh_builder.h` (UV / UV2 / COLOR encoding).
- Ported: `engine/godot/shaders/surface/toon.gdshader`, `engine/godot/shaders/pickup/*`, `engine/godot/materials/*`.
- Related: `palette-tint-uv.md`, `painted-material-arrays.md`, `vertex-ao-bake.md`, `lowpoly-textured-style.md`.
