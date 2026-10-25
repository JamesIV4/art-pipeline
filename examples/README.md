# examples/

References, not templates to run in place. Build scripts export into whichever game root they run
from, so run them only against the game they came from.

## trick-or-treat/ (S:\Repos\trick-or-treat, Godot 4.7 + GDExtension, textured low poly)

| File | What |
|---|---|
| `BRIEF.md` | the real v2 worker brief (the template is `docs/team-brief-template.md`) |
| `build_bush_pot.py` | `bush_round` + `flower_pot`: yard_common style (lumpy blobs, `cull_hidden`, `paint_world`, lathe pot, `finish`) |
| `build_pumpkins.py` | four pumpkins/gourds: farm_lib style (`pumpkin_body`, `stem`, `tendril`, `drape` a leaf on the body) |
| `asset_catalog.sample.json` | 11 catalog entries covering every field (sockets, parts, walkable, bounce, trunk collision, floating, tier/glow) |
| `palette.json` | the palette spec (16x16 named cells, glow row with flicker values): a starting palette |
| `materials.json` | the 28 painted material layers with tiling scale, strength, normal strength and the image-gen subject prompts plus shared style string |
| `results.example.json`, `CHECKPOINT.example.md` | a real lane hand-off (yard_street batch02) |

trick-or-treat uses the default layout, so it needs no `art/pipeline.json`.

## openxcom/

| File | What |
|---|---|
| `pipeline.json` | what `S:\Repos\OpenXcom-Extended-3D\art\pipeline.json` would need for the ported XCOM tools to find its Godot project |

## new-game/

| File | What |
|---|---|
| `pipeline.json` | a starter config for a game whose Godot project is in `godot/` and has no C++ |
