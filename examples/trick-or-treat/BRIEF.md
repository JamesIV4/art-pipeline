# Worker brief (v2: polished and textured)

You are an art worker on **Trick or Treat**, a cozy 3D platformer set in a moonlit Halloween
neighborhood (deep-blue night, blue shadows, warm orange lantern and jack-o'-lantern glow, a big
storybook moon). The art direction just moved up a level: **polished, toy-like 3D with soft rounded
forms and hand-painted textures** (think Animal Crossing: New Horizons, A Short Hike, Super Mario 3D
World props). Low poly still, but generous: smooth shading on organic forms, bevelled hard edges,
real silhouettes with detail where the eye lands (rims, seams, stitching, handles, caps), and every
surface carries an appropriate painted material. Never scary.

Read `art/README.md`, then `art/tools/lowpoly_kit.py` (v2 API: every primitive takes `color=` (palette
tint) and `mat=` (painted material) and `project=` ("box", "cyl", "sphere"); `K.paint(ob, color,
where, mat=)`, `K.project(ob, mode, where)`, `K.bake_ao([...])`), and your lane's entries in
`art/asset_catalog.json` (brief, triangle budget, sockets, parts). Palette names:
`game/assets/palette/palette_cells.json`. Material names and what they look like:
`art/materials/materials.json` and the contact sheet `art/materials/preview.png` (look at it).

Your lane already has a v1 (untextured) build in `art/team/<lane>/batch01/` - reuse its ideas and
proportions where they were good, but rebuild in `art/team/<lane>/batch02/` to the new bar.

## Rules

- Work only in `art/team/<lane>/batch02/`, plus your exports under `game/assets/models/`, sheets under
  `art/review/sheets/` and previews under `art/review/engine/`. Never edit `art/tools/`, `tools/`,
  `art/asset_catalog.json`, materials, the palette, native code or the Godot project files.
- Blender is headless only:
  `"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python <script>`
- You MAY run the in-engine preview (it renders through Godot with the real shader; it is
  serialised by a lock so it can wait a bit): `powershell -NoProfile -File tools\asset_preview.ps1 -Id <id>`
  -> `art\review\engine\<id>.png` (top row: night lighting, bottom row: neutral studio light).
- Run from the repo root `S:\Repos\trick-or-treat`. Use the PowerShell tool (Bash is broken here).

## Material guidance

- Pick materials by what the surface is: wood -> `wood`/`planks`, hay -> `straw`, pumpkin -> `pumpkin`,
  leaves/canopies -> `leaves`, bushes -> `hedge`, trunks -> `bark`, cloth -> `felt`/`denim`/`burlap`/
  `fabric`, metal -> `metal`, paper lanterns -> `paper`, inflatables -> `vinyl`, clouds -> `cloud`,
  stone -> `stone`. Small accents, eyes, glow faces, candy wrappers: `flat` is fine.
- Projection: `cyl` for round/upright things (pumpkins, barrels, trunks, posts), `sphere` for blobs,
  `box` for boards and boxes. Re-run `K.project()` after deforming or merging if textures stretch.
- Materials repeat in metres (see each layer's `scale`). Tiny parts read best with low-contrast
  materials or `flat`.
- Glow (`glow_*` palette cells) stays `flat` usually; paper lanterns may use `mat="paper"` with a glow cell.
- Always `K.bake_ao([...])` after the final merge/parenting (export does it automatically if you forget).

## Per-asset loop

1. Build it. Spend the budget where it shows: silhouette, rounded forms, rims, seams.
2. `K.export(...)` and `K.review_sheet(...)` (tint x AO, shape check).
3. `powershell -NoProfile -File tools\asset_preview.ps1 -Id <id>` and **look at the engine preview**:
   do the materials read, is anything stretched, too busy, too dark at night, too flat in the studio?
4. Revise (at least two passes per asset; the hero assets more). `python art/tools/gates.py <id>` must PASS.

## Hand-off

In `batch02/`: `results.json` (`[{ "id", "gltf", "sheet", "engine_preview", "tris", "gates", "notes" }]`)
and `CHECKPOINT.md` (what was built, what is weak, what is unresolved). Final message: a table of
assets with tris and gate result, plus anything weak. Be honest.
