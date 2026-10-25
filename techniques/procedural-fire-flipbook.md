# Procedural fire flipbook (heat field, not a shape)

## What it is

A 16-frame 4x4 flame flipbook generated in plain numpy + Pillow (tools/vfx/make_fire.py) instead
of modelling a flame shape in Blender. The flame is a scalar *heat field* per pixel; colour and
alpha are both derived from heat, and the result is drawn additively in game. Frames play once
over a particle's life: swell up, flicker as noise rises through it, then cool and break apart
into wisps.

## Why

The first flame was a Blender teardrop with a wavy tip (tools/vfx/make_vfx.py, retired
2026-10-25). Any hard, closed silhouette reads as a raindrop or a cartoon icon, not fire. Real
flame has no outline: it is a soft hot body whose edges and top are torn away by turbulence.

## How

Per frame `t = f / 15` (256 px, values in -1..1, up is +Y):

1. Envelope: a soft gaussian column, wide at the base and narrowing upward,
   `width = (0.36 + 0.12 * grow) * (1 - yn) ** 0.75 + 0.04`,
   `envelope = exp(-((X - sway) / width) ** 2 * 1.6)`, with a smoothstep-rounded base and a
   smoothstep fade near the top (no hard bottom or top edge).
2. Warp: coarse fractal value noise (3 octaves) sways the column sideways, more toward the top:
   `sway = (warp - 0.5) * (0.12 + 0.55 * yn ** 1.3)`.
3. Erode: a finer fbm (4 octaves) bites into the heat, more toward the top and more with age:
   `bite = (0.45 + 0.5 * cool) * (0.35 + 0.9 * yn) * (1 - erode)`;
   `heat = clip(envelope * (1 - 0.4 * cool) - bite)`, scaled by a grow-in factor.
4. Ramp: heat through a fire ramp (deep red 0.0, red-orange 0.18, orange 0.38, yellow-orange 0.6,
   pale yellow 0.82, near-white 1.0). Alpha = `smoothstep(0.02, 0.42, heat) * (1 - 0.35 * cool)`.
5. Life envelope: `grow = smoothstep(0, 0.3, t)`, `cool = smoothstep(0.45, 1, t)`.
6. Motion: generate the noise fields once, 4x taller than the frame, and slide a window down the
   tall field each frame (`rise = int(t * N * 1.6)`; warp moves at half speed). Noise appears to
   rise through the flame.
7. Pack with tools/vfx/assemble_vfx.py (128 px cells, transparent pixels set to white) and draw
   additively: the dim red fringe just warms whatever is behind it.

## Gotchas

- A hard teardrop silhouette reads as a raindrop. Let heat and erosion make the outline.
- Do not animate noise with `np.roll` on a tiling field: the wrap seam crawls through the flame.
  Slide a window down a tall, non-tiling noise field instead.
- Normalise fbm by percentiles (1st/99th) so octave sums use the full 0..1 range.
- Alpha must follow heat, not the envelope, or the eroded tongues leave grey ghosts.
- Additive blending: keep the ramp's low end dark red rather than transparent black, so edges
  warm the background instead of cutting a hole.
- Seeded RNG (`default_rng(23)`) keeps rebuilds reproducible; change the seed for variants.

## Source

trick-or-treat: art/tools/make_fire.py (2026-10-25), art/tools/make_vfx.py docstring, coordinator
note 2026-10-25. Port: tools/vfx/make_fire.py.
