# Surface decals and prints (conformed, offset, AO-safe)

## What it is

Flat painted details (wrapper prints, eyes, cheeks, dots, door seams, chrome rub strips, mat
prints, runes, highlights on glass) built as separate thin polygons conformed onto the body
surface by BVH ray casting, lifted a few millimetres along the normal, and painted with their own
palette cell. Cheaper and more controllable than modelling the detail into the body.

## Why

Low-poly bodies cannot carry painted detail in their tint alone (one cell per face). Decals add
readable graphics (a jack face on a trampoline, bats on a candy wrapper, door seams on a car)
for a handful of triangles, without changing the silhouette.

## How

Helpers: cv_kit `decal(tree, origin, direction, outline, size, color, up, off=0.004, spin)`,
decor_ground `decal()` / `disc_on()` / `oval()`, mon_kit `eye_cute` / `cheek` / `smile`, car_kit
`ribbon()` (flat ribbons ray-cast onto the body), lm_common `stroke()` (tapered brush-stroke
ribbon), dk_kit `stitches()`.

1. Ray-cast the outline's points onto the target (BVH of the body in world space) along a chosen
   direction; place each point at hit + normal * offset.
2. Subdivide decal edges before conforming on curved bodies, or the straight edges cut into the
   surface (v1 eyeball iris and bat/ghost prints sank into round candy).
3. Offsets that held against z-fighting at grazing angles: 2-4 mm for large flat prints, 6-10 mm
   for stacked layers (stem over pumpkin print over mat: +4, +8, +10 mm), 4 mm for glass streaks.
   Stack layers with increasing offsets.
4. Orient for the camera: prints on spinning candy were tilted 22 degrees toward the 30-degree
   gameplay camera and enlarged, on front and back.
5. AO: bake the body without the decals (so the surface under a print does not darken), then give
   decals their own pass with no occlusion. Keep prints as a child node (`mat_print`) or bake them
   separately.
6. Calm the base under a decal: grooves on a string-light globe were flattened on the front so
   the face decal sits flush.

## Gotchas

- Edges of decals stand off the shell by a few mm at grazing side angles; keep offsets minimal and
  shapes compact.
- Directional prints (a face) read as rotated and "broken" from the sides; a ring or target still
  reads from any angle, so combine directional and radial graphics on round props.
- Prints only on front and back of a spinning piece leave it plain side-on.
- A decal outline redrawn as an icon needs testing at size: a bat first read as a moustache or a
  crown; leaves with deep notches and raised centres read as Christmas stars.
- Modelled highlight decals (white streaks and dots on candy) duplicated the shader's gloss and were
  removed at the user's request.

## Source

trick-or-treat: candy_variety/batch03 (cv_kit.py, CHECKPOINT), play_props/batch03 CHECKPOINT
(trampoline prints), decor/batch03 CHECKPOINT (string_jack, bunting, wreath), vehicles/batch03
(car_kit.py ribbons, glass streaks), decor_ground/batch03/decor_common.py,
characters_candy/batch02-03 CHECKPOINTs.
