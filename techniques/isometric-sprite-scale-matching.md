# Matching 3D scale and camera to isometric 2D source sprites

## What it is

The derivation and checklist for rebuilding 2D isometric sprite art in 3D so
that a physical orthographic camera reproduces the original projection: render
metres per tile and per level, axis conventions across game / Blender / Godot,
pixel aspect, unit heights, and a source-camera overlay render.

## Why

XCOM's first models used the original "3 m logical level" as physical metres,
which vertically distorts everything under a 30 deg camera (2.4 m walls with a
3 m stacking gap). Item sprites read with square pixels made every weapon 1.5-2x
too fat. Mirrored axes put north walls on the south edge.

## How: the projection derivation

- Source projection (OpenXcom `Camera.cpp`): screen x = 16(x - y),
  y = 8(x + y) - 24z, in logical tile/level indices.
- Choose a physical tile (2 m) and an orthographic camera at 30 deg elevation,
  azimuth 45 deg. Horizontal pixel density = 16 / (2 cos 45) = 11.3137 px/m;
  vertical = that x cos 30 = 9.79796 px/m. So a 24 px level is
  sqrt(6) = 2.44949 m and one vertical voxel (1/24 level) = 0.1020621 m.
  This is 0.81650 x the 3 m logical level.
- Keep raw source metadata (24 voxels, 3 logical m) separate from render metres;
  use the corrected pitch for stacked walls, ramps, crowns, level offsets.
- Character height = standHeight voxels x sqrt(6)/24 (soldier 22 -> 2.2454 m,
  Sectoid 16 -> 1.633 m). Item real lengths scale by ~1.25 at that height.
- Stairs: exactly 5 steps per tile, so a two-tile flight climbs one level in 10
  risers of sqrt(6)/10 m.
- Source pixel shapes override conservative collision volumes for visible
  proportions; collision (LOFT) is a guide only.

## How: axes (write them in every catalog)

- Game map: X east, Y south. Blender: X east, +Y north, Z up (reflect map Y).
  Godot/glTF: X east, Y up, -Z north. Tile origin at the centre, walking surface
  at 0.
- Unit facings: 8 clockwise, 0 = N; Godot `rotation.y = -45 deg x d`.
- Terrain animation frames are phases in a fixed camera, not facings; separate
  records may be orientations, damage states or neighbouring sections.

## How: reading sprites

- Enlarge 4-9x nearest-neighbour before deciding anything; read colours as
  families, not pixels.
- Use the largest available art (inventory/encyclopedia images, e.g. 320x200
  SPK with the right palette) as the design target; the battlescape sprite stays
  the authority for silhouette and colour. Sprites exaggerate heads (39% vs 31%).
- Measure, don't eyeball: classify foreground by hue and print row widths;
  1 px = height / figure px.
- Pixel aspect: 320x200 displayed at 4:3 means a sprite pixel is 1.2x taller
  than wide. Muzzle-up item art: length = rows x 1.2; lying-down art: height =
  rows x 1.2. With 1.2 the three independent item views agree.
- Multi-tile objects: composite the actual map placements in draw order before
  modelling; a sprite often draws its part offset from its own tile.

## Source-camera check render

Orthographic, 30 deg elevation, azimuth from SE, 0.0884 m per sprite pixel,
target (0, 0, sqrt(6)/2) so the render overlays the 32x40 sprite exactly
(sprite x = 16 + 11.31 P, y = 32 + 5.657 Q - 9.80 z). Score silhouettes with IoU
against the sprite enlarged 10 x 12 for items.

## Gotchas

- Unseen sides are interpretation; never present them as observed.
- Record identity (MCD record) is not frame identity (PCK frame); keep both.
- Zero-based raw offsets vs one-based field docs: use named offsets and one
  canonical decoder.
- A tool's E/W mirrored (previewer compass drew E at -X); verify every tool's
  axes against the game once.
- Modern lighting makes absolute luminance comparisons meaningless; compare
  silhouette, proportion, hue relationships.

## Source

- XCOM `art/WORKFLOW_RESEARCH.md` ("Source projection versus visual meters")
- XCOM `art/README.md`, `art/TEAM_REQUIREMENTS.md` ("Coordinates")
- XCOM `art/team/items_opus55/research.md` (pixel aspect)
- XCOM `art/team/units_opus55/ALIEN_HUMANOID_TIPS.md` section 1
- XCOM `art/team/terrain_rebuild/opus_batch01/research.md` (source-camera render)
- XCOM `art/asset_catalog.json` `coordinates` block
