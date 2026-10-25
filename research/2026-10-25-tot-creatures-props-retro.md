# 2026-10-25 trick-or-treat: monsters, thorn vines and play props retro

Source: trick-or-treat art/team/monsters/batch03, vines/batch03 and play_props/batch03
CHECKPOINTs and helper kits (mon_kit.py, vine_kit.py, build_trampolines.py, build_wand.py).

## Monsters (20 assets: 10 monsters + 10 nests)

- Kit: mon_kit reuses farm_lib and dk_kit read-only; adds blob, band_lathe + wrap_prof
  (bandages), cone, bone, plate, seam, eye_cute, eye_glow, smile, cheek, rig/part, finish,
  nest_finish (clips nests at z = 0).
- Rig: root `monster_<key>`, `body` at translation 0, `part_a`/`part_b` at the C++ pivots exactly,
  no rotation or scale; slime body only; bat floating with a centred body.
- Palette row 14 (12 cells): bat fur/wing/belly, slime greens + glow_slime (flicker 0.25), bone
  shade, spider plum (not pure black so it reads at night), crow blue, grave soil, sarcophagus blue.
- Every asset had two or more engine passes plus a simulated 15 m contact sheet.
- Changes from review: ghost and mummy dropped `fabric` (read as plaid); skeleton `paper` ->
  `concrete` (skull looked striped); slime spikes -> base lumps; chunkier spider legs; toadstool cap
  tilted back so the face shows from above; web nest dome (read as a climbing frame) -> twig tepee;
  gremlin burrow grass top; sarcophagus dark interior with a glow frame and peeking eyes; mummy
  diagonal straps.
- Open: glow eyes bloom away pupils; mummy plainest silhouette; nest vines low contrast on grass.

## Thorn vines (4 assets)

- Knots of 2550-3395 tris (budget 3500) and a root mass of 8903/9000 with `roots` + `heart` parts
  (heart pulsed by the game around (0, 1.5, 0); authored at final size, so game scale 1 not 1.7).
- Passes: (1) pale birch-like stems, flat shard spines, tepee root mass, over budget; (2) dark
  hedge_dark base, 6-sided trim_white spines (lolly_white read pink at night), woven ground-hugging
  roots, bigger husk petals; (3) budget trims, thicker curl tips, footprint to about 4.2 m; (4)
  crown curls angled partly tangential.
- Open: bark furrows read as branches up close; spines pick up lavender under warm light; heart
  glow merges its veins.

## Play props: trampolines and the fire wand

- trampoline_large 5710/6000 (mat top 0.850, bounce 17.0), trampoline_mini 1388/1500 (top 0.280,
  bounce 14.0). Box collision, walkable, `collision_top`.
- Passes: first build 6478/1628 tris (springs 2.5 -> 2 coils, sleeves unchamfered, mini frame ring
  dropped); mat spider_plum -> cat_black (read mid-purple, orange target lacked contrast); mini
  straight white legs read as table legs -> bowed iron legs with lime feet; mini spring band from a
  piano-key strip to 64 finer silver/charcoal columns.
- Prints: flat decals +4/+8/+10 mm, AO baked on the body without them; 3 mm face offset z-fought at
  grazing angles, 6 mm held.
- Open: 1 cm springs read as a grey band at gameplay distance; pads 3-6 cm above `collision_top`;
  ladder widens the AABB.
- fire_wand (566/600): contract origin at grip centre, `socket_tip` at (0, 0, 0.30) Godot; flame
  colours took 5 passes (lemon blob -> peach-white -> glow_jack_shell licks over a hot core);
  cup darkened to foil_gold_dark to separate from the flame.

## Takeaways

Materials must be re-chosen per creature after an engine look; dark-but-not-black body colours
read at night; spines and thorns read by silhouette (bone-white, outward) plus dark stems; small
mechanical detail (springs, wires) needs exaggerated thickness or a painted band.
