# art-pipeline

The central art pipeline for every game: 3D assets written as code and built in headless Blender,
checked by cheap automated gates, exported as glTF, published through a catalog, and reviewed in the
engine (Godot 4.7). It was extracted on 2026-10-25 from two game repos:

- **trick-or-treat** (`S:\Repos\trick-or-treat`): cosy Halloween platformer, Godot 4.7 + GDExtension.
  Textured low-poly: a shared 16x16 palette, painted material layers in texture arrays, vertex AO, a
  toon shader. It is the reference layout and the default for new games.
- **OpenXcom-Extended-3D** (`S:\Repos\OpenXcom-Extended-3D`, "XCOM"): a 3D remake of X-COM whose
  pipeline trick-or-treat adapted. PBR assets rebuilt from source sprites, a strict review process,
  rendering research (layered merges, LOD, lighting calibration, render cost).

Knowledge (techniques, research, process) is shared by every game; tools are generic where that was
cheap, and each file says where it came from.

## For AI agents: start here

You are probably here because you were asked to make or change art (a model, texture, palette,
material, effect, sound, shader, lighting, a capture, a trailer or an icon) in one of the user's games.

1. Read [CLAUDE.md](CLAUDE.md): the standing rules, including the **write-back** you owe this repo at
   the end of every art task. (Other agents: [AGENTS.md](AGENTS.md) points to the same file.)
2. Find the command for your task in [docs/recipes.md](docs/recipes.md); terms are in
   [docs/glossary.md](docs/glossary.md); the doc index is [docs/README.md](docs/README.md).
3. Before inventing a method, look it up in [techniques/README.md](techniques/README.md) (by topic)
   and the newest [research/](research/README.md) notes for the game you are in. Read the Gotchas.
4. Run tools from the **game root**, not from here. `python S:\Repos\art-pipeline\tools\pipeline_paths.py`
   prints which game and which paths a tool would touch.
5. Use the PowerShell tool (the Bash tool is broken on this machine), Blender only headless, the
   Godot `_console` exe, and never kill or import over the user's open Godot editor
   ([docs/toolchain.md](docs/toolchain.md)).

| I need to... | Look at |
|---|---|
| build or change a 3D asset | `kits/lowpoly/README.md`, `examples/trick-or-treat/build_*.py`, `techniques/lowpoly-textured-style.md` |
| decide if an asset is good enough | `docs/quality-contract.md`, `docs/review-gates.md`, `techniques/art-direction-fidelity.md` |
| see an asset in the real renderer | `engine/godot/review/asset_preview.ps1`, `techniques/godot-review-captures.md` |
| change colours or painted materials | `tools/make_palette.py`, `tools/set_palette_row.py`, `tools/make_materials.py`, `techniques/palette-tint-uv.md` |
| make particles, fire or sounds | `tools/vfx/README.md`, `tools/audio/`, `techniques/flame-flipbooks.md`, `techniques/fm-synth-audio.md` |
| set up shaders, lighting, post | `engine/godot/README.md`, `techniques/toon-shading.md`, `techniques/post-processing-stack.md` |
| record a trailer, stills or an icon | `tools/marketing/README.md`, `techniques/trailer-shot-capture.md`, `techniques/engine-rendered-icon.md` |
| run parallel art workers | `docs/lane-batch-workflow.md`, `docs/team-brief-template.md` |
| start a new game on the pipeline | "Adopting it in a game" below, `docs/game-layout.md`, `docs/recipes.md` section 1 |
| know what the user has already decided | `techniques/art-direction-fidelity.md` and the game's `research/*-retro.md` notes |

### Status and known limits (2026-10-26)

- trick-or-treat still runs its own in-repo copies of the tools (`art/tools/`, lane kits); changes
  made there must be ported here (CLAUDE.md, "Pulling improvements back").
- The Godot side of this repo (shaders, presets, the GDScript previewer) has not been run in-engine
  from here yet; trick-or-treat's C++ preview is the proven path.
