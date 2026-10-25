# Review sheets and in-engine previews

## What it is

Three layers of visual review, cheapest first: a Blender Workbench four-angle sheet written by
every build (shape and tint check), an in-engine preview rendered through the real shader and
lighting (night and studio rows), and lane-made contact sheets, close-ups and line-ups for
comparing families and variants.

## Why

Headless agents cannot look at a viewport, and Workbench lies about materials and glow. Most real
problems (stretched textures, materials reading as the wrong thing, glow blooming, colours washing
out at night) only showed in the engine render. The cheap sheet still catches silhouettes,
proportions and missing parts in seconds.

## How

1. Workbench sheet, `K.review_sheet(objects, name)` (kits/lowpoly/lowpoly_kit.py): writes a
   "Preview" corner colour = palette tint (sRGB -> linear) x AO, renders 512 px ortho tiles from
   (yaw, pitch) = (-35, 20) front 3/4, (145, 20) back 3/4, (-90, 5) side, (-20, 35) gameplay pitch,
   with studio light, shadows and cavity, a navy world, and a 1.1 m scale post beside the asset.
   Composed 2x2 into `art/review/sheets/<id>.png`. Materials and glow do not show.
2. Engine preview, `tools/asset_preview.ps1 -Id <id>` -> `art/review/engine/<id>.png` (+ .log):
   imports changed models, then runs the game with `--preview=res://...gltf --capture=...` at
   1600x900. The asset stands on a 14 x 14 m lawn plot with a paver path (materials judged against
   real ground), toon material applied, no depth of field, player cutout off. Camera distance =
   bounds radius / tan(fov / 2) * 1.25. Tiles (800x450): night front 3/4 (yaw -0.6 rad, pitch
   0.38), night back (yaw 2.5), studio front (pitch 0.45), studio side (yaw -1.57, pitch 0.12).
   Night = moon 0.62 + warm omni (1.6 energy, orange); studio = key 1.3 + moon 0.25. Floating
   assets (bounds below 0) are lifted to 0.25 m above the lawn. Runs are serialised by a file lock
   (`godot_lock.ps1`) so parallel workers can preview.
3. Lane aids (review only, never shipped):
   - `close_sheet()` / `closeup()`: close front, gameplay angle and an unlit "night" render for
     judging glow cells; `view_gltf.py` / `view.py <gltf> <png> yaw:pitch:zoom:fx:fy:fz`
     renders any export from any angle (undersides, floating and hanging assets). Pass absolute
     output paths: relative ones resolve against Blender's cwd.
   - Contact sheets of a family (`contact_sheet.py <tag>`: tier rows, side view turned 90 deg,
     gameplay row shrunk to about 10 m size; monsters `contact.py out.png ids --far 15`).
   - Mock-ups: a Workbench porch with catenary string lights, bunting, wreath and lamps at near
     and 15 m (`porch_test.py`) to judge hanging decor in context.
   - Line-ups: temporarily export a trio over one id, preview it, rebuild (vehicles `lineup.ps1`).
   - Boards: candy row + concept crops + gameplay-size row on one image.
   - Crops: `crop.ps1` / `crop.py` 2x enlargements of preview quadrants.
4. Per-lane wrapper `go.ps1` / `run.ps1 <script> id1,id2 -Preview`: headless build, print RESULT
   lines, gate the built ids, preview each.

Judging checklist used in passes: do materials read as what they are; anything stretched; too busy;
too dark at night; too flat or washed out in studio; glow blooming over detail; specular glints on
leaves or chamfers; silhouettes from the back (the likely camera).

## Gotchas

- Studio row washes saturated teal and yellow to pastel; night row is the truth for colour. Lit
  tops of saturated foliage clip to pink under the low preview moon.
- The preview once dropped floating assets into the lawn (half-buried candy); it now lifts them,
  so stale `_lifted.png` workarounds are misleading.
- The engine can show only one asset: combined review exports need a flag and a clean rebuild.
- Godot re-import only follows .gltf changes; without the build stamp the preview shows old models.
- Candy previews render with the toon shader, not the in-game candy shader (self-glow 0.55, white
  rim): pale bodies may wash out further in game.
- Workbench sheets show glow cells as tan; never judge glow there.

## Source

trick-or-treat: art/tools/lowpoly_kit.py (`review_sheet`), tools/asset_preview.ps1,
tools/godot_lock.ps1, native/src/play/festival_game.cpp (setup_preview, step_preview), lane
CHECKPOINTs (decor, vehicles, candy_variety, pumpkins_farm batch01/02, yard_street batch02).
Distance checks: readability-at-distance.md.
