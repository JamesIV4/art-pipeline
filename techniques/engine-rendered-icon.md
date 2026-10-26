# Game icon rendered in the engine (difference matte)

## What it is

The game's icon made from one of its own assets rendered by the game's renderer (real textures,
toon shading, emissive glow), cut out with a black/white difference matte, and saved as a transparent
square PNG plus a Windows `.ico`. Tool: `tools/marketing/matte_icon.py`.

## Why

- The in-engine look (painted textures, glow, lighting) is the game's identity; a Blender re-render
  of the same glTF has no materials (the game applies its toon material at runtime).
- Godot's `transparent_bg` did not give alpha with this project's environment and glow, and a
  chroma key loses the soft glow around lit openings. Rendering on black and on white recovers true
  coverage, glow included.

## How

1. Add an icon mode to the game's asset preview (trick-or-treat: `--preview=<res gltf> --icon`):
   hide the HUD and the preview ground, one view, environment background a flat colour (black, or
   white with `--icon-white`), fog off.
2. Framing the user approved: **straight on** to the face (yaw 0), camera a touch **below centre**
   (pitch -0.04 rad), a **long lens** (FOV 14 deg, distance from the bounds so the subject fills the
   frame): it flattens perspective so the shape reads like an illustration. Night lighting (moon +
   warm omni) read richer than the studio key.
3. Render both backgrounds at the same framing, then
   `python matte_icon.py black.png white.png icon.png --box <middle crop> --sizes-sheet sheet.png`.
4. Judge the sizes sheet (1024, 256, 64, 32 px on dark and light). At 32 px only the silhouette and the
   brightest feature (glowing face) survive; that is the test.
5. Install (Godot): `game/icon.png` as `application/config/icon`, a multi-size `icon.ico`
   (16-256 px, Pillow `save(..., sizes=[...])`) as `application/config/windows_native_icon` and as the
   Windows export preset's `application/icon`.

## Gotchas

- Godot's post vignette darkens the white render towards the edges: crop to the middle before
  matting (`--box`), or the vignette becomes a grey rectangle in the alpha.
- The first try (rounded square, purple night gradient, moon, pumpkin on top) was rejected: the user
  wanted **just the pumpkin**, no background, no moon. Offer the bare cut-out first.
- A candle light inside the jack-o'-lantern washed out the whole shell (no shadowing inside a thin
  shell); the emissive face cells were enough.
- Don't run `godot --import` for the new icon while the user's editor has the project open.

## Source

trick-or-treat, 2026-10-26: `native/src/play/festival_game.cpp` (`--icon`, `--icon-white`,
`--icon-light=`, `setup_preview`, `step_preview`), `game/icon.png`, `game/icon.ico`.
