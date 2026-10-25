# 2026-10-25 trick-or-treat: batch03 concept-fidelity pass retro

Batch03 (2026-10-24 evening to 2026-10-25) raised fidelity against the user's concept image
(art/review/concept/target.png) across decor, decor_ground, landmarks, vehicles, foliage and
characters_candy, then partly reversed on user feedback. Source: those lanes' batch03 CHECKPOINTs,
user memory fidelity-not-conformity.md and art-direction.md.

## What the pass did well

- decor: string_jack bulbs, three bunting flags, door wreath, lamp_post and porch_lantern with a
  shared four-sided Victorian `lantern4()` head (two-tone panes, flared roof). Workbench porch
  mock-up near and at 15 m to judge hanging decor in context. gates.py gained `floating: true`
  instead of a hard-coded id list.
- decor_ground: mums (about 30 twelve-petal heads Poisson-placed crown-first on a lumpy mound),
  brick planter (8 cm courses, 10 bevelled cap slabs, plants, ivy), brick pillar, sheet ghost, black
  cat, hay bales with wicker twine and straw fringe, jack floors moved to glow_jack_hot. Concept
  crops kept in `_ref/`.
- landmarks: travel gate split into a glow-free base and an all-glow lantern half (one glow_boost
  dims every switch-on glow); candy shop cart at 9178 tris; mailbox, car wheels and flower pot
  fidelity fixes; bench left unchanged because it already matched.
- vehicles: three cars rebuilt from a shared kit (profile loft, recessed glass, whitewalls).
- foliage: leaf-card maples, pines, bush, leaf scatter; shadow-only filler; analytic AO.
- characters_candy v3: jade onesie (hue measured on the concept), gold horns and claws, bigger
  forward-leaning wings, 4+4+6 spikes, bare hands; distance sheets with the concept kid alongside.

## Numbers worth keeping

- Gameplay check: 15 m, 35 deg; kid about 70 px of 900. Lamp at 20 m downscale matched the concept.
- string_jack shell: #ea6a1c and #c24c10 bloomed white; #a0400c (glow_jack_shell) worked.
- Maples rebuilt to the batch02 form: about 725 cards of 0.34 m + 215 inner cards, 9341-9699 tris,
  all dimensions within 10% of the old crowns (widest-band height noisy, 7-8%).
- leaf_scatter: 6 leaves of 0.22-0.32 m per 1.22 x 1.25 m patch, 78 tris.

## What the user reversed (2026-10-25)

- Street lamp: the crook design returned (the post-top lantern was a concept copy).
- Purple magic trail intensity and purple sky tint: restored after being dimmed/graded toward the
  concept.
- Drifting mesh clouds: restored after removal.
- Maple canopy: the full, low batch02 crown volume restored over a thinner concept-like umbrella.
- Candy v3.1: "remove the modelled specular from candy and restore the candy stripes".

Decision recorded as a standing rule: the concept is a quality bar, not a style guide; never delete
or restyle identity features to mimic it without asking (techniques/art-direction-fidelity.md).

## Open issues at hand-off

- Box collision from AABB: planter plants put the player at 0.86 m instead of 0.55 m; needs a
  collision-height override or plant-free variant.
- Bright lit tops of red/orange foliage clip to pink/white under the low preview moon (lighting).
- Mums read as daisies/phlox more than pompom mums; wreath brighter than the concept's.
- Hanging assets judged in Workbench for placement, in engine for glow only (preview limits).
- Bunting hems and small bat prints vanish beyond about 10 m.
