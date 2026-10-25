# Toy vehicles (profile-lofted bodies with recessed glass)

## What it is

A recipe and helper kit for bubbly toy cars: a filleted side profile with wheel-arch cut-outs
lofted across the width with per-vertex rounding radii, a greenhouse lofted up from rounded-rect
rings with recessed dark glass, chunky whitewall wheels, and chrome details ray-cast onto the body.
Three variants (compact car, station wagon, pickup) shared one kit at about 4500 tris each.

## Why

The first parked car was a single lofted blob with window panels painted on; it read as a boxy
compact, not a toy. The rebuild needed planar flat-shaded side panels (toy paint), soft bubbly
nose and tail, dark wheel wells, and windows with depth, without blowing the budget.

## How

trick-or-treat art/team/vehicles/batch03/car_kit.py (on top of lm_common -> yard_common):

1. `fillet_outline(corners)` + `profile_corners(spec)`: the side profile as a closed 2D polygon
   with a rounding radius per corner, semicircular arches (`arch_points`) cut in.
2. `lower_body(P, hw, color, r_top=0.13, r_front=0.22, r_back=0.2, r_bot=0.03, r_arch=0.035)`:
   loft the profile across X with rounding rings whose radius is set per vertex from the outline
   normal (about 0.22 m nose, 0.09 m top edges, 0.035 m arches). Flat side panels stay planar and
   flat-shaded; nose and tail bulge in plan; bonnet gets a slight crown. Arch ceilings and the
   underside are charcoal so wheels sit in dark wells. A fifth rounding ring smoothed the nose.
3. Pickup bed: the same loft with rail rings and "lowered" rings for the floor and inner walls,
   plus a separate 12-quad plank floor so AO has interior vertices; `finish_car(ao_lift=...)`
   lifts the bed AO, which baked near-black.
4. `Cabin`: rounded-rect rings lofted up Z with tumblehome, rake and an eased windshield curve.
   Glass bands recessed 2.5 cm (shadow_navy, flat-shaded) with chrome reveal faces; pillars are the
   un-recessed parts in body colour; contrasting roof with a rounded edge; one or two diagonal
   foil_silver highlight quads per window, 4 mm proud.
5. Details: `wheel()` 16 segments, charcoal tyre (inner sidewall skipped), whitewall ring, iron
   band, silver dish, red button, body-coloured rim; `lamp()` lathe pods with chrome bezel and
   domed lens; oval chrome grille with bars; raycast wrap-around bumpers; door seams and a rub
   strip as flat ribbons ray-cast onto the body; handles, mirrors; plates with tori letters; small
   themed cargo (jack-o'-lanterns, bales).
6. Paint: body and roof on `flat` (glossy toy paint). Origin at ground centre, tyres touching
   z = 0, front -Y; collision box, walkable.

Iteration notes: first passes ran 5812 and 6478 tris; cuts came from fewer rounding rings on the
roof, unbevelled feet and straps, lighter mirror and headlight blobs. A `lineup.ps1` previewed the
three together at gameplay distance.

## Gotchas

- The `metal` material read as hairline brush streaks on large panels even with UVs scaled down;
  use flat paint for car bodies.
- Cream rims made wheels read as white discs; body-coloured rims fixed it. 14/10-sided tyres and
  hubs read as white octagons; 16 segments with layered rings fixed it.
- A cream greenhouse read as a tan box; pillars in body colour with only the roof contrasting read
  as a car.
- Mint and teal wash to white/pastel in studio light; check saturation at night.
- Mirrors, antenna (8 mm) and 8 cm plate letters vanish at gameplay distance.
- Roof cargo and mirrors inflate the AABB-based collision box (player stands 0.22 m above the
  roof); see walkable-props-collision.md.

## Source

trick-or-treat: art/team/vehicles/batch03/CHECKPOINT.md and car_kit.py, landmarks/batch03
CHECKPOINT (car wheels pass), yard_street batch01/02 CHECKPOINTs (earlier car).
