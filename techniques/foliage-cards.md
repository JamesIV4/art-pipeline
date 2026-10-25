# Foliage cards, crown volume normals, grass clumps and waxy leaf response

## What it is

The realistic real-time method for leaves and grass: many small alpha-cutout
cards carrying branchlet sprays or blade clumps, normals transferred from a
crown proxy (or pointed up for grass), and a "living, waxy" PBR response.
(Stylised low-poly crowns are a different technique: `foliage-crowns-lowpoly.md`.)

## Why

User verdict on XCOM's first trees and grass: "lettuce folds". Causes, all
seen: few large leaf sheets curled into lobes; leaf clusters modelled as
smooth displaced shells; dense gap-free leaf textures that mip into solid
blocks; flat per-card normals plus sheen (bright/dark lobes per card); even
ball-shaped clumps; grass as wide ribbons. Later: leaves read gray and dusty
because of uniform roughness ~0.76 under Godot's default specular.

## How: trees and shrubs

1. Wood skeleton in geometry down to twigs (see `vegetation-shells.md`); leave
   crown gaps where branches and sky show.
2. Leaves only on alpha-cut cards attached to twigs. Flat quad or polygon
   trimmed to the spray outline (less overdraw); at most a slight bend along the
   twig axis. Never curl or fold a card.
3. Atlas cells = one twig with 5-30 separate leaves and transparent gaps;
   4-8 variants per species; realistic leaf size (broadleaf 4-15 cm). Dilate
   colour under alpha so mips do not fringe. Source priority: CC0 leaf/branch
   scan > image generation with transparency ("a single small twig with 12
   separate leaves, top-down orthographic, evenly lit, no shadows") > procedural
   only for masks/derived maps.
4. Many small cards (0.25-0.6 m at XCOM scale, 2-4 triangles each); a 6k
   budget carries hundreds. Splay outward/upward with random roll about the twig
   and varied pitch; sprays leave twigs at <= ~37 deg; crossing pairs sparingly;
   never coplanar fans or all facing camera. Put the UV midrib on the spray's
   woody stub so the card's exit from the 3D twig lands on opaque texels.
5. Irregular crown masses following the source silhouette: unequal clusters,
   noise-broken outline, a few gaps. No domes, no evenly spaced balls.
6. Volume normals (the key fix): Data Transfer (Face Corner -> Custom Normals)
   from an ellipsoid/convex hull per crown or lobe, or Normal Edit radial to an
   empty at the crown centre; blend 70-100% (below 100% on outermost cards if
   flat). Front and back of a two-sided card share the transferred normal.
7. Per-card colour jitter in COLOR_0 (hue/value +-5-10%) and darker interior
   cards (vertex AO toward the crown centre). XCOM canopy: top clusters ~1.0,
   bulk ~0.5, undersides ~0.36-0.42.
Palm fronds (rachis + separate alpha leaflets) are already correct; keep them.

## How: grass

- The ground texture carries most grass; 3D grass is tufts of 2-3 crossed
  clump cards (10-30 thin tapered blades each, gaps), random yaw and slight
  lean, density map without a grid, height from the source.
- Normals point up (ground normal) via Normal Edit directional or Data Transfer
  from the floor; optionally 20-30% geometric toward tips. Never the cards' own
  sideways normals.
- Base colour matches the floor's hue/value, lighter toward tips (vertex
  gradient). Keep tufts off a regular border pattern; small overhang is fine.
- At map scale XCOM replaced per-tile tufts with a runtime scatter
  (`ground-scatter.md`).

## Material

- Alpha scissor ~0.4-0.5 (glTF MASK), double-sided, opaque bark separate.
- Living plants are waxy (approved recipe, 2026-10-16): ORM roughness centred
  ~0.42 (keep the texture's spread, floor ~0.28, ceiling ~0.58; needles ~0.48,
  blades ~0.52, petals ~0.50, cactus ~0.40), leaf normal scale 1.0, runtime
  dielectric specular 0.25 on those materials. Metallic 0. Dead wood, bark, dry
  grass, straw, litter stay matte (0.8+).
- Exception: clipped flat-topped hedges keep authored roughness and only get the
  low specular (waxy roughness made long glare bars). Check any flat-topped
  foliage in the game camera, not just close-up.
- Tool: XCOM `art/tools/make_waxy_foliage.py` (port: `tools/textures/`) writes
  waxy ORM copies (never touching shared originals), repoints materials, refreshes
  seals and writes the runtime specular manifest; its `PLANT` table maps ORM stem
  -> (centre, gain, floor, ceiling).

## Self-check before export

At game zoom from the source camera: many small leaves/blades with depth, no
folds/lobes/ribbons. Four angles: no visible card planes, no dark backs, broken
silhouette. Lighting soft and volumetric. Atlas mips stay airy at 4x downscale.
Sheet includes one close-up and one game-zoom crop.

## Gotchas

- Free/library trees were useless for budget: 231k-tri cards collapse when
  decimated; in-budget plants are tiny sprigs. Use libraries as texture refs.
- Leaf roughness raised to 0.7-0.8 to kill gray sky glints made leaves matte
  and gray; the real fix was lower specular.
- Generated atlas cells crossing the generator's quadrant lines need re-packing
  by connected components.

## Source

- XCOM `art/team/VEGETATION_FOLIAGE_GUIDE.md` (with its sources: Polycount
  foliage threads, GPU Gems ch. 7, gamesartist lush-tree)
- XCOM `art/team/ORCHESTRATION_OPUS55.md` ("Plant light response")
- XCOM `art/tools/make_waxy_foliage.py` docstring
- XCOM `art/team/vegetation_anatomy_max/opus_batch03/research.md`
- XCOM `art/team/research/asset_server_eval/REPORT.md`
