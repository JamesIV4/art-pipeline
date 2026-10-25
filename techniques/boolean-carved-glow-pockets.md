# Boolean-carved glow pockets (jack-o'-lantern faces, lit openings)

## What it is

Glowing carved openings (jack-o'-lantern eyes and grins, lantern windows, sarcophagus slits) made
as real recessed pockets cut with Blender's Exact boolean: a dark rind band at the lip, a glowing
inner wall that tapers in, and a glowing floor that follows the body's curvature. From the front a
dark rim frames a glowing hole, which reads at distance and at night.

## Why

A glow decal sitting a few mm proud of a shell (first bucket face) has no depth: walls dip into the
shell, there is no inner face, and from a side angle it reads as a sticker. A pocket gives the
classic carved read (dark rind, hot interior) from the gameplay angle with only a few hundred tris.

## How

trick-or-treat `farm_lib.carve(body, features, depth=0.05, inset=0.02, rim_color="pumpkin_dark",
rim_frac=0.4, rim_w=0.012, wall_glow="glow_jack", floor_color="glow_jack")`:

1. Features are 2D outlines in the front plane (x right, z up, metres), given as "grow-aware"
   callables `shape(grow) -> polygon` (`grin`, `arc_band`, `rounded_triangle`, `circle`,
   `convex_shape`) so thin crescents and toothed mouths stay simple polygons at every offset and
   keep the same vertex count.
2. Project each outline along +Y onto the body with BVH ray casts (raise if a ray misses), so the
   pocket follows the surface.
3. Build a cutter per feature: outer ring (grow +4 mm), rind band to `rim_frac` of the depth
   (`rim_w` about 1 cm), inner wall tapering in by `inset` so walls and floor face the camera,
   floor at `depth` along the surface. Exact boolean difference into a closed body (identity
   transform).
4. Classify every resulting face (outer, wall, inner, lip) and repaint: rind `pumpkin_dark`, walls
   and floor glow cells (`glow_jack`, or `glow_jack_hot` for a yellower mouth), then dissolve
   slivers and clean degenerate triangles.
5. Put a light socket inside (`socket_light` at about 0.42 x height) for the engine's flicker light.

Readability tuning from engine passes:

- Floors on `glow_jack_hot` and walls on `glow_jack` read yellow-hot like the concept.
- Flatten the face side of the body about 16% so the far eye does not sit on the silhouette at 3/4
  views.
- Thinnest feature that survives 15 m: about 5-6 cm crescents. Enlarge features that degenerate
  (the sleepy smile was enlarged after the first carve collapsed).
- Use 7 lobes instead of 8 on the body when the carve needs the tris (jacks fit in 1600).
- The same pocket recipe with a thick lobed shell (13 mm) made the dragon kid's bucket face, with a
  glowing chamber under a dark candy floor.

## Gotchas

- Miter offsets of thin shapes self-intersect; the Exact solver then deletes the whole body. Shrink
  convex shapes by scaling about the centroid instead, check `is_simple()` on every ring, and raise
  an error (not a warning) if the boolean loses geometry.
- The body must be a closed manifold at identity transform; apply transforms first.
- In Workbench, glow_jack (#ff8a1f) is almost the pumpkin colour; the sheet read comes only from the
  dark rims. Judge the glow in engine at night.
- At night bloom hides the rind band; in studio light it shows. Both are fine.

## Source

trick-or-treat: art/team/pumpkins_farm/batch01/pumpkin_lib.py and batch02/farm_lib.py (`carve`,
face shapes), pumpkins_farm batch01/02 CHECKPOINTs and batch02/results.json,
characters_candy/batch02 CHECKPOINT (bucket face), decor_ground/batch03 CHECKPOINT (jack glow cells).
