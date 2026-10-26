# Glossary

Terms used across the docs, tools, techniques and game repos.

| Term | Meaning |
|---|---|
| **ToT** | trick-or-treat (`S:\Repos\trick-or-treat`), the reference game: textured low poly on a shared palette, Godot 4.7 + GDExtension C++ |
| **XCOM** | OpenXcom-Extended-3D (`S:\Repos\OpenXcom-Extended-3D`): PBR assets rebuilt from sprites, the strictest review process |
| **Game root** | the game repo the tools act on: `ART_GAME_ROOT`, else the nearest folder with `art/pipeline.json`, else the cwd. Check it with `tools/pipeline_paths.py` |
| **`pipeline.json`** | `art/pipeline.json` in a game: overrides of the default paths and settings (`game-layout.md`) |
| **Root** | the main agent session: owns shared files, imports, approval (`lane-batch-workflow.md`) |
| **Worker** | a subagent building one lane's batch |
| **Lane** | a family of related assets owned by one worker (`foliage`, `vehicles`, `monsters`, `characters_candy`...) |
| **Batch** | one art pass of a lane, `art/team/<lane>/batchNN/` (ToT: `batch01` flat, `batch02` textured, `batch03` fidelity) |
| **Brief** | `art/team/BRIEF.md`: the art pass's goals and rules for workers (`team-brief-template.md`) |
| **Catalog** | `art/asset_catalog.json`: every asset's id, path, lane, triangle budget, brief, collision, sockets, parts (`catalog-schema.md`) |
| **Published catalog** | the engine's `assets/catalog.json`, written by `publish_catalog.py` from gate-passing assets only |
| **Palette** | a 16 x 16 grid of named colour cells (`palette.json` -> `palette.png`); meshes pick a cell via UVs instead of carrying colours |
| **Palette row** | one row of 16 cells owned by one lane, identified by its first cell name (`set_palette_row.py`) |
| **Glow cell** | a palette cell with a flicker value: emissive in `palette_emit.png` (`glow-cells-and-bloom.md`) |
| **Material layer** | one painted texture in the albedo/normal `Texture2DArray`s (`painted-material-arrays.md`) |
| **UV2 encoding** | the toon shader reads palette cell and material layer from UV2 (`palette-tint-uv.md`) |
| **Kit** | a Blender helper library in `kits/` (`lowpoly_kit` core plus lane kits) |
| **Gates** | cheap automated checks on an exported glTF (`gates.py`): budget, palette, material layer, AO, degenerate triangles, ground origin, parts, sockets. Passing is not approval |
| **Floating** | an asset exempt from the ground-origin gate (candy, clouds, hanging lanterns) |
| **Sockets** | named empties in a glTF for attachment points (`socket_light`, hand, seat...) |
| **Parts** | separately exported sub-meshes a game animates (wings, tail, door) |
| **Review sheet** | Workbench 4-view PNG from Blender, for shape (`review-sheets.md`) |
| **Engine preview** | the 2 x 2 in-engine sheet (night + studio) from `asset_preview.ps1`, for materials and glow |
| **Visual gate** | root's judgement of the engine preview and play-distance check (`review-gates.md`) |
| **Revision queue** | XCOM's table of assets that failed the visual gate, with severities |
| **`results.json` / `CHECKPOINT.md`** | a batch's machine-readable and human hand-offs |
| **Build stamp** | a key written into the glTF scene extras on every export so Godot re-imports |
| **Godot lock** | `<game>\.godot_lock`, held by every Godot import or capture so only one runs per project |
| **Engine addon** | `engine/godot` vendored into a game as `res://addons/art_pipeline/` by `sync_engine_addon.ps1` |
| **Cine / shot** | a game's scripted cinematic mode and one named shot of it, used for trailers and stills (`trailer-shot-capture.md`) |
| **Options sheet** | labelled stills of one shot in several world seeds for the user to choose from (`shot_options.ps1`) |
