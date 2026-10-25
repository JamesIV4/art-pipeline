# Review gates

Two layers: cheap mechanical gates that any worker runs, then a visual gate by root in the engine.
Neither replaces the other. Details of the XCOM gate set: `techniques/independent-review-gates.md`.

## 1. Cheap gates (low-poly games): `tools/gates.py`

`python <pipeline>\tools\gates.py <id> ... | --lane <lane> | --all` (plain Python, reads the glTF).
Exit 1 on any failure.

| Check | Rule |
|---|---|
| exists | `<models_out>/<path>.gltf` present |
| budget | triangles <= catalog `tris` |
| palette | every Tint UV within 1/4 cell of a used cell's centre |
| material | layer index (integer part of UV2.x) within the materials spec |
| AO | COLOR_0 present whenever a Tint UV is |
| geometry | no degenerate triangles |
| ground | min height within `ground_tolerance_m` (3 cm) of 0 unless floating |
| structure | every catalog `parts` node and `socket_<name>` present |
| warning | untextured legacy export (no Tint UV) |

`publish_catalog.py` re-runs the gates and publishes only passing assets to the engine catalog.
`inspect_gltf.py <id> [cells]` reports bounds, sockets and which palette cells an asset uses.

## 2. Cheap gates (PBR / XCOM): `tools/review/root_independent_checks.py`

Sealed `render_dependency_sha256` matches; triangles only; POSITION, NORMAL, TEXCOORD_0, TANGENT
present and finite; unit normals/tangents within 0.01; tangent w = +-1 within 1e-3; |N.T| < 1e-3;
COLOR_0 in [0, 1]; no zero-area triangles (|cross|^2 <= 1e-22) or UV triangles (|det| <= 1e-13);
budgets (terrain 4,000, vegetation 6,000, items 12,000, units 24,000); static terrain one mesh and
<= 5 materials; `asset_id` extras match the catalog; import settings `deduplicate_surfaces=true`,
`create_shadow_meshes=true`, `force_disable_compression=false`. Also `texture_import_policy.py
--check`, and lane-specific gates (atlas cell containment, paired shells, winding number, plate edge
change <= 2%). `root_gate_batch.py` runs the whole batch flow (finalize textures, isolated diagnostic
catalog, import under lock, checks, four-angle captures, sheets).

## 3. Shape sheet (worker): Workbench 4-view

`K.review_sheet(objects, name)`: 2x2 at 512 px (front 3/4, back 3/4, side, gameplay pitch) with a
hero-height scale post; colour = palette tint x AO. Shape only: Workbench hides glow and painted
materials. See `techniques/review-sheets.md`.

## 4. Engine preview (worker and root)

`engine\godot\review\asset_preview.ps1 -Id <id>` -> `<review_engine>\<id>.png`, 1600x900, under the
Godot lock: top row night lighting (key light + warm omni), bottom row neutral studio. The night
row is the truth for colour and glow; the studio row washes colours toward pastel. Floating assets
are lifted 0.25 m. `-Scene main` uses the game's own preview mode instead.

## 5. Gameplay distance

`tools\review\distance_check.py <engine.png> <out.png> --px 70 [--concept-image ... --concept x0,y0,x1,y1]`
shrinks the subject to its on-screen height at play distance (trick-or-treat: ~70 px at 15 m on a
900 px screen) and enlarges it nearest-neighbour. Thin detail vanishes at distance; colours close to
the ground colour melt in. Scene captures: `engine\godot\review\review.ps1 -Seeds .. -Views ..`.

## 6. Root visual gate

One actual model beside its own exact source or concept crop; four quarter-turn angles under the
shipped lighting plus a game-zoom crop, after verifying the import is fresh. XCOM: 30 degree ortho
camera from the south-east, five assets per verified sheet. Any change needs fresh renders.
Outcomes: approve, or file in the revision queue with severity and evidence
(`lane-batch-workflow.md`).

## Freshness

Godot imports only when the `.gltf` changes: the kit stamps a build id. A capture proves freshness
when Godot's cached `source_md5` equals the current file's MD5 (`CaptureGodotReview.ps1` writes a
receipt with cache, DLL, exe, viewer and catalog hashes). File modification times are not proof.
