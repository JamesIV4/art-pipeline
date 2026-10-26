# Recipes: common tasks with exact commands

Copy-paste starting points for the jobs agents are asked to do most. Every command runs in Windows
PowerShell 5.1 **from the game root** (or with `$env:ART_GAME_ROOT` set) unless it says otherwise.
`$P` is this repo and `$B` is Blender:

```powershell
$P = 'S:\Repos\art-pipeline'
$B = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
cd S:\Repos\<game>
python $P\tools\pipeline_paths.py        # always first: the game root and every path the tools will touch
```

Read the linked doc or technique before changing how something works; these recipes only cover the
happy path.

## 1. Set up a new game

1. Lay the game out as in `game-layout.md`. Add `art/pipeline.json` only for paths or settings that
   differ from the defaults (start from `examples/new-game/pipeline.json`).
2. Copy `examples/trick-or-treat/palette.json` to `art/palette/palette.json` and
   `examples/trick-or-treat/materials.json` to `art/materials/materials.json`, then edit them for
   the game's look.
3. `python $P\tools\make_palette.py`, then `python $P\tools\make_materials.py`. Materials without a
   painted source get a noise placeholder until recipe 7 runs.
4. `powershell -File $P\tools\sync_engine_addon.ps1 -GameRoot <game>` vendors `engine/godot` into
   `res://addons/art_pipeline/`, then follow `engine/godot/README.md` (render settings, a lighting rig,
   `toon_shader_res`).
5. Copy `team-brief-template.md` to `art/team/BRIEF.md` and fill it in. Point the game's own
   `CLAUDE.md` at this repo's `CLAUDE.md`.

## 2. Register assets in the catalog

Write the new entries (schema: `catalog-schema.md`) to a JSON list, then:

```powershell
python $P\tools\catalog_register.py entries.json            # add or replace whole entries
python $P\tools\catalog_register.py entries.json --merge    # update some fields of existing ids
python $P\tools\catalog_register.py --show bush_round        # print one entry
```

## 3. Build an asset

1. Put the script in `art/team/<lane>/<batchNN>/build_<thing>.py`. Start from
   `examples/trick-or-treat/build_bush_pot.py` (simple) or `build_pumpkins.py` (a family), and import
   the kits by path as `kits/lowpoly/README.md` shows.
2. Build only the ids you are working on:

   ```powershell
   & $B --background --factory-startup --python art\team\<lane>\<batch>\build_x.py -- <id> [<id> ...]
   ```

3. The kit exports the glTF to `models_out` and a Workbench 4-view sheet to `art/review/sheets/<id>.png`.
   Look at the sheet for shape before anything else.

## 4. Check an asset

```powershell
python $P\tools\gates.py <id> [<id> ...]     # or --lane <lane>, or --all
python $P\tools\inspect_gltf.py <id>         # bounds, sockets, palette cells used
```

Gates must PASS, but passing is not approval (`review-gates.md`).

## 5. Review in the engine

```powershell
powershell -File $P\engine\godot\review\asset_preview.ps1 -Id <id>    # art/review/engine/<id>.png
powershell -File $P\engine\godot\review\review.ps1 -Seeds 101 -Views play,overview   # whole-game captures
python $P\tools\review\distance_check.py art\review\engine\<id>.png art\review\engine\<id>_far.png
```

Open the PNGs and judge them under the game's real lighting and at play distance. The preview takes
the game's Godot lock, so it waits rather than colliding with another import. Never run it while the
user's editor has the project open unless the game's notes say that is safe.

## 6. Publish

```powershell
python $P\tools\publish_catalog.py     # writes the engine catalog with gate-passing assets only
```

## 7. Palette and materials

```powershell
# Change one lane's palette row in place (the row is found by its first cell name), then rebuild:
python $P\tools\set_palette_row.py --row 10 --owner bunting_cream "bunting_cream:#f6ead0" "glow_jack_face:#ffd864:0.05"
# A painted material source via the signed-in Codex CLI, with a provenance sidecar:
powershell -File $P\tools\imagegen\codex_imagegen.ps1 -Prompt "<prompt>" -Out art\materials\source\<name>.png
python $P\tools\make_materials.py      # rebuild the texture arrays, materials.json and toon.tres
```

See `techniques/palette-tint-uv.md`, `painted-material-arrays.md` and `ai-texture-generation.md`.

## 8. Effects and audio

```powershell
& $B --background --factory-startup --python $P\tools\vfx\make_vfx.py    # sprite and flipbook frames
python $P\tools\vfx\make_fire.py                                        # procedural flame flipbook
python $P\tools\vfx\assemble_vfx.py                                     # pack frames into game textures
python $P\tools\audio\make_sfx.py                                       # FM sound effects
python $P\tools\audio\make_music.py                                     # FM music loop
```

The effect lists, sound tables and song are trick-or-treat's. Copy and edit them for another game
rather than changing the defaults here.

## 9. Marketing captures

Stills, trailer clips and icons are rendered by the game's own capture modes. The workflow is in
`techniques/trailer-shot-capture.md` and `techniques/engine-rendered-icon.md`.

## 10. Upstream a tool fix from a game

Follow "Pulling improvements back from a game repo" in `../CLAUDE.md`: diff, port the logic, keep
paths behind `pipeline_paths`, run the checks, add a CHANGELOG entry, re-sync the addon.

## 11. Record what you learned

Do this at the end of every art task (`../CLAUDE.md`, "write back"):

- a reusable method goes in `techniques/<kebab-name>.md`, indexed in `techniques/README.md`;
- an investigation, comparison or retrospective goes in `research/YYYY-MM-DD-<game>-<topic>.md`,
  indexed in `research/README.md`;
- a tool, kit or engine change needs a `CHANGELOG.md` entry under "Unreleased".
