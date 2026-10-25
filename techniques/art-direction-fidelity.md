# Art direction: fidelity, not conformity

## What it is

The rule for working from a concept or reference image: the image is a quality bar (polish,
detail, richness), not a style guide. Raise the fidelity of existing assets and areas while
keeping their design, silhouette and colour identity. Never remove features, restyle designs or
re-grade palettes and lighting just because the reference differs, unless the user asks.

## Why

On 2026-10-24 the user saved a concept image (warm cosy Halloween street at night: blue moonlit
sky, warm lamp and porch light pools, lush leafy maples, mums, brick planters and pillars, jack
string lights, bunting, wreaths, fallen leaves everywhere, a green dragon-onesie kid) and asked to
match its fidelity. Agents then also conformed things to it. On 2026-10-25 the user asked to undo:

- the street lamp redesign (old shepherd's-crook lamp restored; the post-top lantern was concept-
  driven),
- the purple magic guide trail intensity (dimmed to match the concept),
- the purple sky tint (graded away),
- the drifting mesh clouds (removed because the concept had none),
- the thinner, concept-like maple canopy (the original full, low leaf volume was preferred).

These are deliberate parts of the game's identity.

## How

Judging an asset against a concept:

1. Crop the concept region that shows the same kind of thing and keep the crops beside the lane
   (`_ref/` folders: ghost, cat, planter, mums, bales, jacks).
2. Compare at the same on-screen size (readability-at-distance.md: `distance_check.py --concept`).
3. List gaps in terms of polish: missing secondary forms (scroll brackets, flared eaves, twine,
   straw fringe, petal bumps), material reads (wicker vs rust bands), lushness (fillers, spill
   leaves), glow behaviour (jack faces yellow-hot), proportions (toy-chunky shafts).
4. Measure, do not guess: hue of the concept's onesie measured at 155-178 (jade, not leaf green);
   bulb size against the door; crown top, bottom and width measured old vs new (within 10%).
5. Upgrade in place: same footprint, sockets, rig contract, collision and walk heights unless a
   change is requested (hay bale fringe kept below 0.562 m so the walk height barely moved).
6. When the concept differs in design (lamp style, cloud presence, colour of a signature effect,
   crown shape), keep the existing design and ask before changing it.
7. Record what changed and why in the CHECKPOINT; say what still differs from the concept.

Standing direction from the user (trick-or-treat): polished toy-like low poly with hand-painted
textures; guidance by a swirling magic trail, never a candy breadcrumb; candy glow is an outline,
not a halo; lots of easy ground candy in loose clusters, jumps only for chains and high-value
pieces, no candy piled on porch roofs; audio AdLib FM, not square wave; feedback scaled to success,
not blanket amplification (no candy wobble near the player, no per-pickup pitch climb). The
2026-10-24 gap analysis named purple tint/haze and pastel washes as the main differences from the
concept; acting on that by re-grading the sky and dimming the trail is exactly what the user
reversed the next day. Fix pastel washes on assets (saturation, night readability); leave the
signature purple sky and trail alone.

User reversals inside a lane are direction too: "remove the modelled specular from candy and
restore the candy stripes" (the concept candies were solid with a highlight; the user preferred the
shader gloss and the old stripes).

## Gotchas

- "Match the concept" invites deleting things the concept lacks. Treat removals as design
  changes that need a yes.
- Modelled highlights duplicate what the shader already does (gloss, rim) and look painted-on.
- A concept-matched colour can still fail in context (leaf green melted into the lawn).
- Keep superseded notes clearly marked in the CHECKPOINT so the next worker does not revive them.

## Source

User memory: fidelity-not-conformity.md, art-direction.md. trick-or-treat CHECKPOINTs of
characters_candy/batch03, decor/batch03, decor_ground/batch03, foliage/batch03, landmarks/batch03;
art/asset_catalog.json (lamp_post brief); art/review/concept/.
