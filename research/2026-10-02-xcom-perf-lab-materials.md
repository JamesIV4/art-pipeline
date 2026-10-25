# XCOM 2026-10-02: perf lab, can static terrain use more than 3 materials?

## Setup

RTX 5060 Ti, Ryzen 7 9700X, Godot 4.7 Forward+ D3D12, 1920x1080, vsync off,
viewer camera/lighting/SSAO. >= 240 warm-up frames + 2 s, 600 measured frames,
each variant 3x interleaved, median of per-run medians. Scenes: the real base
defence map (60x60x2 tiles, 9,676 placements, 109 asset types; 82 stand-ins) and
a synthetic 64x64x2 mix with alpha foliage. "Full" = whole map, "play" = 30 m.
Variants: A = current viewer (4x4 chunks), C = shared identical materials,
D = one layered merged surface per asset, E = MeshInstance3D per tile; chunk
sizes 4/8/16.

## Key numbers (base map; draws / CPU ms / GPU ms)

| Variant | full | play |
| --- | --- | --- |
| A4 | 14,222 / 4.73 / 1.51 | 3,980 / 1.21 / 1.86 |
| A8 | 7,926 / 2.57 / 1.44 | 2,558 / 0.80 / 1.96 |
| A16 | 3,688 / 1.19 / 1.45 | 1,812 / 0.62 / 2.26 |
| C4 dedupe | 14,222 / 5.13 / 1.59 | 3,980 / 1.19 / 1.70 |
| D4 merged | 5,150 / 1.78 / 1.69 | 1,524 / 0.54 / 1.80 |
| D8 | 2,748 / 0.93 / 1.70 | 936 / 0.37 / 1.95 |
| A8 + mipmapped compressed tex | 7,926 / 2.72 / 1.16 | 2,558 / 0.77 / 1.02 |
| E (per tile, D meshes) | 833 / 1.38 / 1.64 | 563 / 0.47 / 1.68 |

CPU = 0.345 ms per 1,000 draw items (R^2 0.995).

## Findings

1. Material count is CPU only; GPU identical with LOD forced equal (3.82 vs 3.85).
2. Shadow pass does not merge surfaces (2,406 vs 914 shadow draws).
3. Bigger chunks hurt tactical GPU (coarser culling): 8x8 is the balance.
4. Per-tile auto-batching loses to chunked MultiMesh (culling cost).
5. Textures are the bigger GPU issue: mipmaps + compression halve tactical GPU,
   memory 155 -> 104 MB (base), 388 -> 159 MB (mixed).
6. Masked foliage stays separate (merging costs 0.13-0.19 ms GPU).
7. Merged arrays per size class; re-tints free; padding a 1261 px canopy to
   2048 cost 2.6x memory for that map.
8. A vs D visual difference 1.4-3.0/255 came from D's regenerated LODs.

## Decisions (user-approved)

- Now: up to 5 authored materials per static terrain asset; viewer to 8x8 chunks.
- With the layered merge: no per-asset cap; cap layers per family and texture
  sets (VRAM). Implement merge at import (EditorScenePostImportPlugin).
- Fit shadow near/far to content; mipmaps + compression on terrain textures.
Engine traps recorded: PackedColorArray to vec4[] double-linearises; shadow mesh
compression flag must match; ortho cascades over a 500 m far plane lose shadows.

## Caveats

Single machine under shared load (A4 CPU 4.16-6.08 ms run to run); 82 of 109
types stand-ins; lab D memory +20 MB because sources stayed loaded.

## Sources

XCOM `art/review/perf_lab/REPORT.md` (+ results.json, visual_stats.json).
