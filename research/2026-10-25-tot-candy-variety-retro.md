# 2026-10-25 trick-or-treat: candy variety batch retro (84 pickups)

Source: trick-or-treat art/team/candy_variety/batch03/CHECKPOINT.md, specs.py, cv_kit.py,
register.py, results.json, contact sheets in art/review/candy_variety/ (v1, v2, v3, final);
native/src/gen/candy_kinds.cpp; characters_candy batch02/03 CHECKPOINTs (classic candy).

## Scope and numbers

- 83 new floating pickups plus a lead follow-up (golden twist) = 84, in candy/, lane
  candy_variety, `floating: true`, `candy_tier`, `glow` (outline colour), brief.
- Tiers: 0 everyday 63 pieces, 500 tris, 0.24-0.34 m; 1 chocolate 10, 500 tris, 0.36-0.44 m;
  2 lollipop 7, 700 tris, 0.52-0.60 m; 3 golden 4, 700 tris, 0.50-0.52 m.
- About 50 parametric family builders from one spec table; one new palette row (15) with 12 candy
  colours; the 16-row palette grid became full.

## Iterations

- v1: all built, 9 over budget. Critique from contact sheets: decals sank into curved bodies
  (eyeball iris, bat/ghost prints invisible); puffy inset self-intersected on concave outlines
  (heart, ghost lollipop); candy-cane stripes stair-stepped; caramel coats hid apples; rock candy
  sparse; gummy worms thin; chocolate frog a brown blob; PB cups showed no wrapper.
- v2: puffy rim = outline scaled about its centroid; decals get edge subdivision; eyeball painted
  on a front-pole lathe; twisted-column tube for cane, coil, wand, fizz tube; coats moved up;
  chunkier rock candy; frog redesigned (white chocolate eye domes, pink cheeks, smile).
- v3: prints raised 22 deg toward the 30 deg camera and enlarged front and back; PB cups stood up
  so fluted wrappers show; finish() triangulates and drops zero-area slivers (3 degenerate-triangle
  failures fixed). All 83 pass.
- Golden twist: cream stripes were invisible on gold under the candy shader, so warm white stripes
  (2 of 18 columns each), darker crinkled foil ends (pleats x1.35), glowing knots and stars.

## Classic candy lessons (characters_candy lane)

- Wrapped candy at 120 tris looked crumpled; at 396 it holds. 18 sides suits three spiral stripes
  (columns 0-1 of every 6, rings twisted 8.5 x z); 12 sides put fan rim vertices on lobe peaks.
- White stripe on lemon has no contrast: lemon keeps a cherry stripe.
- User feedback v3.1: remove modelled highlights (shader gloss and rim already do it) and restore
  the stripes.

## Weak or unresolved

- The 12-piece twist family shares one silhouette; prints only front and back, so plain side-on.
- Flat pieces (coins, peppermint, belts, bars, lollipop discs) go edge-on twice per spin.
- Same-shape colour variants (3 gummy bears, 2 worms, 2 rings, 2 kisses, 2 coins, 2 rock candies).
- licorice_wheel is the only dark piece; reads purple-black and relies on its glow.
- Glow-cell pieces bloom heavily in studio light.
- Only 6 pieces were checked in engine; the rest only in Workbench contact sheets.
- Integration: the outline shader kept a 9-entry kind table, so catalog glow colours did not show
  until code read them; the game wired only 10 "iconic" variety ids into play.

## Takeaways

Budget distinct silhouettes per tier, not colourways; design spinning pickups to read from the
side; check a sample of every family in engine, not just contact sheets; ship the data path for
per-asset colours together with the art.
