# Game repo layout and `art/pipeline.json`

The pipeline owns tools; each game owns its data and outputs. The reference layout is
trick-or-treat's, and every default in `tools/pipeline_paths.py` reproduces it, so a game laid out
like this needs no config at all:

```
<game>/
  art/
    pipeline.json            optional: path/setting overrides (below)
    asset_catalog.json       every asset: id, path, lane, budget, brief, collision... (catalog-schema.md)
    palette/palette.json     the palette spec (16x16 named cells, glow cells carry a flicker value)
    materials/materials.json painted material layers; materials/source/<name>.png painted sources (+ .provenance.json)
    materials/preview.png    contact sheet (generated)
    team/BRIEF.md            the worker brief for the current art pass (team-brief-template.md)
    team/<lane>/<batchNN>/   build scripts, lane helpers, results.json, CHECKPOINT.md
    review/sheets/           Workbench 4-view sheets (generated, gitignore or keep small)
    review/engine/           in-engine preview sheets (generated)
    review/captures/         scene captures (generated)
    review/concept/          concept / target images the user supplied
    vfx/_frames/             rendered particle frames (generated)
  game/                      the Godot project (godot_project)
    addons/art_pipeline/     engine/godot from this repo (copy or junction)
    assets/palette/          palette.png, palette_emit.png, palette_cells.json (generated)
    assets/materials/        albedo_array.png, normal_array.png, materials.json (generated)
    assets/models/<path>.gltf/.bin  exports
    assets/catalog.json      published catalog the game reads (generated)
    assets/vfx|sfx|music/    generated effects and audio
    materials/toon.tres      generated shared material
  native/src/mesh/*.gen.h    optional C++ headers (palette cells, material ids)
```

## `art/pipeline.json`

All keys optional. Paths are relative to the game root (absolute paths also work); `null` disables
an output.

```json
{
  "paths": {
    "godot_project": "godot",
    "models_out": "godot/assets/models",
    "palette_out": "godot/assets/palette",
    "materials_out": "godot/assets/materials",
    "published_catalog": "godot/assets/catalog.json",
    "toon_material": "godot/materials/toon.tres",
    "vfx_out": "godot/assets/vfx",
    "sfx_out": "godot/assets/sfx",
    "music_out": "godot/assets/music",
    "native_header_dir": null
  },
  "settings": {
    "cpp_namespace": "mygame",
    "toon_shader_res": "res://addons/art_pipeline/shaders/surface/toon.gdshader",
    "floating_prefixes": ["sky/", "pickups/"],
    "floating_ids": [],
    "publish_fields": ["id", "path", "collision", "walkable", "radius", "height"],
    "scale_figure_height_m": 1.7,
    "scale_figure_color": "skin",
    "build_stamp_key": "mygame_build"
  }
}
```

| Path key | Default | Used by |
|---|---|---|
| `palette_spec` | `art/palette/palette.json` | make_palette, lowpoly_kit, set_palette_row |
| `materials_spec` / `materials_source` | `art/materials/materials.json` / `art/materials/source` | make_materials, lowpoly_kit, gates |
| `catalog` | `art/asset_catalog.json` | gates, publish_catalog, catalog_register, inspect_gltf, asset_preview |
| `vfx_frames` | `art/vfx/_frames` | make_vfx, make_fire, assemble_vfx |
| `palette_out` | `game/assets/palette` | make_palette (writes), kit and gates (read `palette_cells.json`) |
| `materials_out` | `game/assets/materials` | make_materials |
| `models_out` | `game/assets/models` | kit export, gates |
| `published_catalog` | `game/assets/catalog.json` | publish_catalog |
| `vfx_out`, `sfx_out`, `music_out` | `game/assets/{vfx,sfx,music}` | VFX and audio generators |
| `toon_material` | `game/materials/toon.tres` | make_materials |
| `native_header_dir` | `native/src/mesh` | make_palette, make_materials (C++ headers) |
| `review_sheets`, `review_engine`, `review_captures` | `art/review/{sheets,engine,captures}` | kit review_sheet, previews |
| `materials_preview` | `art/materials/preview.png` | make_materials |
| `godot_project` | `game` | engine scripts, XCOM tools |

| Setting | Default (trick-or-treat) | Meaning |
|---|---|---|
| `cpp_namespace` | `tot` | `<ns>::pal`, `<ns>::mat` in generated headers |
| `palette_grid` | 16 | cells per palette side |
| `toon_shader_res`, `palette_res`, `palette_emit_res`, `albedo_array_res`, `normal_array_res` | trick-or-treat's res:// paths | written into the generated `toon.tres` |
| `floating_prefixes`, `floating_ids` | `candy/`, `sky/`; three lantern ids | skip the ground-origin gate (also per asset: `"floating": true`) |
| `ground_tolerance_m` | 0.03 | ground-origin gate tolerance |
| `publish_fields` | trick-or-treat's 10 fields | fields copied into the engine catalog |
| `scale_figure_height_m`, `scale_figure_color` | 1.1, `dragon_teal` | review-sheet scale post (the hero's height, a palette name) |
| `build_stamp_key` | `tot_build` | glTF scene-extras key that forces re-import |
| `blender_exe`, `godot_exe` | toolchain.md paths | overridden by `BLENDER_EXE` / `GODOT_EXE` |

The PowerShell twin is `engine/godot/review/art_pipeline_paths.ps1`. XCOM's layout is different
(Godot project at `xcom-3d-godot/x-com--ufo-defense-3d`, PBR textures, a much richer catalog); its
tools under `kits/xcom` and `tools/{review,textures}` read their own XCOM-specific locations, listed
in each folder README.
