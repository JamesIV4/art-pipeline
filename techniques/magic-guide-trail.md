# Magic guide trail (swirling smoke ribbon that leads to goals)

## What it is

Wayfinding as a wispy, glowing purple "magic smoke" that meanders down the street and branches to
every unvisited doorstep, ending in a small swirl at the door. Three wide camera-facing sheets
drift around a spline centreline; layered scrolling noise carves them into soft flowing wisps. A
visited branch fades out so the trail always points somewhere new.

## Why

The user rejected a walk-along breadcrumb trail of candy: guidance must be "a subtle swirling
glowing magic trail, not a trail of candy". Candy is a reward for exploration and jumps, so it
cannot also be the signpost. The purple colour and intensity are part of the game's identity: when
an agent dimmed it to match a concept image the user asked for it back (see
art-direction-fidelity.md).

## How

Path planning (C++, generator stage 8, `plan_magic_paths`):

- Spine: down the street every 2 m, offset sideways `1.6 * sin(x * 0.11 + phase)`, height
  `1.0 + 0.25 * sin(x * 0.23 + 2 * phase)`. A second path runs up the side lane.
- One branch per lot: street point -> sidewalk -> entrance -> up the porch steps -> deck, then a
  9-point rising circle (r 0.55 x 0.35 m) in front of the door.

Mesh (`build_magic`): resample each path as Catmull-Rom every 0.25 m; for each of 3 strands
emit a strip whose vertices all sit on the centreline and carry: TANGENT = path direction,
NORMAL = a horizontal perpendicular, UV.x = distance along (m), UV.y = side 0/1, UV2.x = strand
index, UV2.y = fraction along the path. No shadows, extra cull margin 1 m, spine `fade` 0.7,
branches 1.0.

Shader (game/shaders/magic_trail.gdshader, blend_mix, unshaded, cull_disabled,
depth_draw_never, render_priority 2):

- Vertex: each strand orbits the centreline, `th = u * 0.55 + strand * 2.094 + TIME * (0.45 +
  0.12 * strand)`, radius `swirl (0.28) * (0.6 + 0.4 * strand)`, plus a slow vertical bob; then
  expand sideways perpendicular to both the view direction and the tangent by half-width
  `0.8 * (0.45 + 0.28 * strand)`. `near_fade = smoothstep(2.5, 9, camera distance)` so it never
  fogs the player's own view.
- Fragment: two fbm octave sets (billow at 0.4 u scale, curl at 0.9) scrolling toward the
  destination; across falloff `exp(-x^2 * 2.8) * (1 - x^2)^2`; density
  `smoothstep(0.28, 0.98, billow * 0.75 + curl * 0.4)`, squared-smoothstep again for an extra soft
  edge; ends fade over the first 8% and last 12%; depth soft-intersection over 0.7 m; opacity 0.36;
  colour mixes deep purple (0.36, 0.14, 0.72) to lilac (0.78, 0.55, 1.0) by curl, x glow 1.4.
- Visiting: when a doorbell rings, that branch's `instance uniform fade` drops at 0.5 per second,
  then the node hides.

## Gotchas

- Use a sine-free hash (Hoskins `hash2`) for the noise: sin-based hashes lose precision for the
  large u values of long paths and long sessions and show blocky cells.
- Wrap time (`mod(TIME, 600)`) for the same reason.
- Without the depth soft edge, sheets dipping into lawns, steps and walls show hard lines.
- Keep it subtle: an always-on bright trail competes with candy outlines and lantern glow. Fade the
  near part around the camera.
- Never reintroduce candy as the guide (user direction).

## Source

trick-or-treat: native/src/gen/candy.cpp (`plan_magic_paths`),
native/src/gen/neighborhood_generator.cpp (`build_magic`, visit fade),
game/shaders/magic_trail.gdshader, game/materials/magic_trail.tres, README generator stage 8,
user memory art-direction.md and fidelity-not-conformity.md.
