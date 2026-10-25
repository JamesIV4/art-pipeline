# XCOM 2026-10-02: renderer phase 1 (chunks, shadows, textures) and the LOD study

## Phase 1 changes applied to the native viewer

- MultiMesh chunks 4x4 -> 8x8 keyed by level (perf lab recommendation).
- Orthographic shadow near/far fitted to content depth; cast shadows became
  visible at tactical zoom (`--shadow-fit=legacy` kept for diagnostics).
- All 1,395 project textures VRAM-compressed with mipmaps (BC5 normals) via the
  texture import policy and project importer defaults. (From 2026-10-03 the
  policy file moved to Lossless + mipmaps alongside the WebP finalizer; see
  technique `texture-compression.md`.)
- Global lighting calibration measured but reverted by the user.
- Phase 2 the same day: XBASE1 layered merge live (109 scenes, 59 layers,
  PSNR >= 40.8 dB, whole-map draws 541 -> 145; later 129 scenes / 61 of 128).

## LOD study

Problem: Godot's generated LODs cracked seams on multi-tile pieces cut on tile
planes (radar dish 000-008, large radar 009-012, UFO hull edges) and made
concave faces self-shadow (the LOD shadow caster pokes through the full
surface).
Method: paired LOD-on / LOD-off captures per scene; `compare_lod.py` masks the
UI panel and reports mean abs diff on content pixels, pixels > 32 diff, dark
outliers (>= 40/255 darker: cracks or shadow blobs), bright outliers, worst
40 px cells with 4x crops. Example: culta07 mean 0.193, 214 bright outliers;
desert09 play 0 outliers; jungle05 20 dark / 42 bright.
Cost of LODs off on the heaviest maps: draws and CPU unchanged; GPU +0.05-0.2 ms
at play zoom, +0.4-1.3 ms whole-map.
Decision: STOPPED by the user mid-way. `scene_import_policy.py` sets
`meshes/generate_lods=false` (shadow meshes stay on) only for XBASE1, XBASE2,
U_EXT02, U_BITS, UFO1. No project importer default (tried, rolled back), so new
files in those families import with LODs on until the script is re-run. The
independent gate reports generate_lods as info only.

## Sources

XCOM `art/review/opus_revision_queue.md` (renderer DONE row, LOD policy row,
layered merge follow-ups), `art/tools/scene_import_policy.py` docstring,
`art/review/renderer_lod/tools/compare_lod.py`,
`art/review/renderer_lod/captures/repro/compare_lodon_vs_lodoff/compare.json`,
`art/review/lighting_calibration/README.md`, `art/review/layered_merge/README.md`.
