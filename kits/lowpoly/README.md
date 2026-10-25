# kits/lowpoly: Blender helpers for textured low-poly assets

Run inside headless Blender 5.1 with the **game root as the working directory** (or `ART_GAME_ROOT`
set): the kit reads that game's palette cells, palette spec and materials spec, and exports into its
models folder (`tools/pipeline_paths.py`). A build script starts with:

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ.get("ART_PIPELINE", r"S:/Repos/art-pipeline"), "kits", "lowpoly"))
import lowpoly_kit as K          # core
from yard_common import *        # optional: builders on top of K (re-exports K, bpy, bmesh, Vector, math)
```

```powershell
cd S:\Repos\<game>
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python art\team\<lane>\<batch>\build_x.py -- <ids>
```

All kits live side by side here, so their cross-imports (`import yard_common`, `import farm_lib as F`,
`import dk_kit as D`) resolve against this folder. Every file has an `Origin:` line; the logic is the
trick-or-treat batch version unchanged except for import paths.

| Kit | Origin (trick-or-treat `art/`) | Builds on | What it gives you | Reuse |
|---|---|---|---|---|
| `lowpoly_kit.py` | `tools/lowpoly_kit.py` (v2) | - | primitives (`box cylinder sphere ico torus tube polygon_prism`) with `color=` palette tint, `mat=` material layer, `project=` box/cyl/sphere UVs; `paint project deform lean merge empty socket set_parent tri_count bake_ao export review_sheet` | core, generic |
| `yard_common.py` | `team/yard_street/batch02` | K | seam-safe `sweep rod lathe blob loft arc bezier catmull`, `paint_world`, `uv_box`, `cull_hidden`, `cut_below`, `flatten_below`, `clean`, `finish` (clean + AO + export + sheet + gates line), `want()` id filter | generic, the usual base |
| `farm_lib.py` | `team/pumpkins_farm/batch02` | K | superset kit: `board slab rbox blade straw_tuft spiral_points tendril`, `drape seat place`, 2D outline ops (`offset_poly carve grin convex_shape`), `weighted_normals degenerate_count cleanup finish run`; themed `pumpkin_body stem pumpkin_leaf` | generic + produce |
| `dk_kit.py` | `team/characters_candy/batch03` | K | characters: `lathe sweep` (parallel-transport, profile warp), `stitches`, `bvh hit ring_on`, `look put`, `part` (merge at a joint), `attach` (parent without inverse) | generic for rigs |
| `foliage_common.py` | `team/foliage/batch03` | yard_common | leaf outlines (maple variants), leaf-card crowns, `bake_ao_shade`, `apply_shade_normals` (custom normals), `finish_foliage` | generic foliage |
| `cv_kit.py` | `team/candy_variety/batch03` | dk_kit | `decal`, `puffy` 2D-to-3D, `loft`, `lathe_rings`, star/heart/ghost/pumpkin outlines, scale-to-size `finish`, contact `render_tile` | parts generic; `finish` exports under `candy/` and writes `results/<id>.json` + `tiles/` next to the running build script |
| `mon_kit.py` | `team/monsters/batch03` | dk_kit, farm_lib | creature rigs (`part`, `rig`), face helpers (`eye_cute eye_glow smile cheek`), `bone plate seam`, `mirror_x`, `clip_below`, `g2b`/`b2g` axis helpers | face/rig helpers generic; `finish` exports under `monsters/` |
| `lm_common.py` | `team/landmarks/batch03` | yard_common | `stroke`, `rock`, `sector_slab`, `ribbed`, `ellipse`, `export_many` | generic |
| `decor_common.py` | `team/decor_ground/batch03` | yard_common, farm_lib | `flower_head`, `leaf`, `decal`, `surface_points`, `cull_inside`, `sit_on_ground`, `finish` | generic |
| `vine_kit.py` | `team/vines/batch03` | mon_kit | `curl taper wobble rope spines_on bud ground_root`, `finish_knot finish_parts` | tendrils generic; exports under `monsters/` |
| `car_kit.py` | `team/vehicles/batch03` | lm_common | profile-lofted toy car bodies, `fillet_outline`, wheels, lamps, plates; themed `jack hay_bale` cargo | vehicles |

Not ported: `pumpkin_lib.py` (v1 UV layout, superseded by farm_lib), `cc_helpers.py` (superseded by
dk_kit), `decor/batch03/decor_common.py` (themed lamp heads; its `raw()` duplicates yard_common).

## Game-specific assumptions left in

- Palette colour names used as defaults (`hedge`, `vine`, `stem_brown`, `dragon_teal`...) are
  trick-or-treat's. Calls with a name the game's palette lacks raise `KeyError`; pass your own names.
- Export categories hard-coded in some `finish()` helpers: `monsters/` (mon_kit, vine_kit), `candy/`
  (cv_kit). Others take the path as an argument.
- Command-line conventions (`-- ids`, `--nosheet`, `--lift`, `--stats`) come from the lane scripts.
- `review_sheet` scale post height/colour: settings `scale_figure_height_m` / `scale_figure_color`.

See `techniques/lowpoly-textured-style.md`, `sweep-lathe-uvs.md`, `character-kit-lowpoly.md`,
`foliage-crowns-lowpoly.md`, `vehicle-kit-lowpoly.md`, `thorn-vines-spines.md` for how these are used,
and `examples/trick-or-treat/` for two complete build scripts.
