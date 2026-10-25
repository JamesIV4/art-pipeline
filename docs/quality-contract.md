# Quality contract

One contract for every game, merged from trick-or-treat's low-poly contract (`art/README.md`) and
XCOM's `QUALITY_CONTRACT.md` (policy `coverage-first-v1`, 2026-09-30). Each game's brief adds its own
style bar (see `team-brief-template.md`); nothing here is waived by a brief.

## Principles

1. **Technical success is not art completion.** Exported, gate-passing and "rebuilt" are separate
   states from "visually reviewed". Passing gates earns a review, never an approval. Counts of files
   or auto-passed assets are not progress; the metric is more genuinely useful assets with no rise
   in major defects.
2. **The reference is ground truth.** Inspect every real view of the exact source or concept before
   authoring. Record what was observed separately from honest inferences; never claim an unseen side
   as observed.
3. **Fidelity, not conformity.** A concept image is a quality bar, not a style guide. Raise polish
   and detail while keeping each asset's design, silhouette and colour identity. Never delete
   features, restyle established designs or re-grade palettes/lighting to mimic a reference without
   asking the user (`techniques/art-direction-fidelity.md`).
4. **Readable at gameplay distance.** Judge silhouettes and colour from the real game camera, at
   night if the game is at night, not only in close-ups or studio light.
5. **Consistency within a family beats pixel-exact counts.** Finish models first: list small
   imperfections in the report and move on rather than polishing one asset forever.
6. **Be honest in hand-offs.** Weak and unresolved items are stated plainly in `CHECKPOINT.md`.
   Workers never claim art approval.

## Never waived

- Wrong or mismatched references (the sheet's source column must come from the trial manifest or
  catalog, never be hard-coded).
- Inverted or inward-facing geometry; mismatched UV / material roles; degenerate triangles.
- Off-palette colours (low-poly games) or untextured legacy exports.
- Unrooted anatomy, floating attachments, opaque attachment failures.
- Stale imports: a capture must prove the engine loaded the current file (`source_md5`, not mtime).
- Missing required sockets, parts or source features; origin not at ground for grounded assets.
- Vegetation that only works from the front (coplanar fans); trunks without source-led taper.
- Matching route arrays or consistent local normals do not prove contact or outward winding; test
  those directly.

## Style bar for textured low poly (trick-or-treat, reusable)

- Polished, toy-like 3D: soft rounded forms, hand-painted tiling materials, bevelled hard edges,
  smooth shading on organic forms, detail where the eye lands (rims, seams, stitching, caps).
- Low poly but generous: spend the budget on silhouette, rims and seams.
- Pick materials by what the surface is; tiny parts use low-contrast materials or `flat`.
- Glow is an outline or emissive palette cell, not a halo; check glow at night, where bloom can
  swallow detail (`techniques/glow-cells-and-bloom.md`).

## What counts as done

An asset is done when the root reviewer has passed it in the engine under the shipped lighting
(four angles plus a gameplay-distance view), after a verified fresh import, and that is recorded:

- trick-or-treat: gates PASS, engine preview reviewed, the asset published by `publish_catalog.py`.
- XCOM: `status: rebuilt_reviewed`, `quality_review.passed: true` with reviewer, details and
  `source_limits` in the catalog.

User feedback overrides any approval. A changed shared helper or dependency invalidates earlier
mechanical proofs for the assets that use it.
