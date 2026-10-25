# Independent review gates (cheap mechanical gate + root visual gate)

## What it is

A two-layer acceptance process: a cheap, automated, independent check that
re-reads every exported glTF itself (never trusting the worker's report), then
one visual gate by the orchestrator ("root") on fresh engine captures beside the
exact source art. Passing either layer is not art approval by itself; approval
is a separate catalog field set only by root.

## Why

XCOM saw: generic benchmark boxes labelled with a real asset id; sheets
showing two objects against one source; code fixes claimed but old renders
submitted; a Godot capture that used the previously imported mesh despite new
catalog labels (capture race); tangents "present" but zero; COLOR_0 present but
vertex albedo disabled in the live material; worker manifests whose positive
check was computed before a later step changed the geometry.

## Layer 1: cheap independent checks (run on every export, never removed)

XCOM `art/tools/root_independent_checks.py::check(asset_id, model)` (port:
`kits/xcom/`). Fails on:
- missing or mismatched `asset.extras.render_dependency_sha256` (uri + SHA-256
  of every external .bin and image), missing images;
- primitives not triangles; missing POSITION / NORMAL / TEXCOORD_0 / TANGENT;
- non-finite values; |normal| or |tangent.xyz| off unit by > 0.01;
  tangent w not +/-1 (1e-3); |N.T| > 1e-3;
- COLOR_0 outside [0, 1]; index out of range;
- zero-area triangles (|cross|^2 <= 1e-22) or zero-area UV triangles
  (|det| <= 1e-13);
- triangle budget: terrain 4,000, vegetation 6,000, items 12,000, units 24,000;
- static terrain not consolidated to one mesh, or > 5 materials;
- `asset_id` extras not matching the catalog id;
- Godot `.import` missing or lacking `deduplicate_surfaces=true`,
  `create_shadow_meshes=true`, `force_disable_compression=false`.
Info only: signed volume (cards/open shells are legitimate), generate_lods
value, missing .blend at the conventional path. Lane-specific gates add:
outward winding/closure where solid, paired shells, atlas cell containment,
modular-fit volume (`modular-fit-clipping.md`), per-pose morph vectors.

Seal before hashing: `seal_model_versions.seal(path)` writes the dependency
hashes into the glTF so a changed sidecar changes the scene hash (Godot then
reimports). Seal after every texture rewrite.

## Layer 2: root batch gate (one per batch of ~10 assets)

`python art/tools/root_gate_batch.py --batch <name> --models ids_models.json`
(`[{"id": "terrain/URBAN/050", "model": "xcom-3d-godot/.../050.urban23-opus-v1.gltf"}]`):
1. Finalize pending textures (WebP) before taking the lock.
2. Under the exclusive Godot project lock: write an isolated diagnostic catalog
   (`assets/review_diagnostics/<batch>/catalog.json`, status
   `isolated_preview_unapproved`), a staging record (`art_approved: false`,
   `main_catalogs_unchanged: true`), import headless, re-apply texture policy,
   re-import if it changed anything.
3. Run layer-1 checks -> `<batch>-root-checks.json`.
4. Capture four native angles per asset (quarter turns from the 30 deg review
   camera) with `CaptureGodotReview.ps1`, which refuses to capture unless: seals
   match, every model/texture has an imported cache whose `source_md5` equals the
   current source MD5 (mtime is not freshness), and it records cache SHA-256,
   native DLL hash, Godot exe hash, viewer source hash and catalog hash in a
   runtime receipt. It also audits live material flags (alpha scissor, cull,
   vertex albedo) and actual loaded triangle count/bounds.
5. Contact sheets of 5 assets each: exact source sprite (enlarged, nearest) +
   four engine angles (`<batch>-<n>.png`); partial recaptures get their own name.
6. Root inspects sheets under the normal game light; approves adequate assets,
   files concrete revision rows for weak ones (`revision-queue` pattern).
Optional fixtures: neutral lighting, reflection gray, instanced patch, corner
pairs, ground context, exact map layouts. Use only for a real risk.

## Comparison identity rules

- Each trial persists exact asset_id, actual source frame(s), construction and
  material candidate in a manifest; the sheet's source column is generated from
  that manifest, never a hard-coded representative.
- One actual model beside its own source; no mixed objects, no generic
  material benchmarks carrying an asset id.
- Any change (colour calibration, UV crop, material, geometry) needs new
  renders; old images never validate a new derivative. Mechanical proofs may be
  reused only inside a frozen unchanged batch.

## Isolated labs instead of the main project

Workers never import into the shared project (concurrent imports corrupt
`.godot`). For runtime behaviour use isolated labs that copy the viewer's
camera/lighting (perf lab, unit lab, reflections lab), with byte-identical
asset copies (SHA-256 verified). A lab report gives numbers, a contact sheet and
porting notes; it never edits the deliverables.

## Gotchas

- "Equal declared route arrays" or "local normal consistency" do not prove
  contact or outward winding; test the final mesh.
- Data presence is not rendered-material proof (COLOR_0 vs vertex-albedo flag).
- Capture only after import completion; compare source MD5 to cache digest.
- Do not run "nothing broke" regression passes for every change (XCOM user
  rule 2026-10-07): test the new feature only; the cheap gates still run.

## Source

- XCOM `art/tools/root_independent_checks.py`, `root_gate_batch.py`,
  `CaptureGodotReview.ps1`, `seal_model_versions.py`, `godot_main_lock.py`
- XCOM `art/review/environment-worker-audit.md`
- XCOM `art/review/workflow_snapshots/20260930-strict-TEAM_REQUIREMENTS.md`
  ("Additional comparison identity gate")
- XCOM `art/TEAM_REQUIREMENTS.md`, `art/team/ORCHESTRATION_OPUS55.md`
- XCOM `art/review/unit_lab/sectoid_opus-v2/REPORT.md`, `perf_lab/REPORT.md`
