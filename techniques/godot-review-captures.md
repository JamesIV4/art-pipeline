# Godot review captures (asset preview sheets, scene captures, render controls)

## What it is

The engine half of review: scripts that render an asset or a game view in the real Godot renderer, with the real
shader and lighting, to a PNG an agent or the user can judge. Three tools in `engine/godot/review/`:

- `asset_preview.ps1 -Id <catalog id>`: one asset, a 2 x 2 sheet (1600 x 900). Top: night light (moon + warm porch
  omni) front-left and back-right; bottom: neutral studio key (moon dimmed) front-left high and side-on low.
- `review.ps1 -Seeds 101,102 -Views play,overview`: whole-game captures through the game's own `--capture` mode.
- `CaptureGodotReview.ps1`: XCOM's sealed per-asset capture with import-freshness and stdout-contract checks, plus
  `controls/*.gd` single-variable render diagnostics.

## Why

- Blender / Workbench sheets cannot show the toon ramp, palette glow, bloom, SSAO or the real texture arrays; only
  the engine does (`toon-shading.md`), so final colour, glow and material judgements use an engine sheet.
- Several art workers run at once; two Godot imports on one project corrupt the `.godot` cache, and a running Godot
  holds the GDExtension DLL. Every capture goes through one lock.
- A capture of a stale import or the wrong catalog looks valid. XCOM's capture refuses unless the import cache MD5
  matches the source, the glTF sidecars match their seals, and the viewer prints the expected checks.

## How

- Lock: `godot_lock.ps1` opens `<game root>\.godot_lock` with FileShare None (retry every 0.7 s, 900 s timeout).
  The handle dies with the process, so there are no stale locks.
- Game root: `-GameRoot`, else `$env:ART_GAME_ROOT`, else the folder holding `art\pipeline.json`, else the current
  directory; the Godot project is `pipeline.json paths.godot_project` (default `game`); Godot is `-Godot`,
  `$env:GODOT_EXE` or the 4.7 console exe.
- Asset preview: `godot --headless --import --path <project>` first (picks up new / changed glTF), then a windowed
  run at `--resolution 1600x900` of `res://addons/art_pipeline/review/asset_preview.tscn -- --preview=<res gltf>
  --capture=<png> --material=<toon.tres> [--ground-uv2=layer,u,v --path-uv2=layer,u,v]`.
  Framing: bounds of every MeshInstance3D; distance = (diagonal / 2) / tan(fov / 2) x 1.25 at fov 56; views
  (yaw, pitch rad) = (-0.6, 0.38), (2.5, 0.38), (-0.6, 0.45) studio, (-1.57, 0.12) studio. Wait 8 frames before the
  first shot and 6 between (temporal effects settle). Warm omni (1.0, 0.58, 0.26) x 1.6, range 6 + diagonal; studio
  key (1.0, 0.97, 0.92) x 1.3 from (0.4, -0.8, -0.5); moon 0.62 night / 0.25 studio. Assets reaching below y = 0
  (floating props) are lifted to 0.25 m. No DOF, cutout off. Prints `CAPTURED <path>`.
  `-Scene main` instead runs the game's main scene with `--preview=` (trick-or-treat's C++ version, real lawn).
- Scene captures: `--seed= --capture= --capture-frames=200 --capture-view=` are implemented by the game (trick-or-treat
  views: play, overview, lot:N, nest:N, gate, shop, prop:ID#K, at:x,z, atover:x,z). `-BuildNative` rebuilds the
  extension with scons / MinGW inside the lock first.
- Render controls: `godot --path <project> --script <abs path>\controls\ssao_control.gd -- --control-scene=res://...`
  loads the scene, flips exactly one thing (SSAO off, directional shadows off, mesh LOD threshold 0, shadow distance
  24 m, or shadow distance fitted to the camera depth of all geometry / fade start), asserts nothing else changed and
  prints a `TACTICAL_*_CONTROL` line. Compare against an unchanged capture to attribute an artefact to one system.
- Sealed captures (XCOM): `.import` -> cache path -> `.md5` must hold `source_md5` of the current source; glTF
  sidecars must match `asset.extras.render_dependency_sha256`; receipts (`import-receipt.json`,
  `runtime-receipt.json`) are written next to the PNGs; Godot runs hidden at `--position -10000,-10000` with a 45 s
  kill timeout.

## Gotchas

- Captures need a GPU and a window: never `--headless` for the render step (only for `--import`).
- The previewer applies the material override to every MeshInstance3D: a glTF with its own special materials needs
  `-Material none`.
- `--ground-uv2` is in the toon encoding: `layer,u,v` with u, v the palette cell centre ((col + 0.5) / 16); without
  it the floor is the neutral grid (good for silhouettes, wrong for colour judgement against ground).
- PowerShell passes `--` before the user args; keep it as its own array element.
- A control that finds more than one DirectionalLight3D or WorldEnvironment fails its assert on purpose: the
  comparison must be single-variable.
- Equal bytes rewritten later look "changed" by mtime; XCOM trusts source MD5 + seals, never timestamps.

## Source

- trick-or-treat: `tools/asset_preview.ps1`, `tools/review.ps1`, `tools/godot_lock.ps1`,
  `native/src/play/festival_game.cpp` (parse_cmdline, setup_preview, step_preview), README "Command-line review modes".
- XCOM: `art/tools/CaptureGodotReview.ps1`, `art/tools/godot_main_lock.py`, `art/tools/{ssao,shadow,lod,
  shadow_distance,shadow_scene_aware_control_v2}*.gd`.
- Ported: `engine/godot/review/`. Related: `review-sheets.md`, `independent-review-gates.md`,
  `lighting-calibration.md`.
