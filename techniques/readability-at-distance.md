# Readability at gameplay distance

## What it is

Every asset is judged at the size it appears on screen during play, not at close-up size. A
simple pixel-shrink of the engine preview to its gameplay footprint, blown back up with
nearest-neighbour, shows what survives.

## Why

The quality contract's first rule: an asset must read instantly as a flat silhouette from the
gameplay camera (35 degrees down, about 15 m away). Many details that cost budget (embossed ribs,
8 cm licence-plate letters, 1 cm springs, thin crescents) vanish or turn to noise at that size,
while blunt silhouette and glow decisions decide the read.

## How

Numbers used in trick-or-treat: camera about 15 m, pitch about 35 degrees, fov 50, 1600x900. The
1.1 m hero is about 70 px tall on a 900 px screen (80 px and 96 px were also used as checks).

Tools (trick-or-treat lane scripts, worth porting as one tool):

- `far_check.ps1 -Ids a,b [-Distance 15] [-Fov 50]` (pumpkins_farm/batch02, decor_ground):
  reads the glTF POSITION min/max to get the preview camera distance
  (radius / tan(fov/2) * 1.25), shrinks the night tile by preview_dist / Distance with bicubic,
  crops the centre, enlarges x4 nearest-neighbour into a labelled strip.
- `distance_check.py <engine.png> <out.png> --subject 300 --px 70 [--concept x0,y0,x1,y1]`
  (characters_candy/batch03): shrinks each preview quadrant so the subject is `px` tall, enlarges
  x3 nearest, and pastes the concept-image crop of the same subject at the same size alongside.
- Contact sheets with a far row (`contact.py --far 15`, candy `gameplay` sheet at about 10 m).
- Mock-ups at distance (`porch_mockup_15m.png`) for hanging decor in context.

What the checks taught:

- Thin carved features at risk: wink and sleepy crescents (about 5-6 cm) were the thinnest that
  still read at 15 m; thinner ones go.
- 3/4 views hide the far eye of a carved face near the silhouette; flatten the face side (16%) so
  both eyes face the camera.
- Small details invisible beyond about 10 m: a 0.16 m bat print, bunting hems, car antenna and
  topper, mailbox daisies. Either enlarge them or spend the tris elsewhere.
- Thin wire and frames read as a grey band or shimmer (springs, chair frames); thicken or paint.
- Glow reads first: at distance "glowing eyes" beats cute pupils, and a jack's face reads by its
  emissive floor plus dark rind rim.
- Contrast with the ground: low-contrast vines and leaves on grass disappear; colours too close to
  the lawn (leaf-green onesie) melt in.
- Cream or white elements glare at night (a cream number plate was swapped for brass/caramel).

## Gotchas

- Shrinking the studio tile overstates pastel wash; use the night tile.
- Workbench sheets have no glow, so a distance check on them misjudges lanterns and jacks.
- The concept image's subject size must be measured (e.g. bulbs about 0.25 m against a 2.2 m door)
  before comparing.

## Source

trick-or-treat: art/README.md (quality contract), pumpkins_farm/batch02/far_check.ps1,
characters_candy/batch03/distance_check.py, CHECKPOINTs of characters_candy batch01-03,
pumpkins_farm batch01/02, decor, landmarks, vehicles, play_props, monsters.
