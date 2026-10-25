# Layered merge (one surface per static asset, texture-array layers)

## What it is

An import-time pass that replaces every opaque StandardMaterial3D on a static
terrain asset with ONE family-wide layered ShaderMaterial. Each distinct source
material becomes a "layer": a slice in shared albedo / normal / ORM / emission
Texture2DArrays plus a row of per-layer scalars (tint, roughness, normal
strength, emission mode, UV1 scale/offset). The layer id is written per vertex
(CUSTOM0.r), so the whole asset collapses to one opaque surface and one draw
per chunk per pass.

## Why

Measured in the XCOM perf lab (2026-10-02, RTX 5060 Ti, Godot 4.7 Forward+):
material count is a CPU-only multiplier (0.345 ms per 1,000 draw items,
R^2 = 0.995); GPU time is identical with LOD forced equal. Merging cut draws
2.8x (14,222 -> 5,150 whole-map) and made per-asset material count irrelevant,
with visual error 0.026/255 close-up (PSNR 62 dB). Sharing identical materials
without merging (dedupe) changed nothing, because Godot draws per surface.
Result: the per-asset "max N materials" art rule can be lifted once the merge
is live; budget layers and texture sets per family instead.

## How

1. Build a family manifest: scan the family's imported scenes, hash each opaque
   material signature (maps + factors), assign append-only dense layer ids.
   Cap 128 layers (`kMaxLayers` in `layered_merge.h` == `MAX_LAYERS` in
   `layered_terrain.gdshaderinc`; 5 vec4 tables x 128 = 10 KiB of uniform
   buffer, under the 16 KiB every backend guarantees).
2. Build Texture2DArrays per size class (next power of two >= the largest
   texture the family uses; upsample only, never downsample). XBASE used 1024^2
   (+ a 512^2 emission array), URBAN 2048^2.
3. Merge in `EditorScenePostImportPlugin::_pre_process` on the ImporterMesh, so
   Godot's own LOD, shadow-mesh and compression steps run on the merged
   surface: `surface_get_arrays`, append with CUSTOM0 = layer id
   (`ARRAY_CUSTOM_R_FLOAT << CUSTOM0_SHIFT` + compression flag),
   `ImporterMesh::add_surface`.
4. Switch scenes on with an import param (XCOM wrote
   `x3d/layered_revision="<layers>/<size>"`; the merge never reads it, it only
   forces a reimport when the manifest grows).
5. Refresh after every batch (root only, under the Godot project lock):
   import pending -> build family -> import arrays -> switch on -> merged
   import -> re-apply texture import policy. Exit codes: 0 fully merged,
   2 something left unmerged (listed), 3 an old layer id moved (never expected).

Implementation (XCOM): `native/src/layered_merge.{h,cpp}`,
`layered_merge_plugin.{h,cpp}`, shaders `assets/shaders/layered_terrain*`;
orchestration `art/tools/layered_refresh.py`, `layered_family_switch.py`
(port: `kits/xcom/`). GDScript prototype: `perf-lab/scripts/surface_merge.gd`.

## What stays a separate surface

- Alpha-masked foliage (merging saves 2-4% of draws but costs 0.13-0.19 ms GPU
  at tactical zoom).
- Blend-transparent glass, unshaded, triplanar and custom-shader materials.
- Anything whose signature is unknown or past the cap (logged as
  `kept[i]=over_cap` / `unknown_signature`, never silently dropped).

## Gotchas

- A PackedColorArray bound to a `vec4[]` uniform gets an extra sRGB->linear
  conversion. Pass PackedVector4Array.
- The merged shadow mesh must use the same vertex-compression flag as the main
  mesh, or depth/shadow geometry renders wrongly.
- The shadow pass does not merge surfaces by itself; only the import-time merge
  reduces shadow draws (2,406 -> 914 at tactical zoom).
- Runtime merge in GDScript cost 260-300 ms for 109 meshes including LOD
  generation; do it at import, not at load.
- Mipmaps for the arrays were built in sRGB, which dims high-contrast textures
  5-10% at distance. Build mips in linear if that matters.
- A naive runtime merge regenerates LODs with different triangle choices; that
  caused most of the 1.4-3.0/255 A-vs-merged difference. Merging pre-import
  fixes it.
- Layer ids are append-only. Raising the cap 64 -> 128 kept every old id, row
  and slice; verify with pixel-identical before/after captures.
- Re-tints of one texture set are free (just a new layer row). Separate texture
  sets cost VRAM per size class: a 1261x1247 palm canopy padded to 2048^2 cost
  2.6x memory for that map.

## Status at XCOM handoff

Live for XBASE1 (129 scenes, 61/128 layers, 11 slices, 1024 class; draws
541 -> 145 whole-map, PSNR >= 40.8 dB). Other families not yet built.

## Source

- XCOM `art/review/layered_merge/README.md`, `phase2_results.json`,
  `layers128_results.json`
- XCOM `art/review/perf_lab/REPORT.md`
- XCOM `art/tools/layered_refresh.py` (docstring)
- XCOM `art/review/opus_revision_queue.md` (renderer rows)
