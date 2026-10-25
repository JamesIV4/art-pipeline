# Flame, smoke and swirl flipbooks (particle art designed in Blender)

## What it is

Particle sprites are modelled as flat geometry with node-built emission + transparency shaders and
rendered headless in Blender (EEVEE, transparent film, orthographic camera), then packed into
128 px sprites and 4x4 flipbook atlases that the engine plays on billboard particles. Set:
`sparkle` (four-point twinkle), `glow` (soft round light), `ring` (thin band dotted with stars),
and 16-frame flipbooks `smoke_4x4`, `flame_4x4`, `swirl_4x4`, plus tiny 3D confetti meshes (star,
heart, candy corn, curl) exported as JSON triangle lists with vertex colours.

## Why

Hand-drawn sprite sheets were not available and generic noise textures looked like a different
game. Designing the effects as code keeps them in the toy-like style, reproducible and tweakable
(colours, timing, shapes), with no external assets.

## How

tools/vfx/make_vfx.py (Blender) and tools/vfx/make_fire.py (numpy), then tools/vfx/assemble_vfx.py (Pillow):

- Scene: 256 px, film transparent, view transform Standard, EEVEE 32 TAA samples, ortho scale
  2.2-2.4, camera on +Z looking down.
- Material: Emission + Transparent mixed by an alpha socket; colour and alpha come from small
  builders (radial spherical-gradient ramps, object-space Y ramps, UV ramps).
- Flame: since 2026-10-25 `flame_4x4` comes from tools/vfx/make_fire.py (numpy + Pillow, no
  Blender), a procedural heat-field flame; see procedural-fire-flipbook.md. make_vfx.py no longer
  renders it. The retired Blender version was a 40-point teardrop outline with a travelling-wave
  tip and an inner yellow core layer; it read as a cartoon raindrop, not fire.
- Smoke (16 frames): 7 seeded faceted ico blobs that grow, drift up and dissolve, lit from above by
  mapping normal.y into a lilac-to-white ramp; fade after 35% of life.
- Swirl (16 frames): a 90-segment spiral ribbon that unwinds (radius grows with t), alpha ramps
  along its UV so it fades from the tail, plus 3 twinkle stars that appear in sequence.
- Assemble: single sprites downsampled to 128 px; flipbooks pasted into 512x512 4x4 grids of 128 px
  cells; fully transparent pixels set to white so filtering never pulls dark fringes. Art stays
  white where the engine tints it.
- Engine: billboard-particles material, `particles_anim_h/v_frames = 4`, loop off, anim speed 1 so
  one flipbook plays over one particle life; additive for flame, swirl, sparkle, glow, ring; mix
  for smoke. Pools of one-shot CPUParticles3D (sparkle 14, smoke 10, flame 24) are reused.
  Particle textures load straight from PNG at runtime (no import step).

Related ribbon effect: the fireball trail is a camera-facing ribbon through recent positions,
coloured in-shader (game/shaders/fire_trail.gdshader): fbm turbulence streaming back along the
trail, width `mix(0.9, 0.2, along^0.7)`, heat ramp from white-yellow core through orange to deep
red, the tail tearing into wisps; flipbook flame particles lick around the hot core.

Effects scale with the reward (feedback proportional to success): plain candy gets a glow pop and
twinkles, chocolate a magic swirl, lollipops a star ring and confetti, golden a sparkle fountain.

## Gotchas

- Blender engine enum names changed (BLENDER_EEVEE vs BLENDER_EEVEE_NEXT); try both.
- Spherical gradient is 1 at the centre: mirror ramp stops (`1 - pos`).
- Leave colour white in the art when the game tints it; baked colour plus tint double-saturates.
- Blender winds counter-clockwise; Godot front faces are clockwise: swap two vertices per triangle
  when importing the JSON particle meshes, and convert Z-up to Y-up (x, z, -y).
- Modelled flames on assets are not flipbooks: the fire wand's flame crystal read lemon-yellow with
  glow_jack and peach-white with glow_lantern_red; it read as fire only with the dim
  glow_jack_shell cell on the licks and the hot cells in the core (see glow-cells-and-bloom.md).

## Source

trick-or-treat: art/tools/make_vfx.py, art/tools/assemble_vfx.py, native/src/play/vfx.cpp,
native/src/play/combat.cpp, game/shaders/fire_trail.gdshader, README "Effects",
play_props/batch03/CHECKPOINT.md (fire_wand).