- XCOM-lineage tools (`kits/xcom`, `tools/review`, `tools/textures`) still assume XCOM's layout and
  catalog schema; see their READMEs.
- Godot 4.7 has no plugin route for DLSS / FSR 3 / FSR 4 yet
  (`research/2026-10-26-tot-polish-pass-retro.md`).

## The flow

```
 brief            build script                 gates / QA            export           publish            engine review
 art/team/        art/team/<lane>/<batch>/     tools/gates.py        K.export()       tools/            engine/godot/review/
 BRIEF.md   -->   build_x.py (Blender,   -->   K.review_sheet() -->  .gltf + .bin --> publish_catalog -> asset_preview.ps1
 + catalog        kits/lowpoly)                inspect_gltf.py       (models_out)     .py (only gate-   review.ps1, distance
 entries                                                                              passing assets)    check, root visual gate
```

1. **Brief.** Root writes `art/team/BRIEF.md` from `docs/team-brief-template.md` and adds catalog entries
   (id, path, lane, triangle budget, brief, collision, sockets, parts) with `tools/catalog_register.py`.
   The palette (`tools/make_palette.py`, one row per lane via `tools/set_palette_row.py`) and painted
   materials (`tools/make_materials.py`, sources via `tools/imagegen/codex_imagegen.ps1`) are built first.
2. **Build.** Workers write Blender scripts per lane and batch using `kits/lowpoly` (palette tint,
   material layer and projection on every primitive; merge, AO bake, export, review sheet).
   `blender --background --factory-startup --python build_x.py -- <ids>`, run from the game root.
3. **Gates and QA.** `tools/gates.py <ids>` (budget, palette, material layer, AO, degenerate triangles,
   ground origin, parts, sockets) must PASS. Workbench 4-view sheet for shape. XCOM-style PBR assets use
   `tools/review/root_independent_checks.py` and friends.
4. **Export.** glTF separate, Y-up, no materials, a build stamp so Godot re-imports; the game applies
   the shared toon material.
5. **Publish.** `tools/publish_catalog.py` writes the engine catalog with only gate-passing assets.
6. **Engine review.** `engine/godot/review/asset_preview.ps1 -Id <id>` renders night + studio views with
   the real shader; `review.ps1` captures game scenes; `tools/review/distance_check.py` checks play
   distance. Root does the visual gate (docs/review-gates.md); failures go to a revision queue.

Process rules: `docs/quality-contract.md`, `docs/lane-batch-workflow.md`, `docs/review-gates.md`.

## Layout

| Path | What |
|---|---|
| `tools/` | generic Python / PowerShell tools: palette, materials, gates, catalog, VFX, audio, image generation, textures, review, marketing (trailer clips, shot options, icon matte) (see `tools/README.md`) |
| `kits/lowpoly/` | Blender helper libraries for textured low poly (core `lowpoly_kit.py` + lane kits) |
| `kits/xcom/` | Blender helper libraries from XCOM (assembly, atlas, glTF writer, textures, sheets, finalize, master render, SDF meshes, poses) |
| `engine/godot/` | shaders, post-processing, environment presets, review/capture scripts; install as `res://addons/art_pipeline/` |
| `docs/` | process: recipes, glossary, toolchain, game layout + `pipeline.json`, asset conventions, quality contract, lane/batch workflow, review gates, catalog schema, team brief template (index: `docs/README.md`) |
| `techniques/` | one file per learned technique (what, why, how, gotchas, source) |
| `research/` | dated research notes and retrospectives |
| `examples/` | real build scripts, catalog sample, palette/material specs, a brief and a checkpoint; example `pipeline.json` files |
| `CLAUDE.md` / `AGENTS.md` | standing instructions for agents doing art in any game |
| `CHANGELOG.md` | every tool / kit / engine change |

## Toolchain

