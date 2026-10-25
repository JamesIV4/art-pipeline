# XCOM 2026-09-30: vegetation semantic and orientation audit

## Trigger

User: dead fronds modelled as tree limbs, many plant parts upside down, weak
source fidelity, thick trunks, unnatural branch arrangements. All promotion of
affected vegetation was stopped (137 plant/wood/foliage identities out of 190
audited). One approved asset (FOREST003) and all frozen artifacts protected.

## Findings

- Classification errors from colour: brown/pale was read as wood, producing
  capped cylinders with sawn end rings for what were dead fronds, petioles,
  sheaths and rolled laminae. Damage records (via the MCD Die link in the same
  dataset) are the same plant damaged, not new "burnt trees" or "log piles".
- Box-clipped rectangular foliage panels and cube-sheared crowns were being
  treated as evidence of source continuity; a sprite crop edge is not a
  physical cut.
- Helper bug: `Mesh.leaf` rotated its frame by texture roll before applying
  bend; bend's vertical component goes as cos(roll), so roll 1.8 rad turns a
  downward bend upward. Calling it "hanging" did not repair it. Near-vertical
  leaf axes made bends horizontal.
- Paddle petioles used straight centrelines while laminae bent away: attachment
  had to be checked, not inferred from a UV endpoint.
- Hard XY/Z clipping removed midrib strips and left floating opaque tips.
- Double-sided use of one photo does not establish upper vs lower face.
- Atlas orientation registration used the lowest opaque band, not anatomical
  landmarks.
- Strict export validation passed all 190 files: mechanical health says nothing
  about semantics or orientation.

## Decisions

- Hard semantic/orientation gate per exact id before any affected promotion:
  classify from form and attachment (record uncertainty; unknown species stay
  unknown); separate texture/profile roll from an explicit gravity/centreline
  frame; check upper/lower face, root/crown attachment, UV base/tip, winding and
  gravity bend in four angles.
- A fresh anatomy-first worker; small representative pilot before expanding.
- Follow-up rules (user 2026-10-01): roots/branches grow continuously out of the
  trunk as one surface with bark UVs across the join (became the implicit-field
  tree method on 2026-10-02).
- 2026-10-02 foliage guide superseded the leaf-surface approach (cards).

## Sources

XCOM `art/team/vegetation_rebuild/orientation_anatomy_audit_v13/confirmed_findings.md`,
`orientation_anatomy_audit_v14/summary.md`,
`art/review/workflow_snapshots/20260930-strict-TEAM_REQUIREMENTS.md` ("Direct user
vegetation correction"), `art/TEAM_REQUIREMENTS.md`.
