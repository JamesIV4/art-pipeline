# 2026-10-24 trick-or-treat: painted material texture pass

Retro of the pass that produced the 28 painted material layers (27 painted + `flat`) for the
textured low-poly look. Source: trick-or-treat art/materials/CHECKPOINT.md, materials.json,
source/*.provenance.json, art/tools/make_materials.py.

## Setup

- One shared style string plus a per-layer subject, generated with codex_imagegen.ps1 (Codex
  image_gen, one image per call, provenance sidecar per image).
- make_materials.py: resize 512, seam blend if needed, neutralise to mean 0.5, level contrast
  toward std 0.13, normals from luminance, texture arrays + toon.tres + C++ header + preview sheet.
- Result: 28 layers, 27 painted, 0 placeholders; materials.json unchanged by the pass.

## Results by layer (attempts, verdict)

- Excellent first try: stone, bark, leaves, burlap, scallop (exactly 7 rows), soil, lattice.
- Good first try: shingles (7 staggered rows), planks (5 + nail dots), brick (8 courses),
  asphalt, grass (slightly side-on tufts), hedge (busy at 1 m repeat), straw, felt (stitching
  stronger than "faint", fibres a bit realistic), paper (crinkle a touch realistic), stucco,
  fabric (plaid clearer than "faint", 2x4 repeats), cloud.
- OK: wood (source std 0.016 was boosted about 8x; grain streaky with dark knot "eyes"; strength
  0.6 softens it), concrete (joint line and speckles go dark and crisp after levelling).
- Needed a second attempt (5 of 27):
  - pavers: v1 3x3 grid; a half-tile offset is 1.5 cells so the seam blend made a ghosted double
    grid. v2 prompt "perfect 3 by 3 grid filling the tile ... half a gap along each outer edge",
    then np.roll by half a paver (209, 209) so edges fall inside stones; seam ratio 4.16 -> 0.48;
    a checker artifact at the old corner patched with a neighbouring grout crossing.
  - pumpkin: v1 about 3.3 ribs per tile (ghosted ribs). v2 "exactly 4 identical straight parallel
    ribs ... groove exactly at the left and right edges", rolled half a rib (157, 0). Faint
    brightness step on vertical repeat remains.
  - denim: v1 had a hard horizontal seam; v2 "one continuous uniform piece ... no seams, folds or
    lines". Clean but fine twill, least chunky, reads as diagonal hatch at distance.
  - metal: v1 faint mottled brush became purple blotches after levelling; v2 "soft horizontal
    brushed streaks running evenly across the whole tile". Streaky but fine at strength 0.4.
  - vinyl: v1 glossy tufted-cushion grid with baked specular that did not tile; v2 "smooth matte
    inflatable vinyl ... no tufted cushion grid, no shiny specular highlights".

## Findings

- The seam check (then `seam_ratio > 1.6`) fired on most structured textures even when they tiled.
  The half-offset blend is harmless when the pattern period divides half the tile and ghosts
  otherwise. Fix used: offset the source, keep the script. The current script (as ported) uses a
  2.2 threshold and crossfades only a 12% border band.
- Low-contrast sources (wood, concrete, metal, stucco, asphalt) were boosted 4-8x by the
  TARGET_STD levelling at the time; the current script caps the gain at 2.5 ("don't blow faint
  paintings up into streaks").
- siding (pre-existing) leaves short dark lip streaks mid-board after the blend; same half-board
  offset trick suggested.
- Bookkeeping that worked: rejected attempts in source/rejected/, unmodified output in source/raw/
  when post-processed, `postprocess` field in provenance.

## Later in-engine verdicts (from lane CHECKPOINTs)

- felt reads as fuzzy, crumpled terrycloth at kid scale; quilting invisible (characters lanes).
- fabric reads as plaid on ghosts/mummies; paper striped a skull; metal streaky on car panels;
  hedge read as pebbles on a bush. Lanes switched material per asset rather than repainting.
