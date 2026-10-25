# tools/

Plain-Python and PowerShell tools that act on one game repo at a time. Run them from the game root
(or set `ART_GAME_ROOT`); `pipeline_paths.py` resolves every input/output (`docs/game-layout.md`).
Blender-side libraries are in `../kits/`, engine-side scripts in `../engine/godot/`.

## Core (trick-or-treat lineage, low-poly palette pipeline)

| File | What | Origin |
|---|---|---|
| `pipeline_paths.py` | game-root + `art/pipeline.json` resolution; `python pipeline_paths.py` prints the resolved layout | art-pipeline original |
| `make_palette.py` | palette spec -> `palette.png`, `palette_emit.png` (glow RGB + flicker alpha), `palette_cells.json`, optional C++ header | trick-or-treat `art/tools/` |
| `set_palette_row.py` | rewrite one lane-owned palette row in place, then rebuild | generalised from lane `set_palette_row.py` scripts |
| `make_materials.py` | painted sources -> neutralised, seamless 512 px albedo + derived normal Texture2DArrays, `materials.json`, generated `toon.tres`, contact sheet, optional C++ header | trick-or-treat `art/tools/` |
| `gates.py` | cheap gates on exported glTFs (budget, palette, material layer, AO, degenerate, ground, parts, sockets) | trick-or-treat `art/tools/` |
| `publish_catalog.py` | publish gate-passing assets to the engine catalog | trick-or-treat `art/tools/` |
| `catalog_register.py` | add/update a lane's catalog entries in one read-modify-write | generalised from lane `register.py` / `catalog_update.py` |
| `inspect_gltf.py` | bounds, sockets, palette cells used per asset | trick-or-treat `art/team/landmarks/batch03/` |

## Subfolders

| Folder | What |
|---|---|
| `vfx/` | particle sprites and flipbooks (trick-or-treat) and Mantaflow sims + atlas packing (XCOM); see its README |
| `audio/` | `fm_synth.py` (2-operator OPL2-style FM synth), `make_sfx.py`, `make_music.py` (trick-or-treat's effects and song; edit the tables per game). numpy. See `techniques/fm-synth-audio.md` |
| `imagegen/` | `codex_imagegen.ps1`: one image via the signed-in Codex CLI's image_gen, with a provenance sidecar; `-Root` = game root. See `techniques/ai-texture-generation.md` |
| `textures/` | PBR derivation, WebP finalising, dedupe, Godot import policy, CC0 fetch (XCOM lineage); see its README |
| `review/` | review sheets, validation and gate tools, web asset reviewer (mostly XCOM lineage, XCOM catalog schema) and `distance_check.py`; see its README |

Every copied file starts with `Origin:` and `Changed:` lines. When you change a tool, add a
`CHANGELOG.md` entry and update the docs or technique that describes it (see `../CLAUDE.md`).
