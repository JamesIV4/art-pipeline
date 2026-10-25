# Thorn vines, curls and spines (organic tendrils at scale)

## What it is

A helper set for bramble-like organic shapes: tapered bark tubes along smoothed control paths
ending in fiddlehead curls, rope-lobed twisted cross-sections, hundreds of thorn spines scattered
in golden-angle steps and merged into one mesh, buds and a few leaves. Used for thorn knots (about
3300 tris) and a 4 m thorn root mass around a pulsing heart (about 8900 tris).

## Why

Vines must read as a hazard (bristling, dark) but stay cute (curled, rounded, bone-white thorns),
and they appear many times per level, so they had to be built from a few parametric pieces with a
predictable budget.

## How

trick-or-treat art/team/vines/batch03/vine_kit.py (on mon_kit -> farm_lib + dk_kit):

- Paths: `smooth(ctrl)` Catmull-Rom; `curl(p0, t, nrm, R0, turns=1.1, n=9, shrink=0.78)` a
  shrinking spiral; `with_curl()` appends a curl to a path; `wobble()` adds a travelling wave;
  `taper(pts, r0, r1, power, swell)`.
- `stem()`: tapered bark tube, `hedge_dark` base with twisting `vine` and `pine_deep` stripes (sweep
  side colours), twist 0.3; `rope(j, sides=9, lobes=3)` gives a lobed section so several strands
  read as one braided trunk.
- `Spines`: every spine of an asset in one bmesh; a spine is a 6-sided cone (5-sided under 0.3 m)
  with an open buried base, `trim_white` shaft and `cream` tip. `spines_on()` scatters them along a
  stem in golden-angle steps every 0.24-0.36 m, biased outward and upward.
- `bud()` (glow_purple bud with three sepals), `leaf()`, `ground_root()` (roots hug the lawn, then
  rise).
- `finish_parts()`: an empty root with `roots` and `heart` children; the heart (pulsed by the game
  around its origin, translation [0, 1.5, 0]) gets its own AO bake so the cage does not dim it.

Silhouette ideas that read: corkscrew spire of four twisted stems splitting into crozier hooks;
bramble dome of low arches diving back into the ground; a shepherd's crook with companion stems
curling the other way; neighbouring roots twisting in opposite directions; crown curls angled
partly tangential so none reads as a bare stick edge-on from the front.

## Gotchas

- Pale stems read as birch; a dark base (hedge_dark) fixed it. The bark material's furrows still
  make stems read like branches up close.
- The first spines were flat 5-sided shards and did not read as thorns; fuller 6-sided cones did.
- `lolly_white` spines read pink at night under warm light; `trim_white` held, though spines still
  pick up a lavender cast near warm lights.
- A straight-trunk tepee read as a structure, not a growth; woven, ground-hugging roots fixed it.
  Knot roots can still read as tripod legs.
- Authored at final size: the game scaled the old knot by 1.7; the new mass needs scale 1.
- Very small leaves do not register; that is acceptable when the brief asks for few.
- Budget levers: catmull density, smaller spines 5-sided, fewer spill spines, footprint pulled in.

## Source

trick-or-treat: art/team/vines/batch03/CHECKPOINT.md and vine_kit.py, monsters/batch03/mon_kit.py,
art/review/vines_before/ (comparison captures).
