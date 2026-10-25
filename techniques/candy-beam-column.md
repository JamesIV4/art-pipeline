# Candy beam column (soft light strip under floating pickups)

## What it is

A soft vertical column of light under every floating pickup, in the pickup's colour: a single
quad billboarded about the vertical axis only (yaw-facing, never tilting), additive, widest where
it rises from the ground, fading out just below the pickup, with depth-softened contact so it
never draws a hard line where it meets ground or roofs.

## Why

Platforming research ("readable landings", Iwata Asks: Super Mario 3D Land) says the player needs
to see where a floating object sits in depth. A drop shadow under the hero plus a glow pool under
each floating candy make the jump spot visible. The glow around the candy itself is the outline
(outline-glow.md, the user rejected a halo); the column marks position below the piece without
touching its silhouette.

## How

Shader (trick-or-treat game/shaders/candy_beam.gdshader), material render_priority 1:

- `render_mode blend_add, unshaded, depth_draw_never, cull_disabled, shadows_disabled,
  fog_disabled`; `strength = 0.18`.
- Vertex: build a basis from the camera direction projected flat (`to_cam.y = 0`), keep the
  instance's scale, replace MODELVIEW. A per-position hash gives a shimmer phase.
- Fragment, with `u` across (-1..1) and `h` up (0..1):
  - width `mix(0.42, 0.7, smoothstep(0, 0.85, h))` (never comes to a point)
  - across falloff `exp(-u^2 / w^2 * 2.2) * (1 - u^2)` (zero at the edge, no border)
  - along: `mix(0.45, 1, smoothstep(0, 0.8, h)) * smoothstep(0, 0.3, h) * (1 - smoothstep(0.84,
    1, h))` so it fades in at the bottom and out before reaching the candy
  - flicker `0.85 + 0.15 * sin(t * 2.2 + shimmer + h * 6)`
  - soft contact: reconstruct scene depth from `hint_depth_texture`, `soft = smoothstep(0, 0.35,
    scene_depth - fragment_depth)`, NaN-safe (`gap == gap`)
  - `ALBEDO = instance_colour * beam_tint * across * along * flicker * soft * strength`
- Placement (C++): one MultiMesh of unit quads; instance scale `(w, 1.3, w)` with w = 0.75 for
  everyday tiers and 1.0 for tier 2+, positioned 0.76 m below the candy centre; instance colour =
  the candy's glow colour times a fade (fades with the pickup). Loose candy uses per-node
  MeshInstances with `instance uniform beam_tint`.

## Gotchas

- `mod(TIME, 600)` before using time in sines: long sessions otherwise lose precision.
- Without the depth soft edge the strip shows a hard horizontal line where it cuts the lawn or a
  porch roof.
- Keep the strip from overlapping the pickup (the top fade ends at 84-100% height); additive light
  over the candy washed its colours out.
- Additive on a dark night reads well; on bright daytime scenes the strength must drop.
- Unused capacity instances must be scaled to zero, not just coloured black.

## Source

trick-or-treat: game/shaders/candy_beam.gdshader, native/src/play/candy_field.cpp (setup,
write_instance), native/src/play/loose_candy.cpp, README "Platforming design" (readable landings).
