# XCOM 2026-10-02: global lighting calibration (rejected) and neutral reflection sky (applied)

## Lighting calibration: measured, not applied

Question: can one global setting render sprite-coloured albedo at sprite
brightness? Lab reproduced the viewer bit-exactly; same face polygons sampled in
sprite and capture in linear light; pass-based predictor validated within 0.1
sRGB.
- Shipped lighting (sun 1.65, ambient 0.65, filmic, specular 0.5): lit faces
  1.84x the sprite (range 1.5-3.0), shaded faces 0.81.
- Fit: sun 0.75, ambient 0.45, specular 0.25 -> lit 0.99, shaded 0.38; specular
  change removed the gray veil on dark surfaces (black sRGB 48 -> 9).
- Specular sweep at shipped lighting: black tile 48 (0.5), 30 (0.35), 18 (0.25),
  0 (0); dark green (40,72,30) tile 83/123/61 at 0.5 vs 69/116/48 at 0.25.
Decision (user): keep brighter 3D lighting and darker real shadows. Rule:
modern lighting is expected to differ; no per-asset compensation; judge hue,
saturation, contrast and form. Per-asset albedo darkening already done (Sectoid
v3) was reverted.
Kept from the same renderer phase: 8x8 chunks keyed by level, shadow near/far
fit, mipmapped compressed textures, then the XBASE1 layered merge.

## Neutral reflection sky: applied

Problem: metal nearly black because the environment had nothing to reflect.
Tested constant gray 0.25 / 0.42 / 0.60 and graded skies in a lab with chrome,
steel, brass, dielectric probes.
- Constant gray flattens every metal face to one tone; a graded sky (top 0.50,
  horizon 0.42, ground 0.25 sRGB) keeps top faces brighter and a horizon line on
  curved chrome.
- Chosen probe lumas: chrome sphere 7 -> 94, steel 66 -> 114, brass 57 -> 117;
  dielectric shifts +0.6 to +2.1 (black plastic +9.3); background unchanged.
  Constant 0.60 doubled dielectric shift: rejected.
- Real assets: +1 to +2 luma (authored with almost no metallic texels); UFO hull
  + floor +5.7 (glossy dark dielectric floor, correct F0 0.04 sheen).
- Same assets with metal set to metallic 1.0: UFO hull 14 -> 39 luma; navy-
  albedo handles stay dark (metal albedo is reflectance and must be bright).
Decision: reflection sky on by default everywhere; metal authoring guidance
(metallic 1, bright reflectance albedo, roughness bands); satin fakes converted
when revisited. Side effect found later: dark foliage picked up gray glints ->
lower foliage specular (0.25) rather than retint.

## Sources

XCOM `art/review/lighting_calibration/README.md`, `lighting_calibration.json`,
`art/review/reflections/README.md`, `art/review/neutral-light-diagnostic-research.md`,
`art/team/ORCHESTRATION_OPUS55.md`.
