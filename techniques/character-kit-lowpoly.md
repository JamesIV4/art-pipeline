# Low-poly characters and creatures (part rigs for procedural animation)

## What it is

Characters and monsters are built as a few rigid named parts parented to an empty root, each
part's origin at its joint, with translation-only glTF nodes. The game animates them procedurally
(rotating parts about their origins, scaling a heap), so there is no skinning. Built from lathes,
sweeps, ray-cast surface details and stitched seams with lane helper kits (dk_kit, cc_helpers,
mon_kit).

## Why

A cosy platformer needs readable, cute characters at a high 35-degree camera about 15 m away, on a
tight budget, animated without a rigging pipeline. Rigid parts with clean joints keep the
contract between art and code tiny and verifiable.

## How

Rig contract (hero, trick-or-treat dragon_kid):

- Empty root at the feet (z = 0). Children: `body` (pelvis), `head` (neck), `wing_l/r`, `tail`,
  `leg_l/r` (hips), `arm_l/r` (shoulders). A prop (`bucket`) is a child of `arm_r` with its origin
  at the grip; `bucket_candy` is a child of the bucket with its origin on the candy floor so scaling
  it 0 -> 1 grows the heap out of the bucket; `socket_bucket_light` at the bucket centre.
- Character right is Blender -X, front -Y. Every part has identity rotation and scale; bake any
  pose offset (a 6-degree curious head tilt) into the mesh so the rest pose stays identity.
- Monsters: root `monster_<key>` with `body` (translation 0) and optional `part_a` / `part_b` whose
  translations equal the code's pivot constants. Nests are one merged mesh, origin at ground centre.
- List parts and sockets in the catalog (`parts`, `sockets`); the gate fails if any are missing.

Helpers worth keeping (trick-or-treat art/team/characters_candy/batch02/dk_kit.py,
batch01/cc_helpers.py, monsters/batch03/mon_kit.py):

- `part(objs, name, joint)`: merge pieces, translate the mesh by -joint, set location = joint.
- `attach(child, parent)`: parent without a parent-inverse matrix (local translation = world
  difference). `K.set_parent` chained a parent-inverse through an already-parented object and left
  `bucket_candy` offset by the bucket's world position.
- `lathe()` with poles/warp/cut; `sweep()` with per-point radius, parallel-transport frames, profile
  warp and per-face column paint (paint stripes by sweep column, not by face position, or they
  come out jagged).
- `stitches()`: tent-shaped dashes, 6 tris each, along a ring found by ray casting (`bvh`, `hit`,
  `ring_on`). Seams and patches are ray-cast onto the body and pillowed with a soft edge.
- Faces: `eye_cute` (ink eye, white highlight, optional glint), `eye_glow`, `smile`, `cheek`.
- `g2b()` / `b2g()` convert game coordinates (Y up, Z front) to Blender (x, -z, y) for pivots.
- `--pieces` flag prints tris per sub-piece; budget planning is per part (hood 712, face 360, eyes
  196 each on a 9000-tri hero).

Readability rules from the engine passes:

- Check at gameplay size: shrink the preview to about 70-96 px tall. Face (eyes, cheeks, smile),
  bucket glow, and the back silhouette (horns, wings, spikes, tail) must survive.
- The likely camera is behind and above: wings leaned forward 18 degrees so their back face catches
  light; tail tip colour that reads as a white blob from behind was stopped before the curl.
- Mouth shape: a D read as a pout; an upturned crescent reads as a smile.
- Main colour must separate from the ground: a leaf green blended into the lawn; jade (#30ad6b,
  hue measured on the concept at 155-178) did not. Brighter felt teal read better at night.
- A fully glowing bucket interior washed out the candy: make a glowing chamber under a dark floor.
- Glow eyes bloom and swallow pupils; at distance that reads as "glowing eyes", up close the cute
  pupils are lost. Keep pupils on non-glow cells when cuteness matters.
- Pick materials per creature: fabric read as plaid on ghost/mummy, paper striped a skull.

## Gotchas

- Verify the exported glTF: node names, parents, translation-only transforms, socket positions.
- Floating creatures (bat) need `floating: true` and a centred origin; preview them lifted.
- Front-only details (wings as flaps from the front) may need to be larger if the AD wants them in
  the front silhouette.
- At 24-70 tris of headroom, any addition must be paid for elsewhere.

## Source

trick-or-treat: characters_candy batch01/02/03 CHECKPOINTs, dk_kit.py, cc_helpers.py,
monsters/batch03/CHECKPOINT.md and mon_kit.py, art/asset_catalog.json (parts/sockets).