Windows 11; Blender 5.1 (`C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`, headless only);
Godot 4.7 standard console build (`C:\GameDev\Godot_v4.7-stable_win64\Godot_v4.7-stable_win64_console.exe`);
Python 3.13 with `numpy` and `Pillow`; PowerShell 5.1 (the Claude Code Bash tool is broken on this
machine). Optional: MinGW + SCons for GDExtension games, the Codex CLI for painted texture sources.
Details, environment variables (`ART_GAME_ROOT`, `ART_PIPELINE`, `BLENDER_EXE`, `GODOT_EXE`) and
machine gotchas: `docs/toolchain.md`.

```powershell
pip install numpy pillow
python S:\Repos\art-pipeline\tools\pipeline_paths.py      # from a game root: shows what the tools will touch
```

## Adopting it in a game

Three options were considered:

| Option | For | Against |
|---|---|---|
| Copy the tools into each game | self-contained | improvements stay stranded in one game; copies drift (this is how trick-or-treat's lane kits multiplied) |
| Git submodule | pinned version per game | two-repo commits for every tweak, detached-HEAD friction on Windows, agents edit the pinned copy and lose changes |
| **Reference by path** (recommended) | one clone, every game uses the latest tools, improvements land once | a game's build depends on the pipeline being present; record the pipeline commit you built with |

**Recommendation: reference the tools and kits by path, and vendor only the engine addon.**

1. Keep one clone at `S:\Repos\art-pipeline` (or set `ART_PIPELINE`).
2. In the game, lay out `art/` as in `docs/game-layout.md`. If the layout differs from the defaults,
   add `art/pipeline.json` (start from `examples/new-game/pipeline.json`).
3. Copy a starting palette and materials spec (`examples/trick-or-treat/palette.json`,
   `materials.json`), then `python S:\Repos\art-pipeline\tools\make_palette.py` and `make_materials.py`
   from the game root.
4. Build scripts import the kits by path:
   `sys.path.insert(0, os.path.join(os.environ.get("ART_PIPELINE", r"S:/Repos/art-pipeline"), "kits", "lowpoly"))`.
5. Install the engine side into the Godot project with
   `powershell -File S:\Repos\art-pipeline\tools\sync_engine_addon.ps1 -GameRoot <game>`: a vendored copy
   at `res://addons/art_pipeline/` (it has to ship with the game's export) with a `VERSION.txt` recording
   the pipeline commit and file hashes. Re-run it to update; `-Diff` shows game-side edits to upstream.
   Then follow `engine/godot/README.md` (paste `presets/project_rendering.cfg`, instance a rig, set
   `settings.toon_shader_res` to the addon shader).
6. Copy `docs/team-brief-template.md` to `art/team/BRIEF.md` and point the game's own `CLAUDE.md` at
   this repo's `CLAUDE.md`.

trick-or-treat already matches the default layout (no `pipeline.json` needed); it still runs its own
in-repo copies until it is switched over. XCOM would need `examples/openxcom/pipeline.json`.

## Key render settings (Godot 4.7 Forward+)

Full side-by-side tables: `engine/godot/presets/project_settings_rendering.md`.

| Setting | trick-or-treat (night) | XCOM "Latest 2" (day) |
|---|---|---|
| AA / shadows | MSAA 4x; 8192 atlas, Ultra; moon PSSM4 70 m | MSAA 4x; 8192, Ultra; sun PSSM4 515 m |
| Tonemap | Filmic, exposure 1, white 1 | same |
| Key light | moon (0.6, 0.7, 1.0) x 0.62, 52 deg elevation | sun #897f6a x 3.44, 45.5 deg elevation |
| Ambient | (0.42, 0.48, 0.85) x 0.55, sky reflections | #4f6995 x 2.22, neutral grey reflection sky |
| SSAO / SSIL | radius 1.61, intensity 16, power 1.5 / radius 10.87, intensity 1.6 | same |
| Glow | levels 0/0.8/0.4/0.1, intensity 3.41, strength 1.12, threshold 1.0, soft light | same |
| Post | sharpen 0.27, vignette, dither, compositor depth AO 0.46 m | same + film grain 0.015 |
| Fog / DOF | fog 0.004, volumetric 0.011; toy-lens DOF | off |
