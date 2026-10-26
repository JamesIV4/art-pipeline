# research/

Dated research notes and retrospectives: `YYYY-MM-DD-<game>-<topic>.md`, dated when the work
happened. Each keeps the findings, the numbers, the decision and what was rejected and why. They are
history: when a finding becomes a standing method, distil it into `techniques/` and link back here;
don't edit old notes except to add a "Superseded by" line.

| Note | Summary |
|---|---|
| [2026-09-29-xcom-workflow-research-and-environment-audit.md](2026-09-29-xcom-workflow-research-and-environment-audit.md) | first workflow decisions; audit that caught generic-benchmark comparison sheets |
| [2026-09-30-xcom-coverage-first-policy.md](2026-09-30-xcom-coverage-first-policy.md) | strict per-asset contract to coverage-first-v1, and later amendments |
| [2026-09-30-xcom-vegetation-orientation-audit.md](2026-09-30-xcom-vegetation-orientation-audit.md) | dead fronds read as wood; the bend-direction bug |
| [2026-10-01-xcom-garment-solidify-saga.md](2026-10-01-xcom-garment-solidify-saga.md) | garment v01-v11 and the delete-group fix |
| [2026-10-01-xcom-sectoid-unit-lab.md](2026-10-01-xcom-sectoid-unit-lab.md) | first runtime unit check (ragdoll, blood) |
| [2026-10-01-xcom-polar-water-morph-pilot.md](2026-10-01-xcom-polar-water-morph-pilot.md) | water morph iterations and the engine method gate |
| [2026-10-02-xcom-perf-lab-materials.md](2026-10-02-xcom-perf-lab-materials.md) | material count is a CPU-only cost |
| [2026-10-02-xcom-lighting-and-reflection-decisions.md](2026-10-02-xcom-lighting-and-reflection-decisions.md) | global calibration rejected; neutral reflection sky applied |
| [2026-10-02-xcom-renderer-phase1-and-lod.md](2026-10-02-xcom-renderer-phase1-and-lod.md) | chunks, shadow fit, textures; the LOD study |
| [2026-10-02-xcom-foliage-lettuce-and-waxy-response.md](2026-10-02-xcom-foliage-lettuce-and-waxy-response.md) | foliage rebuild and the waxy leaf recipe |
| [2026-10-06-xcom-asset-server-eval.md](2026-10-06-xcom-asset-server-eval.md) | third-party asset search tested; rejected |
| [2026-10-07-xcom-revision-queue-patterns.md](2026-10-07-xcom-revision-queue-patterns.md) | six recurring failure classes in the revision queue |
| [2026-10-07-xcom-tripo-hands.md](2026-10-07-xcom-tripo-hands.md) | hands on generated characters, and the user's correction |
| [2026-10-13-xcom-shared-ground-materials.md](2026-10-13-xcom-shared-ground-materials.md) | shared ground and scatter trials, readability numbers |
| [2026-10-16-xcom-render-cost-sweep.md](2026-10-16-xcom-render-cost-sweep.md) | in-game GPU cost of each render setting |
| [2026-10-24-tot-audio-direction.md](2026-10-24-tot-audio-direction.md) | AdLib FM chosen; square-wave chiptune rejected |
| [2026-10-24-tot-material-textures.md](2026-10-24-tot-material-textures.md) | painted material pass: per-layer attempts and fixes |
| [2026-10-24-tot-platforming-feedback-art.md](2026-10-24-tot-platforming-feedback-art.md) | platformer feedback research and its art requirements |
| [2026-10-24-tot-v1-to-v2-retro.md](2026-10-24-tot-v1-to-v2-retro.md) | flat to textured rebuild across lanes |
| [2026-10-25-tot-candy-variety-retro.md](2026-10-25-tot-candy-variety-retro.md) | 84 pickups, tiers, three iterations |
| [2026-10-25-tot-concept-fidelity-retro.md](2026-10-25-tot-concept-fidelity-retro.md) | concept-matching pass and what the user reverted |
| [2026-10-25-tot-creatures-props-retro.md](2026-10-25-tot-creatures-props-retro.md) | monsters, thorn vines, trampolines, fire wand |
| [2026-10-26-tot-polish-pass-retro.md](2026-10-26-tot-polish-pass-retro.md) | costumes, cleared houses, signs, clouds; trailer re-shoot; upscalers rejected; icon |

Deliberately not imported: XCOM's `art/review/web_archive_20261010` deployment READMEs (repetitive),
the per-batch staging/validation JSON dumps, logs, and the full 50 KB revision queue (distilled into
the patterns note).
