# Palette tint via UV (shared 16x16 palette, layer + cell in UV2)

## What it is

All colour comes from one shared palette texture: a 16x16 grid of named cells (16 px each,
256x256 png). Each face's tint UVs sit on the centre of one cell. With painted materials (kit v2)
the second UV map ("Tint", glTF TEXCOORD_1) encodes both: `u = material_layer + cell_u`,
`v = cell_v`. The shader takes `floor(UV2.x)` as the texture-array layer and `fract(UV2.x)` as the
palette u. The first UV map ("UVMap", TEXCOORD_0) carries material tiling in metres.

## Why

One palette keeps every asset (Blender props and C++ procedural meshes) in one colour world, makes
colour edits global, and lets one painted texture serve every tint (one siding texture for every
house colour). Glow is a property of the cell, so emissive parts need no extra material.

## How

- Spec: `art/palette/palette.json` with `cell_px`, `grid`, and `rows`: each entry
  `"name:#rrggbb"` or `"name:#rrggbb:flicker"`. A third field marks a glow cell; flicker 0..1 is
  written to the emit texture's alpha (0 = steady, 0.6 = candle flicker).
- Build: `tools/make_palette.py` writes `palette.png` (albedo; unused cells magenta),
  `palette_emit.png` (glow RGB + flicker alpha, black elsewhere), `palette_cells.json`
  (name -> col,row,u,v,glow) for the Blender kit, and a C++ header with cell constants and RGB.
- Kit: `_uv_cell(color)` flips v for Blender (PNG row 0 is the top; glTF export flips back).
  `_paint_bm` writes `(u + layer, v)` on every loop of the face.
- Shader (toon.gdshader): `tint = texture(palette, cell)`; `ALBEDO = tint * mix(1, detail*2,
  layer_strength)`; `EMISSION = emit.rgb * 2.6 * flicker * glow_boost`. Meshes without UV2 fall
  back to the flat path. `glow_boost` is an instance uniform (locked areas dim their glow).
- Gate (tools/gates.py): every tint UV within 1/4 cell of a cell centre, on a used cell, and the
  layer index inside 0..N_LAYERS-1.

Palette organisation that worked across 10 concurrent lanes:

- Rows 0-8 are the shared base (neutrals, wood, pumpkin, foliage, houses, candy, characters,
  textiles, glow row 8). Later rows belong to one lane each (row 10 decor, 12 dragon/candy,
  14 monsters, 15 candy_variety, 9 foliage tints).
- Each lane owns a `set_palette_row.py` that rewrites only its own line in place (matched by its
  first cell name, e.g. `["dragon_green:`), appends the row if missing (asserting the expected row
  count), validates the JSON, and leaves every other line byte-for-byte untouched. Then run
  make_palette.
- Only add cells when no existing cell fits; landmarks and vehicles batches added none.

## Gotchas

- Inserting a cell mid-row shifts every later column in that row: cell indices in already
  exported meshes then point at the wrong colour. Append at the end of a row only (characters
  batch03 hit this; nothing outside the lane referenced the shifted cells, by luck).
- The grid fills up: 16 rows were full after batch03. Plan rows per lane early.
- Workbench review sheets show colour attributes in linear space: convert sRGB with `** 2.2`
  or everything looks washed out. Skin still read tan in Workbench (preview darkening, not the cell).
- Glow cells look tan or orange in Workbench (no emission). Judge glow only in the engine.
- A glow cell close in hue to its surround (glow_jack #ff8a1f vs pumpkin #f07b1f) has no contrast
  in sheets; it only separates in game where it emits.
- Old v1 exports with palette UVs in UVMap break v2; helper libs must write UVMap first, then Tint.

## Source

trick-or-treat: art/palette/palette.json, art/tools/make_palette.py, art/tools/lowpoly_kit.py,
art/tools/gates.py, game/shaders/toon.gdshader, characters_candy/batch03 and monsters/batch03
set_palette_row.py and CHECKPOINTs.
