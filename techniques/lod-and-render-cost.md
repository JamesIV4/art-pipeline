# LOD, instancing chunks and render cost

## What it is

The measured rules XCOM used to decide triangle budgets, material counts,
MultiMesh chunk size, Godot LOD generation and which lighting features ship.
Every number below was measured, not assumed.

## Why

Art rules ("max 3 materials", "always generate LODs") were being written from
intuition. Two labs (perf lab 2026-10-02, in-game render sweep 2026-10-16)
replaced them with measurements and found the real costs were elsewhere
(unmipmapped textures, MSAA, depth AO), not in material count.

## How: the asset-side rules

- Triangle ceilings (not targets): static terrain/props <= 4,000, vegetation
  <= 6,000, articulated units <= 24,000. Justify exceptions.
- One consolidated mesh per static asset, few surfaces. Up to 5 authored
  materials per static asset is fine (measured); unlimited once the layered
  merge is live (see `layered-merges.md`).
- Movable parts keep pivots; deforming characters are one skinned mesh with
  <= 4 normalized weights.
- Godot import params for scenes: `array_mesh/deduplicate_surfaces=true`,
  `meshes/create_shadow_meshes=true`, `meshes/force_disable_compression=false`.
  `meshes/generate_lods` is a per-family decision (below).
- Textures: mipmaps on for every 3D texture (see `texture-compression.md`).

## How: the renderer-side rules

- Repeated terrain: one MultiMesh per (asset type, 8x8-tile chunk, level).
  MultiMesh culling is collective, so it must be spatially partitioned.
  4x4 -> 16x16 chunks cut CPU about 4x (as much as merging), but bigger chunks
  hurt tactical-zoom GPU through coarser culling (A 1.86 -> 2.26 ms). 8x8 is
  the balance. Destruction rewrites only that chunk's instance buffer.
- Per-tile MeshInstance3D (Forward+ auto-batching) does not beat chunked
  MultiMesh: culling ~20,000 instances costs more than it saves.
- Orthographic shadow cascades spread over camera near..far. With a 500 m far
  plane the tactical view got no visible shadows. Fit near/far to content depth.
- SSAO/SSIL fade by camera distance (Godot defaults fadeout 50 / 300 m). An
  ortho camera parked 250-359 m back loses AO entirely; XCOM set
  `rendering/environment/ssao|ssil/fadeout_from/to` to 2000 / 4000 m.

## Generated LODs: when to turn them off

Godot's generated LODs cracked seams of multi-tile pieces cut on tile planes
(radar dishes, UFO hull edges) and made concave faces self-shadow (the LOD'd
shadow caster pokes through the full-detail surface). XCOM imports those
families with `meshes/generate_lods=false` via `art/tools/scene_import_policy.py`
(port: `kits/xcom/`), keeping shadow meshes on. Cost of LODs off on the
heaviest maps: draws and CPU unchanged, GPU +0.05-0.2 ms at play zoom,
+0.4-1.3 ms whole-map. Compare tool: `art/review/renderer_lod/tools/compare_lod.py`
(dark outliers >= 40/255 darker = seam cracks or shadow blobs; heat map +
worst-cell crops). Default stays LODs on; turn off per family when the
comparison shows cracks.

## Lighting feature costs (in game, 1080p, RTX 5060 Ti, GPU ms delta)

| Setting | farmland | forest | urban fire night |
| --- | --- | --- | --- |
| MSAA off (from 8x) | -1.77 | -0.61 | -1.02 |
| depth AO off | -0.62 | -0.52 | -0.68 |
| shadows off | -0.45 | 0.00 | -0.56 |
| SSIL off | -0.25 | +0.04 | -0.44 |
| shadow filter Ultra | +1.01 | +0.19 | +0.25 |
| SDFGI on | +0.43 | +0.33 | +0.39 |
| TAA on | +0.39 | +0.24 | +0.26 |
| SSR on | +0.34 | +0.12 | +0.25 |
| shadow map 4096/2048/1024 | ~-0.05..-0.17 | ~0 | ~-0.15 |

Baselines 5.38 / 3.65 / 4.45 ms; noise 0.05-0.1 ms. Shadow map size barely
matters; filter quality and MSAA do. SDFGI and volumetric fog are camera-
centred and show almost nothing with a distant ortho camera.

## Gotchas

- Godot's draw count = visible + shadow list items; depth prepass is not
  counted separately.
- One machine under shared load: CPU varied 4.16-6.08 ms between runs. Run
  every variant 3x interleaved, >= 240 warm-up frames + 2 s, 600 measured
  frames, median of medians.
- Masked foliage merged into opaque costs GPU; keep it separate.
- Textures were the biggest GPU item: unmipmapped terrain textures; mipmaps +
  block compression cut tactical GPU 0.8-1.5 ms and memory 155 -> 104 MB.

## Source

- XCOM `art/review/perf_lab/REPORT.md`
- XCOM `docs/RENDER_COST_SHADOWS_LIGHTING.md`
- XCOM `art/tools/scene_import_policy.py` docstring, `art/review/renderer_lod/`
  (`compare.json`, `tools/compare_lod.py`)
- XCOM `docs/BATTLESCAPE_3D_INTEGRATION.md` (render debug panel, AO distance)
- XCOM `art/review/opus_revision_queue.md` (LOD policy, renderer phase 1)
