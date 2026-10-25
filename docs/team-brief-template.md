# Team brief template

Copy into `<game>/art/team/BRIEF.md` for each art pass and fill in the angle-bracket parts. One brief
serves every worker; lane specifics live in the catalog `brief` fields. A real example:
`examples/trick-or-treat/BRIEF.md`.

---

```markdown
# Worker brief (<pass label, e.g. "v2: polished and textured">)

You are an art worker on **<Game>**, <one-sentence game description>. Art direction: <setting,
palette mood, lighting>. The bar: <style, e.g. "polished, toy-like 3D with soft rounded forms and
hand-painted textures">; reference games: <2-3 named games>. <Polish rule, e.g. "Low poly but
generous: detail where the eye lands (rims, seams, caps)">. <Hard limits, e.g. "Never scary.">

Scale: <hero> is <h> m tall; <door/step/other anchors>. Gameplay camera: <distance> m, <pitch> deg down.
Lighting the game ships with: <night / day>; judge colour and glow in that light.

Read first:
- `S:\Repos\art-pipeline\docs\quality-contract.md` and `docs\asset-conventions.md`
- the kit API: `S:\Repos\art-pipeline\kits\lowpoly\lowpoly_kit.py` (and `kits\lowpoly\README.md`)
- your lane's entries in `art/asset_catalog.json` (brief, triangle budget, sockets, parts)
- palette names: `<palette_out>/palette_cells.json`; materials: `art/materials/materials.json` and the
  contact sheet `art/materials/preview.png` (look at it)
- relevant techniques in `S:\Repos\art-pipeline\techniques\` (<list the ones for this pass>)
- the user's concept / target image: `art/review/concept/<file>` (a quality bar, not a style guide)

Context: <what earlier batches did; reuse their ideas, rebuild in a new batch folder>.

## Rules

- Work only in `art/team/<lane>/<batchNN>/`, plus your exports under `<models_out>`, sheets under
  `<review_sheets>` and previews under `<review_engine>`. Never edit the pipeline repo, the catalog
  (except via your lane's register script, if this pass allows it), materials, the palette (except your
  row via `tools/set_palette_row.py`), native code or Godot project files.
- Blender is headless only, from the game root:
  `& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python <script> [-- ids]`
- Engine preview (serialised by a lock, it may wait):
  `powershell -NoProfile -File S:\Repos\art-pipeline\engine\godot\review\asset_preview.ps1 -Id <id> [-Scene main]`
- Use the PowerShell tool (the Bash tool is broken on this machine). No git commits.
- If something in the shared tools blocks you, report it as a shared tooling change; do not patch it.

## Material guidance

- <surface -> material map, e.g. wood -> wood/planks, leaves -> leaves, cloth -> felt/denim/fabric>
- Projection: `cyl` for round/upright things, `sphere` for blobs, `box` for boards. Re-project after
  deforms or merges.
- Materials repeat in metres; tiny parts read best low-contrast or `flat`.
- Glow cells stay `flat`; check glow at night (bloom).
- Always bake AO after the final merge/parenting.

## Per-asset loop

1. Build it; spend the budget on silhouette, rims, seams.
2. Export + review sheet (shape check).
3. Engine preview: do materials read, anything stretched, too busy, too dark in game light?
   Check gameplay distance (`tools\review\distance_check.py`).
4. Revise: at least two passes, hero assets more. `python S:\Repos\art-pipeline\tools\gates.py <id>`
   must PASS.

## Hand-off

In your batch folder: `results.json` (`[{"id", "gltf", "sheet", "engine_preview", "tris", "gates",
"notes"}]`) and `CHECKPOINT.md` (built / weak / unresolved; see
`S:\Repos\art-pipeline\docs\lane-batch-workflow.md`). New techniques or tool ideas: list them in the
checkpoint under "For the pipeline" so root can write them back to art-pipeline. Final message: a
table of assets with tris and gate result, plus anything weak. Be honest.
```
