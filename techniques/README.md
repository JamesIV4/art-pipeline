# techniques/

One file per learned technique: **What**, **Why** (the problem it solved or the user direction behind
it), **How** (steps, numbers, the tool or kit that implements it), **Gotchas** (failures actually
seen), **Source**. Keep them short; add a new file rather than growing an unrelated one, and update
an existing file when a technique changes (note the date). Origin: ToT = trick-or-treat, XCOM =
OpenXcom-Extended-3D.

## Style and direction
| File | Origin |
|---|---|
| [art-direction-fidelity.md](art-direction-fidelity.md): fidelity, not conformity; judging against a concept image | ToT |
| [lowpoly-textured-style.md](lowpoly-textured-style.md): the kit v2 contract and build/review loop | ToT |
| [readability-at-distance.md](readability-at-distance.md): checking silhouettes and colour at play distance | ToT |
| [parametric-asset-families.md](parametric-asset-families.md): one spec table, many variants | ToT |

## Colour, materials, textures
| File | Origin |
|---|---|
| [palette-tint-uv.md](palette-tint-uv.md): 16x16 palette, UV2 = layer + cell, glow cells, lane rows | ToT |
| [painted-material-arrays.md](painted-material-arrays.md): painted layers as Texture2DArrays | ToT |
| [ai-texture-generation.md](ai-texture-generation.md): Codex image_gen sources with provenance | ToT |
| [glow-cells-and-bloom.md](glow-cells-and-bloom.md): emissive cells that survive bloom | ToT |
| [vertex-ao-bake.md](vertex-ao-bake.md): baked per-vertex AO and its variants | ToT |
| [surface-decals-and-prints.md](surface-decals-and-prints.md): conformed, offset, AO-safe decals | ToT |
| [sweep-lathe-uvs.md](sweep-lathe-uvs.md): seam-safe material UVs on sweeps and lathes | ToT |
| [pbr-map-derivation.md](pbr-map-derivation.md): CC0 first, map conventions, derivation recipes | XCOM |
| [texture-compression.md](texture-compression.md): lossless WebP, import policy, content-addressed sharing | XCOM |
| [atlas-packing.md](atlas-packing.md): prop atlases, fit and lathe mapping, cutout atlases | XCOM |
| [ground-materials.md](ground-materials.md): world-projected layered ground, wavy borders | XCOM |
| [reflections.md](reflections.md): neutral reflection sky and true-metal values | XCOM |

## Modelling
| File | Origin |
|---|---|
| [character-kit-lowpoly.md](character-kit-lowpoly.md): part rigs for procedural animation | ToT |
| [vehicle-kit-lowpoly.md](vehicle-kit-lowpoly.md): profile-lofted toy vehicles | ToT |
| [foliage-crowns-lowpoly.md](foliage-crowns-lowpoly.md): leaf-card crowns, custom normals, analytic AO | ToT |
| [thorn-vines-spines.md](thorn-vines-spines.md): tendrils, curls, spines at scale | ToT |
| [boolean-carved-glow-pockets.md](boolean-carved-glow-pockets.md): carved lit openings | ToT |
| [walkable-props-collision.md](walkable-props-collision.md): walkable tops and the collision contract | ToT |
| [vegetation-shells.md](vegetation-shells.md): continuous wood shells, laminae, orientation gates | XCOM |
| [foliage-cards.md](foliage-cards.md): "lettuce" failure, spray cards, crown normals, waxy leaves | XCOM |
| [ground-scatter.md](ground-scatter.md): density-field grass, litter, clods | XCOM |
| [procedural-terrain-bases.md](procedural-terrain-bases.md): shared base meshes + detail attachments | XCOM |
| [modular-fit-clipping.md](modular-fit-clipping.md): allowed volume per tile part | XCOM |
| [solidify-thickness.md](solidify-thickness.md): thickness without spikes; paired-shell gates | XCOM |
| [garment-workflow.md](garment-workflow.md): body-derived undersuits, delete groups, plates | XCOM |
| [hair-cards.md](hair-cards.md): hair cards from a Curves groom | XCOM |
| [humanoid-rig-fitting.md](humanoid-rig-fitting.md): CC0 base retargeting, generated-mesh fitting, hands | XCOM |
| [isometric-sprite-scale-matching.md](isometric-sprite-scale-matching.md): 3D scale/camera from 2D sprites | XCOM |
| [tangent-integrity.md](tangent-integrity.md): tangents and normals through glTF export | XCOM |

## Animation and sidecars
| File | Origin |
|---|---|
| [in-place-locomotion.md](in-place-locomotion.md): in-place loops, distance-driven playback, ground IK | XCOM |
| [unit-sidecars.md](unit-sidecars.md): ragdoll, blood, sockets, handling JSON | XCOM |
| [morph-water-animation.md](morph-water-animation.md): shape-key water as glTF morphs | XCOM |

## Effects
| File | Origin |
|---|---|
| [flame-flipbooks.md](flame-flipbooks.md): sprite/flipbook particle art and packing | ToT |
| [procedural-fire-flipbook.md](procedural-fire-flipbook.md): heat-field fire, sliding noise window | ToT |
| [outline-glow.md](outline-glow.md): inflated back-face outline in the object's colour | ToT |
| [candy-beam-column.md](candy-beam-column.md): yaw-only billboard light column under pickups | ToT |
| [magic-guide-trail.md](magic-guide-trail.md): swirling smoke ribbon that leads to goals | ToT |
| [fm-synth-audio.md](fm-synth-audio.md): OPL2/AdLib-style FM sound and music | ToT |

## Engine, lighting, performance
| File | Origin |
|---|---|
| [toon-shading.md](toon-shading.md): the textured toon shader | ToT |
| [post-processing-stack.md](post-processing-stack.md): Godot 4.7 Forward+ post stack and presets | ToT + XCOM |
| [lighting-calibration.md](lighting-calibration.md): one lighting profile, calibration lab, no per-asset albedo fixes | XCOM |
| [layered-merges.md](layered-merges.md): one surface per static asset via texture-array layers | XCOM |
| [lod-and-render-cost.md](lod-and-render-cost.md): budgets, MultiMesh chunks, LOD, setting costs | XCOM |

## Review
| File | Origin |
|---|---|
| [review-sheets.md](review-sheets.md): Workbench sheets and engine previews | ToT |
| [godot-review-captures.md](godot-review-captures.md): preview sheets, scene captures, render controls | ToT + XCOM |
| [independent-review-gates.md](independent-review-gates.md): mechanical gate + root visual gate | XCOM |
