# Character costume fidelity pass (concept-matched outfits on one shared rig)

## What it is

Raising a family of procedurally built character outfits (trick-or-treat's five unlockable
costumes on the kid rig) to the detail level of a concept painting: shared high-detail parts
(sneakers), clean applique bands, grid-aligned painted regions, close-up review sheets, and a
parallel build where each outfit is its own module.

## Why

2026-10-26, user direction: "match the fidelity of the new costumes to this example image" (a
painted lineup of the same five costumes). Because the image showed the very assets being built,
the user was asked once whether it was a design target or only a quality bar (see
[art-direction-fidelity.md](art-direction-fidelity.md)); they chose to follow the image (designs,
colours, accessories), keeping the face, the candy bucket and the wand. Later directions: no wings
on the ghost, witch or pumpkin (the game shows magic dust instead), better witch hair, no hair
poking through the pumpkin cap.

## How

- **Split before fanning out.** One builder file per outfit (`costume_<name>.py`) plus a shared
  helper module, so several agents or people can iterate at once without edit collisions. The
  shared kit (rig joints, face, hands, bucket, sneaker) is changed first by one person and frozen
  while outfits are in progress; palette and catalog edits stay with the coordinator.
- **Shared detailed parts, per-outfit colours.** A chunky cartoon high-top built once
  (`kid_kit.sneaker(name, x, colors)`, ~1,600 tris per foot): a lathed upper whose warp lengthens the
  foot but keeps the ankle round, a two-piece sole (coloured outsole lathe under a white midsole
  lathe, so the stripe is a clean straight edge), a toe cap painted by grid band, swoosh panels as
  strip appliques on both sides, a swept padded collar, a blob tongue, criss-cross lace sweeps
  ray-cast onto the instep, and a heel tab. Each outfit passes a colour dict.
- **Grid-aligned paint on lathes.** Selecting faces by a world-space test (`y < k`) on a warped
  lathe gives staircase edges. Lathe faces are created ring-major, so face k = band k // segs,
  segment k % segs: paint whole bands and segment ranges (`kid_kit.paint_grid`) for edges along
  the mesh grid.
- **Strip appliques for curved shapes.** A decal built as one polygon and fan-triangulated breaks
  on concave or crescent outlines (swooshes, bones, bands). Build it as quads between a top and a
  bottom edge row, each vertex ray-cast onto the surface, plus thin walls (`kid_kit.strip`).
- **Hand recolour without moving grips.** Mitts and gloves reuse the exact hand shape with a
  different colour/material (`arm(hand_color=, hand_mat=)`); pads and finger bones stay inside the
  hand's farthest point, so the rig check's hand-tip delta stays 0 and held props don't move.
- **Review at three scales.** The normal 2x2 sheet (the 4th view is the gameplay camera), a 1024 px
  close-up sheet (`review_sheet(size=1024, zoom=1.75, focus=...)`) and a shoes sheet (`zoom=4`).
  Render them before posing the rig for the glide/flap sheet, which leaves the rig posed. Then
  in-engine previews for the real materials: Workbench sheets hide problems that only show under
  the game's toon lighting.
- **Budget.** The outfits went from ~9k to 11-15k tris (budget raised from 10k to 16k for the single
  player character); the face and bucket are a fixed ~4k.

## Gotchas

- A round white head with two dark ovals reads as a PANDA (the skeleton, twice): dark hood lumps
  at the temples read as panda ears. Make the skull cover the crown and temples, put sockets on the
  front face (skull-shaped, not round), and give the nose cavity and teeth real presence.
- Ghost eyes and the skeleton both depend on a forward-facing brow; eyes on the crown face the sky
  from the gameplay camera.
- A hat or cap shell must fully enclose the hair cap (or the hair cap must be cut to what shows
  below the rim), or hair pokes through at the back from the gameplay camera.
- Hair built as a single curtain or flat side panels reads as cardboard; build a rounded volume
  plus 10-16 tapered overlapping locks with curled, flipped ends and a few thick swept bangs.
- Thigh lathes with few rings make striped stockings coarse; add rings or a separate stocking.
- Concurrent builds rewrite a shared build log and rig report; that's harmless but last write wins.
- A snake-like tail swish: splitting the tail into a chain of rigid segments (with joint balls)
  read as segments and was rejected. Keep the tail one continuous mesh and bend it in the vertex
  shader: a per-instance `tail_wave` uniform (tip amplitude, phase, wavenumber, length) displaces
  vertices sideways by `amp * (s/len)^2 * sin(phase - k*s)`, s = distance from the tail's origin,
  plus a small rigid sway at the root. Keep it gentle (~5 cm at the tip); a strong swish read as too much.
- A tail that curls back into a hook reads as a "C"; an S (low swoop out, rise, tip easing back
  out) reads as a cat.

## Source

ToT `art/team/characters_candy/batch04/` (`kid_kit.py`: `sneaker`, `strip`, `paint_grid`, `arm`;
`costume_*.py`; `build_costumes.py --close --pose`; `CHECKPOINT.md`), 2026-10-26.
