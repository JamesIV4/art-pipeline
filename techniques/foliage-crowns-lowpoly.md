# Low-poly foliage crowns from leaf cards

## What it is

Tree crowns and bushes built from hundreds of small closed leaf-outline cards (no alpha) placed on
the exposed surface of a union of ellipsoid "lobes", with custom split normals so the crown shades
as a few soft masses while its silhouette breaks into leaves, analytic per-leaf AO, an inner shell
of large dark cards and a "shadow-only" filler core.

## Why

Smooth lumpy blobs with a leaves texture read as balloons, cauliflower or "brains" (one toon
specular per blob). Big cards read as paper stars. The concept called for lush, full, leafy maples.
The user also preferred the original full, low crown volume over a thinner concept-like umbrella,
so form and leaf look were tuned separately.

## How

trick-or-treat art/team/foliage/batch03 (`foliage_common.py`, `build_maples.py`):

1. Lobes: about 20-26 ellipsoids spread over a whole crown ellipsoid (directions down to z
   -0.55) so lobes bulge out and down and the crown bottom sits low (crown bottom about 3 m on a
   5.6 m tree). Keep a clearance volume free for the low branch and its socket (swings, lights).
2. Placement pool (`surface_pool`): Fibonacci directions on each lobe at a density per m^2
   (outer skin 24, inner shell 6), radius factor jittered (outer 0.92-1.03, inner 0.74-0.86),
   culled if inside another lobe. Record the lobe normal and a crevice metric (distance to the
   nearest other lobe).
3. Cards (`Acc.leaf`): outline in the card plane, cupped along the midrib (cup 0.14), slight
   droop. Outer skin about 725 cards of 0.34 m; inner shell about 215 cards at 1.9x size in deep
   colours. Serrated 14-point maple outline only on the silhouette (|lobe normal z| < 0.22 or
   poking), cheaper 10-point outline face-on. 6% of cards poke out by 0.35 card size.
4. Single-sided unless needed: a card lying on the mass only ever shows its outer face. Only
   poking or strongly tilted cards (dot < 0.78) are double-sided. Roughly doubles leaf count for the
   budget.
5. Shading normals: outer `0.82 * lobe_n + 0.18 * crown_n + noise`; inner `0.7 * lobe + 0.3 *
   crown`. Written as custom split normals (`normals_split_custom_set_from_vertices`), exported to
   glTF: one toon terminator per mass.
6. Analytic AO per card: `(0.45 + 0.3 * (lobe_nz * 0.5 + 0.5) + 0.25 * height01) * (1 - 0.4 *
   crevice)`, floor 0.32; inner cards 0.36-0.5; trunk below fork + 0.6 m at 0.6x. Ray AO speckled.
7. Tint ramp: 4 steps (deep, dark, main, light) chosen by `e = 0.62 * lobe_nz + 0.5 *
   (h01 - 0.5) + per-lobe offset - 0.4 * crevice`, plus 3-4% accent cards from a neighbour hue.
8. Filler core: an ellipsoid at 0.6x crown radii with a fixed downward shading normal and AO 0.35,
   so no light from above ever lights or glints on it. It reads as inner shadow and stops the sky
   showing through.

Budgets: maples 10000 tris (full crown has about twice the surface of a cap), bush 2000, pines 3000.
Measure crowns against a reference with a script (top, 2nd-percentile bottom, width, widest-band
height) before and after a rebuild; target within 10%.

Ground leaves: big (0.22-0.32 m) and few (6 per 1.25 m patch, one from each colour family,
centres at least 0.42 m apart), single-sided, stacked 4 mm apart so overlaps never z-fight.

## Gotchas

- Per-mass smooth cores read as shiny balloons or cobbles whatever the texture; no core at all
  was see-through. Shadow-only filler is the fix.
- Ear-clip triangulation fills lobe notches if new faces have no normal (call `normal_update()`).
- Under a bright low moon, lit tops of saturated red/orange cards clip to pink/white (near-step
  toon ramp); darker ramps helped but this needs lighting/exposure work, not more geometry.
- A thin cap crown with a long bare trunk was rejected by the user; preserve the established form.
- Sparse pools (411 leaves on 17 lobes) look see-through; raise density before raising card size.

## Source

trick-or-treat: art/team/foliage/batch03/CHECKPOINT.md, foliage_common.py, build_maples.py,
measure_crowns.py, catalog_update.py; yard_street/batch02 CHECKPOINT (blob canopies); user memory
fidelity-not-conformity.md. Grass and shell vegetation: see vegetation-shells.md.
