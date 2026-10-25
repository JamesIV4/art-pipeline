# XCOM 2026-09-29: initial workflow research and the environment worker audit

Context: OpenXcom-Extended-3D (3D Godot 4.7 remake of X-COM: UFO Defense,
Blender 5.1.2 authoring). First day of the reference-led rebuild; every initial
batch export had already been declared a rejected draft.

## Workflow research decisions (art/WORKFLOW_RESEARCH.md)

| Need | Decision |
| --- | --- |
| Exportable materials | Principled BSDF with image inputs; +Y tangent normals; Non-Color normal/ORM (R AO, G rough, B metal); shared external images (GLTF_SEPARATE) |
| Manufactured edges | Small real silhouette bevels + weighted normals; no coplanar duplicate faces for marks |
| UV/baking | Physical-scale seamless maps for modular surfaces; unique bakes need island margins; procedural nodes do not export |
| Foliage | Alpha MASK, opaque bark, economical cards, no blended stacks |
| Organic anatomy | OpenVDB remesh-union, smooth, simplify before weighting |
| Animation | Normalized weights, named actions stashed to NLA, pivots kept for rigid parts |
| Repeated terrain | MultiMesh per asset per spatial chunk (collective culling) |
| Native code | Pin godot-cpp, compile against the installed engine's dumped API |

- Ground tint: a Mix/Multiply node at factor 1 with a constant exports as
  `baseColorFactor`, so meadow/jungle grounds share one image.
- Fence UVs: repeating photographed board joints along a continuous rail was
  rejected; sample inside one board, bake sawn ends separately (~683 texels per
  2 m rail).
- Grass seams: repeat cannot fix source edge discontinuities; blend half-period
  shifted samples near boundaries; compare 6/10/16% widths.
- Rubble: BMesh bisect + hole fill corner cuts on closed stones (offline only).
- Scale: sqrt(6) m visual level pitch derived from the source projection and a
  30 deg ortho camera (see technique `isometric-sprite-scale-matching.md`).
- Metal review: navy-only background makes valid steel read black; test a
  constant-gray reflection sky at 0.25/0.42/0.60 (became `reflections.md`).
- Frogger's pipeline reused for join-after-weighting, pivots, import settings;
  its low-poly style explicitly rejected for this project.

## Environment worker audit (same day)

Root inspected the environment worker's sheets after a user complaint:
- A "metal trial" sheet labelled a rubbish-bin sprite showed generic rectangular
  boxes on a round post; the same cast box/post served paint and metal trials.
- A mailbox sheet showed a mailbox AND a bin per render against one source.
- Claimed brick-jamb code fix; sheets still showed old geometry.
- Uncalibrated scan selections preceded palette derivatives; old sheets could not
  validate new derivatives.
Source decoding itself was independently re-audited and passed (12 binaries, 178
MCD identities, 184 phases, 178 sheet crops).

Decision: replace the worker; reuse only independently checked source data and
download provenance; one exact source identity per comparison, all phases, four
model angles; small first batch reviewed before expansion; generic benchmarks
never carry an asset id.

Follow-ups: the v5 replacement went mailbox/bin/window wall through five
revisions (degenerate bevel UVs, can H/W fitted numerically to the 14x19 sprite
crop within -0.226%, zinc maps with true cylindrical aspect). Root also caught a
capture race (Godot screenshot used the old imported mesh); the capture harness
now verifies seals, source MD5 vs cache digest and loaded triangle count.

## What this cost

Three assets took a full day of strict per-asset review: three material trials
each, 36 inspected views per revision, five revisions. This overhead is what
the 2026-09-30 coverage-first policy removed.

## Sources

XCOM `art/WORKFLOW_RESEARCH.md`, `art/review/environment-worker-audit.md`,
`art/team/environment_replacement/research.md`, `root_gate_feedback.md`,
`worker_visual_review.md`.
