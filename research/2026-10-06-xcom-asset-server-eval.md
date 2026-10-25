# XCOM 2026-10-06: third-party asset search (3d-asset-server / 3d.shep.bot) evaluation

Status: REJECTED for now (user). Kept for reference. Licence ruling from the
same day: any free asset is acceptable (CC0, CC-BY, BlenderKit free/RF, other
free licences) provided source, licence and attribution are recorded.

## Tools

- arielshad/3d-asset-server (Apache-2.0, Node/TS): one keyword search over 18
  sources with licence, price, polycount and rigged flags; direct downloads from
  Poly Haven, ambientCG, BlenderKit (free, no login), Kenney, TextureCan,
  HDRMaps; others as links. No keys; local run logs nothing; 2 GB cap.
- 3d.shep.bot: hosted copy (REST, MCP, web UI, 120 req/min), logs search text
  server-side, no ToS page. Results matched a local clone (629/630 ids).
Recommendation: local clone via MCP if used by agents.

## Test (world assets only, budgets terrain 4k / vegetation 6k)

Every over-budget candidate got a real Blender decimation test (outline overlap
1.0 = unchanged, degenerate triangles, UV survival, game-zoom + close renders).
- Spruce (BlenderKit RF, alpha cards) 231,058 tris: decimation stalls at 8,603,
  outline 0.30: rejected. Poly Haven fir/pine 7.9M-17.4M, 1k glTF 487-958 MB.
  Best matching spruce was paid.
- Bushes/grass in budget (1,164-3,319) but tiny sprigs, weak or partial match.
- Boulders 59k-66k tris decimated cleanly to 3,880 (outline 0.993-0.994) after
  welding split vertices; need hue shift, re-pivot, rebake.
- Armchairs 5k-271k decimated cleanly to ~3,880 (0.994-0.999); style/colour off.
- Materials: CC0 PBR sets download in one call, sometimes with Godot .tres.

## Gotchas

BlenderKit "polyCount" counts faces (real tris ~2x); geometry-node assets list 1
polygon; keyword-only search; CGTrader bot-blocked; HDRMaps HTTP 500; duplicate
GLB downloads; deep folders exceed the Windows path limit.

## Verdict

Rocks/solid props: usable starting meshes but about the same effort as an
in-house build. Trees/bushes/grass: not useful; keep the foliage-card rebuild.
Materials: the strongest use. Safe to ship without a ruling: CC0 only
(BlenderKit RF forbids redistribution "in the same form").

## Sources

XCOM `art/team/research/asset_server_eval/REPORT.md` (+ candidates.json).
