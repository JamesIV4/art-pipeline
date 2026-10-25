# 2026-10-24 trick-or-treat: batch01 (flat) to batch02 (textured) retro

Three lanes built a v1 flat-palette set (batch01, about 15:00) and rebuilt it the same day to the
v2 "polished and textured" bar (batch02, about 16:15) after the user saw the flat slice. Source:
CHECKPOINT.md and results.json of yard_street, pumpkins_farm, characters_candy batch01/02;
art/team/BRIEF.md.

## What changed in the brief

- Direction: polished, toy-like 3D with soft rounded forms and hand-painted textures (Animal
  Crossing NH, A Short Hike, Mario 3D World props). Low poly but generous.
- Kit v2: every primitive takes `color=`, `mat=`, `project=`; AO baked; in-engine preview allowed
  (`tools/asset_preview.ps1`); at least two engine passes per asset, heroes more.
- Budgets roughly tripled: dragon kid 3000 -> 9000 (later 10000), wrapped candy 120 -> 400,
  lollipop 160 -> 500.

## yard_street (21 assets)

- v1: lathe with band colours and mullion panes, faceted blobs and puffs, cull_hidden, clean().
  Weak: car read as a boxy compact; thin chair/bench frames; inflatable cat had no definition;
  mailbox door same colour as box; clouds bead-like; glow never checked in game.
- v2: builders write their own seam-safe UVs (sweep, lathe, blob with pole axis and box UVs,
  loft). Trees with root flare and a visible fork, 32+ lobed leaf clusters, darker filler core;
  per-face underside tint removed (stair-step lines). Gored vinyl inflatables with pinched seams.
- Still weak: canopies like balloons/cauliflower (toon specular per cluster), car still Beetle-like
  at 3972/4000, several assets at budget, cauldron bloom, cream mailbox plate too bright at night.

## pumpkins_farm (21 assets)

- v1 pumpkin_lib: lobed bodies with painted groove strips, Exact-boolean carved jacks, ribbons,
  cleanup. Judged in Workbench only, where glow_jack is nearly the pumpkin colour.
- v2 farm_lib: plump sqrt-sine lobes, sharp grooves, real stem cavity, UVs giving each lobe one
  texture rib; ridged bark stems; corrugated draped leaves; carve with rind band + glowing wall +
  floor; WeightedNormal; build stamp in glTF extras. 21/21 PASS, no degenerate triangles.
- Pipeline finding: Godot re-imports only when the .gltf JSON changes; a build stamp now forces it.
- Still weak: far eye at 3/4 views, stiff paper-star leaves, twisted 3/4-sided twine catches pink
  highlights, 10-sided gourds, egg-like wagon heap.

## characters_candy (dragon kid + 7 candy)

- v1: rig contract set (root at feet, named parts at joints, bucket under arm_r, heap scaling from
  its floor); `attach()` without parent-inverse because K.set_parent drifted a nested child; 96 px
  far sheet.
- v2: pear torso, 28x15 hood, ray-cast belly patch with stitches, real boolean bucket face with a
  13 mm shell, felt materials. Engine passes changed: pout mouth -> upturned crescent; bigger
  highlights, face opening and horns; dragon_teal -> brighter felt_teal for night; tail stripe
  painted by sweep column; glowing interior -> glowing chamber under a dark candy floor; heap spread
  into a ring. Checked at about 80 px tall.
- Still weak: felt reads as terrycloth; dark back under blue night light; candy previews half
  buried (preview tool dropped floating assets on the grass; fixed later in the tool).

## Cross-lane findings

- K.ico subdiv 1 = 20 tris in Blender 5.1 (docstring said 80).
- K.set_parent read stale matrices (sockets at the origin) until fixed in the kit; re-export and
  check node translations.
- Every lane wrote its own clean/triangulate step to kill bevel and bisect slivers.
- Engine preview was the decisive review step; Workbench sheets were for shape only.
