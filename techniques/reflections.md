# Neutral reflection sky and true-metal authoring

## What it is

A reflection-only environment (graded gray procedural sky feeding only the
radiance term) plus the authoring rules for metals that it enables: bare metal
is metallic 1.0 with a bright reflectance-colour albedo.

## Why

Metal rendered nearly black in XCOM because the environment gave it nothing to
reflect (navy background, ambient source = colour). Workers compensated by
faking chrome/steel/hull as low-metal satin (metallic 0.3-0.35, "dielectric so
the hull never reads black"). That hides the real problem and breaks once the
environment changes.

## How

1. `Environment.reflected_light_source = SKY` with a `ProceduralSkyMaterial`
   used ONLY for reflections; 128 radiance cube, no sun disc. Do not change
   exposure, tonemap, sun, ambient (still source = colour) or specular.
   Visible background unchanged.
2. Graded, not constant (sRGB gray): sky top 0.50, horizon (both sides) 0.42,
   ground bottom 0.25. A constant gray makes every flat metal face the same tone
   (a chrome box reads as a flat gray hexagon); the grade gives top faces a
   brighter reflection than walls and a horizon line on curved chrome.
3. Ship it on by default in every review tool; keep `--reflection-sky=off` and
   `--reflection-gray=<v>` for diagnostics; log
   `reflection_sky=0.5/0.42/0.25` per capture.

Measured (lab, mean probe luma before -> chosen): chrome sphere 7 -> 94,
brushed steel sphere 66 -> 114, brass sphere 57 -> 117; dielectrics shift
little (painted steel +2.1, concrete +1.0, white plastic +0.6, black plastic
+9.3); background identical. Constant 0.60 doubled the dielectric shift.
Real authored assets moved +1 to +2 luma (UFO hull/floor +5.7, the largest,
because of glossy dark dielectrics).

## Metal authoring rules

- Bare metal: metallic 1.0 (ORM blue 255), albedo = real reflectance colour.
  Paint, enamel, powder coat, rubber, dirt, rust, skin, hair, cloth: metallic 0.
  No in-between metallic except at worn transitions.
- Metal albedo is bright (sRGB): steel/iron 0.55-0.75 gray, chrome ~0.77,
  aluminium 0.85-0.95, brass ~(0.92, 0.80, 0.52), copper ~(0.95, 0.64, 0.54),
  gold ~(1.0, 0.86, 0.57). Never darken metal albedo to "look metallic"; a dark
  navy metal stays dark (XBASE handles 1 -> 26 luma).
- Roughness: polished/chrome 0.05-0.15, brushed/machined 0.3-0.45,
  worn/cast 0.5-0.7.
- Expect metal to read mid-tone (80-120 sRGB on lit faces), darker than white
  paint, top faces brighter than walls; the sun highlight carries sparkle.
- Glossy dark dielectrics (glass, screens, gloss black) gain a faint gray sheen
  at grazing angles (the correct F0 = 0.04 reflection). If a display must stay
  saturated, raise roughness to ~0.4 or rely on emission.
- Generated/scanned PBR sets often carry wrong metallic (Tripo face metallic up
  to 0.34, a global 0.25 on a power suit made faces and hair silvery). Mask
  metallic to real metal islands.

## Gotchas

- Dark leaves pick up gray sky glints too (foliage read lighter/grayer). Fix
  with a lower specular on foliage, not by raising leaf roughness to 0.8 (that
  washed them gray in a different way). See `foliage-cards.md`.
- A true-metal tin with a light sprite lid turns dark gray (the sprite lid was
  baked highlight). Accept or use a painted lid.
- Flat-topped glossy foliage (clipped hedges) turns any waxy roughness into long
  glare bars at game camera angles.

## Source

- XCOM `art/review/reflections/README.md` (+ `lab_measurements_*.json`,
  lab `xcom-3d-godot/labs/reflections/`)
- XCOM `art/WORKFLOW_RESEARCH.md` ("Reflective-metal review lighting")
- XCOM `art/team/ORCHESTRATION_OPUS55.md` ("Metals")
- XCOM `art/team/research/tripo_hands/GUIDE.md` section 8
- XCOM `art/team/environment_replacement/batches/urban_consistency_01/research.md`
