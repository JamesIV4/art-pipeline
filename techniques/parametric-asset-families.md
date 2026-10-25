# Parametric asset families (one spec table, many variants)

## What it is

Large sets of related assets (83 candy pickups in one batch) are produced from a single spec
table: id, tier, family, target size, glow colour, brief and family parameters. A Blender build
script dispatches each spec to a parametric family builder; a plain-Python register script writes
the catalog entries from the same table. Contact sheets per tier compare the whole family.

## Why

Hand-writing 80 build functions and 80 catalog entries drifts: briefs, sizes and budgets go out of
sync, and nobody sees the family side by side. One table keeps build, catalog and review
consistent, and family builders turn variety into parameters (colour, pattern, print, shape).

## How

trick-or-treat art/team/candy_variety/batch03:

- `specs.py`: `S(id, tier, fam, size, glow, brief, **params)` rows; e.g. twist family with
  `body=`, `fan=`, `pat="dots"|"bands"|"check"|"split"|"lstripes"`, `print="bat"|"pumpkin"|...`,
  `shape="log"|"pillow"`. Imported by both the Blender build and register.py.
- `build_variety.py -- [ids|tier0..3|family] [--sheet] [--notile] [--lift]`: about 50 family
  builders (twist wrappers with patterns and prints, lens discs, puffy outlines, lathes, sweeps,
  bars, lollipops, twisted-column tubes for canes and wands).
- `cv_kit.finish(parts, aid, size, tier, args, budget)`: merge, recentre on the bbox centre, scale
  to the spec size (longest side), triangulate and drop zero-area slivers, AO, export, render a
  tile, write `results/<id>.json` (`id, tris, budget, tier, dims`).
- `register.py`: builds entries `{id, path, lane, tris (by tier), collision: none, floating: true,
  candy_tier, glow, brief + size and origin note}`, updates existing ids in place, appends new,
  re-reads the catalog right before writing.
- Budgets by tier: everyday 500, chocolate 500, lollipop 700, golden 700 tris. Sizes by tier:
  0.24-0.34, 0.36-0.44, 0.52-0.60, 0.50-0.52 m.
- `contact_sheet.py <tag>`: tier0 grid, tier1-3 grid, side view (turned 90 deg), gameplay view
  (shrunk to about 10 m). Keep each version's sheets (v1, v2, v3, final) to see progress.

Iteration pattern that worked: build all, critique the contact sheets as a group, fix shared
causes in the family builders (decal subdivision, puffy rim scaling, twisted tubes), rebuild all.

## Gotchas

- Shared silhouettes: the 12-member twist family differs only by colour and pattern; same-shape
  colour variants (3 gummy bears, 2 worms, 2 coins) add count, not variety. Budget for a few
  distinct silhouettes per tier.
- Spinning pickups: flat pieces go edge-on twice per spin; prints on front and back only leave the
  side plain. Prefer chunky forms and prints visible from several sides.
- Puffy inset on concave outlines (heart, ghost) self-intersected; scale the rim outline about its
  centroid instead of offsetting.
- Dark pieces (licorice) rely entirely on their glow at night.
- Being in the catalog is not being in the game: only 10 iconic variety ids were wired into play,
  and the outline colours needed a code change to be read from the catalog.
- A finish step that triangulates and drops slivers fixed 3 degenerate-triangle gate failures.

## Source

trick-or-treat: art/team/candy_variety/batch03/CHECKPOINT.md, specs.py, cv_kit.py, register.py,
results.json, results/*.json; native/src/gen/candy_kinds.cpp (ICONIC list).
