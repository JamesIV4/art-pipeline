# Asset catalog schema

Each game has one authoring catalog (`catalog`, default `art/asset_catalog.json`) and one published
engine catalog (`published_catalog`, default `game/assets/catalog.json`) generated from it by
`tools/publish_catalog.py`. Sample: `examples/trick-or-treat/asset_catalog.sample.json`.

## Low-poly schema (trick-or-treat, the default for new games)

```json
{
  "comment": "Root-owned. Workers read only. collision: none | box | cylinder | trunk ...",
  "assets": [
    {"id": "pumpkin_round", "path": "props/pumpkin_round", "lane": "pumpkins_farm", "tris": 1400,
     "collision": "cylinder", "walkable": true,
     "brief": "Plump squat pumpkin 0.6 m wide, 0.45 m tall, 8 soft lobes, curly stem. Readable ridges."}
  ]
}
```

| Field | Required | Gate / consumer | Meaning |
|---|---|---|---|
| `id` | yes | all | unique asset id (snake_case) |
| `path` | yes | kit export, gates | export path under `models_out`, no extension (`props/x`, `candy/x`, `monsters/x`) |
| `lane` | yes | `gates.py --lane` | owning lane |
| `tris` | yes | budget gate | triangle budget |
| `brief` | yes | workers | the art brief: size in metres, colours (palette names), materials, origin, sockets, intent |
| `collision` | yes | game | `none` / `box` / `cylinder` / `trunk` (cylinder r=`radius`, h=`height` at origin) |
| `radius`, `height` | no (trunk needs them) | game | collider size in metres (trick-or-treat defaults: radius 0.2, height 2.0; box/cylinder colliders come from the model bounds, so in practice these matter for `trunk`) |
| `collision_top` | no | game | explicit walk height when the top is not the bounds |
| `walkable` | no | game | the top is a traversal platform (and may carry pickups) |
| `bounce` | no | game | launch speed in m/s (trampolines) |
| `floating` | no | ground gate | skip the ground-origin gate (hang point or centre origin) |
| `parts` | no | structure gate | required named child nodes (characters, creatures) |
| `sockets` | no | structure gate | required `socket_<name>` empties |
| `candy_tier` | game-specific | game | pickup value tier 0-3 |
| `glow` | game-specific | game, outline shader | `#rrggbb` outline colour |

The published catalog holds `{"assets": [...]}` with only `publish_fields` (setting) for assets
that pass every gate; the game falls back to placeholders for the rest. Game-specific fields such as
`candy_tier` go in `publish_fields` per game.

Rules:
- Lanes add or update only their own ids, in one read-modify-write (`tools/catalog_register.py`).
- Changing a budget is a catalog edit with a reason in the lane checkpoint; budgets end near 100%,
  so later fixes need a trade.
- Catalog data the engine must read (glow colours, tiers) needs the game code wired in the same
  change, or the art silently does nothing.

## Extended schema (XCOM, for reference-driven remakes)

Top level: `schema` (1), `scope`, `coordinates` (`tile_meters` 2.0, `level_meters` 2.4495 =
sqrt(6), `source_logical_level_meters` 3.0, `vertical_voxel_render_meters`, axis strings for Blender
and Godot), `source_files` (bytes + SHA-256 of each original data file), `assets[]`.

Per asset, grouped:

- identity: `id` (`terrain/<SET>/<NNN>`, `units/<FAMILY>`, items), `category`, `set`, `record`, `part`
- source: `source`, `reference_image`, `frames`, `reference_frames[]` (`pck_frame`, `kind`, `phases`,
  `path`, `pixel_sha256`), `frame_semantics`, `source_label`
- raw game data: `lofts`, `terrain_level`, `destroyed_record`, `alternate_record`, `big_wall`...
- model: `model`, `blend`, `model_source`, `metrics` (`triangles`, `mesh_objects`, `surfaces`)
- status: `status` (`pending`, `rejected_initial_draft`, `rebuilt_needs_native_review`,
  `rebuilt_needs_visual_review`, `rebuilt_reviewed`, `intentional_empty`), `rebuild_status`
- review: `quality_review` (`passed`, reviewer, details, `source_limits`), `export_integrity` (model and
  blend SHA-256 plus dependency hashes), `reference_review`, `texture_trials`, `godot_reviews`
- variants: `variants`, `selected_review_variant`, `legacy_model`
- natural terrain: `natural_terrain_work` (`base_status`, `material_status`, `detail_status`,
  `detail_models`, `review_status`, `task_index`)
- units: `direction_count`, `required_clips`, `footprint`, `armors`

Batch staging catalogs are written separately (`<batch>-staging.json`, `art_approved: false`;
diagnostic catalog `status: isolated_preview_unapproved`, `quality_passed: false`) so nothing unreviewed
reaches the shipped catalog. Tools that read this schema: `tools/review/xcom_publish_catalog.py`,
`root_independent_checks.py`, `validate_rebuilt_models.py`, `record_visual_review.py`.

Adopt the extended fields a la carte: a new game that rebuilds existing source art (a remake) wants
`reference_image`, `status`, `quality_review` and `export_integrity`; an original game usually needs
only the low-poly schema plus `status`.
