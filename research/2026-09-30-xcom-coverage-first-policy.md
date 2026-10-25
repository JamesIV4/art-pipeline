# XCOM 2026-09-30: from the strict per-asset contract to coverage-first-v1

## Before (strict contract, preserved as rollback)

Every asset required: source byte verification and dossier; online research per
new material; at least three actual material trials on the asset beside the
sprites; four-plus Blender angles and Godot captures; a written results
manifest; worker self-approval; root review of all trials. Parallel workers:
GPT-6.1 Sol at max effort only. Result: correct but very slow (a day for three
props), with repeated formal reviews of unchanged evidence.

## Decision (user, 2026-09-30)

Policy `coverage-first-v1`: same quality bar, far less review ceremony.
- One strong researched candidate per asset; alternatives only when the first
  visibly fails, the source is genuinely ambiguous, or a new technique needs a
  pilot.
- Artist checks four Blender angles while modelling and saves ONE selected
  sheet; no second formal self-approval, no long per-asset essay.
- Cheap mechanical gates stay mandatory on every export (identity, geometry,
  winding, UV/tangent/material, budget, metadata, seals, import settings).
- Root does ONE visual gate per selected candidate: exact source + four actual
  Godot angles under normal game light, after verified fresh import.
- Batches of about 10 related non-unit assets; units one at a time as careful
  pilots.
- Exception tools (neutral lighting, macro captures, pixel/ray probes, readback
  renders, stress tests, map assemblies) only for a real risk, new method,
  shared-helper change or visible mismatch; reuse valid frozen batch proofs.
- Compact revision queue (asset, revision/hash, owner, severity, discrepancy,
  image path). Blockers fixed immediately; major errors stay unapproved; polish
  batched later.
- Never waived: wrong references, inverted/inward geometry, role-mismatched
  UV/material, unrooted anatomy, stale imports, missing source features, opaque
  attachment failures.
- Trial success metric: more genuinely useful assets with no increase in major
  source/anatomy/import defects; after two batches per family compare effort,
  rejections and regressions; tighten only failing families.

## Later amendments (same policy line)

- 2026-10-01: orchestration handed to Claude Opus 5.5 as root; workers are Opus
  subagents (~10 assets per batch, one unit per worker); GPT workers parked.
- 2026-10-02: "finish models first": build and export the batch, list small
  imperfections, move on; consistency across a family over pixel-exact counts;
  pacing note that environment microdetail is already good (no tiny modelled
  cracks).
- 2026-10-07: test only the new feature, no regression/sanity passes; one test
  client at a time (lock); muted test runs; no unneeded animation clips.

## Why it worked

Most rework came from wrong source reading, generic geometry and bad exports,
which the cheap gates and one exact-source visual gate still catch. The
three-trial matrix mostly produced near-identical options. Root throughput went
from a few assets a day to families completed per day (URBAN 000-111, JUNGLE,
XBASE1 000-061 approved by 2026-10-02).

## Sources

XCOM `art/review/workflow_snapshots/20260930-strict-QUALITY_CONTRACT.md`,
`20260930-strict-TEAM_REQUIREMENTS.md`, `art/QUALITY_CONTRACT.md`,
`art/TEAM_REQUIREMENTS.md`, `art/team/ORCHESTRATION_OPUS55.md`,
`art/review/opus_batches.md`, `art/team/terrain_rebuild/research/coverage-first-workflows.md`.
