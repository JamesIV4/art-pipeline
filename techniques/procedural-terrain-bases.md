# Procedural natural terrain bases with separate detail attachments

## What it is

Natural ground (flat ground, hills, slopes, water surfaces, ice blocks) is not
modelled per tile. One base mesh is generated per source-derived SHAPE profile,
cached at runtime, and shared by every tile identity and biome with that shape;
biomes differ only by material. Raised features (rocks, bones, grass clumps,
branches, floes) are independent reusable detail scenes registered per tile.

## Why

XCOM had 280 natural tile identities but only 67 distinct shapes (117 of them
flat). Sculpting and exporting each tile was slow, inconsistent across biomes,
and cosmetic mesh deformation broke shared boundaries. Collision data was also
being mistaken for an exact silhouette.

## How

1. Decode the source shape data (XCOM: 62-byte MCD records + LOFTEMPS voxel
   slices + standard MCD patches; `T_Level` signed). Recognise monotone ramps
   and exact quantised corner patterns as continuous surfaces; other contours use
   a deterministic smoothed height field. Walking height alone does not identify
   a slope; collision volumes are conservative, not the sprite silhouette.
2. Generate and cache one base per shape (`art/tools/natural_terrain.py` offline,
   `scripts/natural_terrain.gd` at runtime, time-sliced ~6 ms per frame). No
   per-tile or per-biome glTF.
3. Keep shared boundaries exact and ice sides flat/planar. Grain, fissures,
   snow marks and wear go into albedo/normal/roughness or shader relief, never
   unique mesh deformation. Future displacement must preserve shared boundaries.
4. Materials: an appearance manifest picks top/side resources per base;
   explicit choices outrank legacy extraction. Store materials once by content.
5. Details: register in `natural_terrain_details.json`:
   ```json
   "terrain/DESERT/027": [{"scene": "res://.../rock_cluster.tscn",
     "surface_anchor": [0.3, -0.2], "height_offset": 0.0,
     "rotation_degrees": 45, "scale": 1.0, "enabled": true}]
   ```
   Anchor = Godot X/Z metres in [-1, 1]; Y follows the generated surface plus
   offset. Each tile has its own `Details` container; attachments never alter or
   duplicate the base; MultiMesh preview keeps attachment transforms and material
   overrides separate from the cached base.
6. Track three states separately in the catalog (`natural_terrain_work`):
   `base_status`, `material_status`, `detail_status` (+ `detail_models`) and
   `review_status`, with a generated work queue listing exact references, frames,
   existing candidate models to reuse, and ambiguous raised marks.

## Validation

- Unit tests on the decoder (`test_natural_terrain.py`).
- `build_shared_natural_terrain.py --check` (holds the project lock): every
  profile/tile, shared mesh identity, winding, planar sides, attachment placement
  and packing.
- Visual check of changed materials in actual Godot views and joins; water
  animation and shore masks where relevant. Coverage is not approval.

## Workflow ownership

Workers deliver only material choices (with provenance and source scale) and
attachment scenes plus proposed detail entries. Root owns the material source
inputs, the generator, catalog publication and locked imports. Durable choices
live in source config/generator code; generated manifests are ignored outputs,
never hand-edited. A retire tool archives obsolete per-tile models (backups
outside the repo, keeps any still referenced by review catalogs).

## Gotchas

- Raised natural objects authored with their own slab double-draw over an
  existing floor; hide the slab only when its top sits at the floor.
- Some "raised" marks are actually fissures or crevasses (dark lines grading to
  openings): they need material/decal work, not an attachment.
- Regenerating materials can restore obsolete pending detail tasks; reconcile
  resolved tasks with registered scenes before publishing.
- Do not export another ground block when making an attachment.

## Source

- XCOM `art/README.md` ("Procedural natural terrain")
- XCOM `art/TEAM_REQUIREMENTS.md` ("Natural terrain: procedural bases and
  separate details")
- XCOM `art/team/ORCHESTRATION_OPUS55.md` ("Natural terrain assignments")
- XCOM `art/review/opus_revision_queue.md` (DESERT 004/005, POLAR crevasse rows)
- XCOM `docs/GROUND_MATERIALS.md` ("Slope relief" slab rule)
