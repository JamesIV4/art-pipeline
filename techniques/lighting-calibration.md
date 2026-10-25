# Lighting calibration and review lighting

## What it is

How XCOM decided what lighting assets are judged under, how to compare
albedo against 2D source art that has baked shading, and the diagnostic
"neutral" preset used to separate pigment errors from lighting errors.

## Why

Workers kept darkening or brightening albedo per asset to match sprite
brightness, then the global lighting changed and every corrected asset was
wrong (Sectoid v3 albedo x0.647/0.592/0.553 had to be reverted). A measured
lab showed one global setting could match sprite brightness, but the user
preferred brighter modern lighting with darker real shadows. The durable rule
that came out of it: author albedo to the source's hue/saturation, never
compensate per asset for lighting.

## How

1. One shipped lighting profile, shared by every review tool (viewer, unit lab,
   perf lab, battlescape, previewer). XCOM's viewer calibration: filmic,
   exposure 1, sun 1.65 colour (1, .94, .83), ambient 0.65 colour
   (.70, .78, .91), SSAO radius 0.75 intensity 1.15, specular as imported 0.5,
   neutral reflection sky (see `reflections.md`). Copy the exact block into
   every lab; log the active preset line in every capture.
2. Calibration lab, when you need numbers: reproduce the viewer bit-exactly in
   an isolated Godot project; sample the same face polygons in sprite and
   capture in linear light; validate a pass-based predictor against direct
   captures (within 0.1 sRGB). XCOM result at shipped lighting: lit faces
   1.84x sprite (1.5-3.0), shaded faces 0.81. A fit (sun 0.75, ambient 0.45,
   specular 0.25) reached lit 0.99 / shaded 0.38. NOT APPLIED (user choice).
3. Neutral diagnostic preset (`--neutral-lighting`): white key 0.8, white
   ambient 0.35, constant gray reflection sky 0.4, linear tonemap; key
   direction, shadows, SSAO, background and model bytes unchanged. Compare
   both presets on the same sealed export before requesting an albedo change.
4. Per-batch colour lab: each worker may copy the perf-lab scenes (not its
   `.godot/`) into `labs/<batch>/`, load exports at runtime with GLTFDocument
   (nothing imported into the main project), and compare luma per region with
   the sprite. Apply corrections as per-channel ratios to atlas cells, and only
   for hue/saturation/contrast, not absolute brightness.

## Rules that survived

- Modern lighting is expected to render brighter than sprites, and real
  shadows darker than baked sprite shading. Not a defect.
- Judge form, hue, saturation and contrast relationships, not absolute
  brightness or shadow depth. Do not chase encoded pixel-luma scores.
- One global decision instead of per-asset darkening.
- Specular 0.5 puts a gray veil on dark surfaces (black tile sRGB 48 at 0.5,
  18 at 0.25, 0 at 0). For dark foliage the fix is a lower runtime specular on
  those materials (plant wax: 0.25), not a retint.

## Blender working-render settings that cost iterations

- Verify the sun vector: `rotation_euler=(55deg, 0, 35deg)` lit the model from
  behind for several passes. Keep world ambient low (~0.22) so form shows.
- AgX/Filmic desaturates bright saturated orange to pink-white; use exposure
  -0.35 or compare under Khronos PBR Neutral.
- A world-coordinate gradient sky rendered metals near black in EEVEE; sheets
  used a constant 0.47 gray world. Blender suns need x pi to match Godot's
  diffuse level (sun 1.65*pi).
- Fixed studio lights make one view of a turntable look wrong (glare or a dark
  back); note it rather than "fixing" the material.
- Always add a game-distance crop (30 deg elevation, ~5 m) beside close-ups.
- Before fixing a bright patch, check it is not a sunlit face bounded by a cast
  shadow.

## Gotchas

- Linear tonemapping clips highlights; do not infer a pigment error from them.
- Godot renders lighter than Blender; calibrate in Godot, not in Blender.
- Unit-lab textures had `mipmaps/generate=false`; without mips normal and
  albedo alias into sparkle and read lighter at game zoom. Match import
  settings between labs and the game before comparing.
- Godot multiplies a roughness texture by the scalar; on textured materials a
  global "roughness offset" slider can only darken, never add.

## Source

- XCOM `art/review/lighting_calibration/README.md`, `lighting_calibration.json`
- XCOM `art/review/neutral-light-diagnostic-research.md`
- XCOM `art/team/ORCHESTRATION_OPUS55.md` ("MODERN LIGHTING IS EXPECTED TO
  DIFFER", "Godot preview lab")
- XCOM `art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md` section 9,
  `art/team/items_opus55/research.md` (review lighting)
- XCOM `art/team/tools/previewer_lighting/CHECKPOINT.md`
- XCOM `docs/BATTLESCAPE_3D_INTEGRATION.md` (render debug panel, shipped profile)
