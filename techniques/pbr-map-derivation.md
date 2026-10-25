# PBR map sourcing and derivation (albedo, normal, ORM)

## What it is

How XCOM obtained and processed the runtime PBR set for every material:
where albedo comes from, how normal/ORM maps are derived or baked, how region
masks are composed per texel, and the honesty rules for resolution and scale.
(AI image generation itself is covered in `ai-texture-generation.md`.)

## Why

Early workers used crude generic noise presets, claimed "native 2k" detail from
resampled 1254 px images, stretched square maps around cylinders (zinc can read
as wrinkled fabric) and repeated photographed board joints along continuous
rails. Procedural shader graphs also do not survive glTF export.

## How: source priority (user-final 2026-10-02)

1. Free CC0 PBR sets (Poly Haven, ambientCG, TextureCan, Kenney) from a shared
   local library, each set with `provenance.json` (URL, licence, date, file
   hashes). Workers never download; root fetches on request
   (`art/tools/fetch_cc0.py ambientcg Metal032 --res 2K`). Regrade toward the
   source colours; processed maps get new names.
2. Image generation for what scans cannot match (decals, signage, goods prints,
   creature skin, blood, leaf cards with transparency). Keep a provenance sidecar.
3. Procedural last: utility masks, normal/ORM/height derived from albedo,
   gradients, or when both above fail (record why).
Generated/downloaded images never override the source art.

## How: conventions every map obeys

- Albedo sRGB; normal tangent-space OpenGL (+Y green up), Non-Color; ORM
  Non-Color with R = AO, G = roughness, B = metallic (glTF occlusion wired too).
- Principled BSDF with image-backed inputs only; procedural nodes are baked.
- Share images, vary factors: a Mix/Multiply node with factor 1 and constant B
  exports as `baseColorFactor`, so meadow/jungle variants share one image.
- 8-bit WebP at runtime (see `texture-compression.md`).

## How: derivation recipes

- Image-derived normal: low-amplitude, approximate micro-relief from albedo
  luminance; label it approximate (not scanned, not high-to-low).
- ORM from scratch: AO from coverage/cavity, roughness from material class
  (see `reflections.md`, `foliage-cards.md` for ranges), metallic 0 except real
  metal.
- Seamless tiles: offset + heal, then always inspect a 2x2 repeat.
- Periodic boundary repair: repeat alone cannot fix source edge discontinuity.
  Blend half-period-shifted samples only near boundaries, bake colour at native
  resolution, re-bake approximate normals; compare widths (6%, 10%, 16%) for seam
  suppression vs ghosting. Runtime keeps two samples, not the authoring 4 taps.
- Per-texel composition (best for crisp source-led regions): bake per asset,
  into its own atlas, coverage + object-space position (enc = P*0.15+0.5 in a
  float buffer) + object-space normal + each scan's albedo/ARM (EMIT bakes, no
  lights) + tangent normal; then compute masks (snow, ash, colour bands) in numpy
  from baked position/normal and fBm, and mix layers (normals: weighted sum,
  renormalised, same tangent frame). No COLOR_0 runtime dependency.
- Mesoscopic detail (snow aggregate, clasts): Voronoi/Noise in metre
  coordinates with modest domain warp, bump-only 1.5-3 mm relief, baked to
  normal/ORM. Changes shading, not silhouette.
- Directional wood: sample a bounded region inside one board (no repeated board
  joints along a continuous rail), bake sawn ends separately; XCOM got ~683
  longitudinal texels per 2 m rail. End grain is its own small baked map.
- Cylinders and lathed parts: maps authored for the measured circumferential
  and vertical physical periods, not a square map wrapped around.
- Neutral scan carrier + bounded COLOR_0 tint when a coloured carrier would
  clip the target hue (pink on a gold carrier lacked blue).

## Honesty rules (recorded per material)

- Native resolution, physical repeat and any resampling/compression of scale
  (e.g. a 2.16 m scan remapped to 2 m = 7.4% compression) are written in the
  provenance. No "native 2k per quadrant" claims for a 1024 crop in a 2048 atlas.
- Image-generation output is ~1254 px; say so.
- A sprite is never upscaled and offered as a near-view material.

## Gotchas

- Bake margin type EXTEND, not ADJACENT_FACES, when photo UV islands overlap or
  fold (adjacent-face margins pulled garbage positions in).
- Put the geometry/depth version in the bake cache key, or changed normals reuse
  stale maps.
- Triangulate BEFORE baking normals; triangulating after bakes on a different
  split, and quads make the glTF exporter drop TANGENT.
- `Image.pixels` of a byte sRGB image returns encoded values. A numpy UV-space
  raster must flip rows (row 0 = top, v = 0 = bottom); exported glTF v = 1 - v.
- Regular procedural bands bake as moire rings; use noise.
- An ORM gate must sample the texels the mesh actually uses; a whole-image mean
  failed stairs because a shared atlas held an unused metal latch cell.
- Uncalibrated scan selections followed by palette-shifted derivatives invalidate
  the old comparison sheets; re-render after any calibration.

## Source

- XCOM `art/WORKFLOW_RESEARCH.md`
- XCOM `art/team/ORCHESTRATION_OPUS55.md` ("Texture source priority")
- XCOM `art/team/terrain_rebuild/opus_batch01/research.md`,
  `research/mesoscopic-material-pilots.md`, `research/coverage-first-workflows.md`
- XCOM `art/team/environment_replacement/research.md`, `root_gate_feedback.md`
- XCOM `art/team/units_opus55/HUMANOID_UNITS_WORKFLOW.md` 12c
- XCOM `art/team/stairs_opus/batch01/research.md`
- XCOM `art/texture_research/*/provenance*.json`, `art/dossiers/*.json`,
  `art/tools/fetch_cc0.py`
