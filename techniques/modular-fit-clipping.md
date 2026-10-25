# Modular fit: allowed volume per tile part and offline clipping

## What it is

Every modular tile part owns an allowed volume in the tile frame. Geometry
outside it is cut off offline (new variant files), and a gate fails any
non-whitelisted model that pokes out of its volume or whose wall ends / floor
edges are not exactly on the cell boundary. Junctions are then resolved at
runtime by snapping wall end vertices.

## Why

In XCOM's barn test, interior walls and floor edges showed through outer walls,
neighbouring tiles z-fought on coplanar faces, and walls ended slightly short
or long of the boundary (slits and overlaps). Runtime clip planes were
considered and rejected in favour of offline clipping.

## How: the volume rules (glTF frame: Y up, -Z north, +X east, tile centred on
origin, walking surface y = 0, tile 2 m, level sqrt(6) m)

- Floors own the cell (x, z in [-1, 1]), clipped strictly; edge vertices sit on
  the boundary planes within 0.5 mm; a 2.5 cm edge zone free of trim/bevel so a
  runtime floor-edge snap finds them.
- Objects own the cell; objects with "big wall" edge flags (W, N, E, S, E+S,
  W+N) also own the outer wall band on those edges.
- Walls (west/north, plus fence/rail parts following an edge):
  - ACROSS: the wall band straddles the tile edge (north walls about -1.05 to
    -0.8 with the edge at -1.0; west mirrored). Derive each set's standard band
    from its correctly placed walls; clip anything thicker plus tolerance.
    The outer face must sit 1-2 cm beyond the edge; sets with the outer face ON
    the edge get their outer skin pushed out 2 cm.
  - ALONG: clip exactly at +-1.0 (<= 1 mm tolerance). Collinear neighbours meet
    flush; a T-stem ends inside the through-wall's band and is buried.
  - Ends: planar cap on the boundary plane only where a cut opens a closed
    volume; end vertices exactly on the boundary (0.5 mm); no trim within 3 cm of
    the end (the tool cuts 3 cm in, extrudes the clean cross-section, caps).
  - Outer L-corners leave a ~5x5 cm square no wall owns; do not extend walls to
    fill it. Junction posts were rejected; L/T/X junctions use a runtime
    per-instance end-snap (ends move by half the band thickness per context).
- Vertical: y in [-0.30, sqrt(6) + 5 mm]; slabs and belly plating may go lower;
  nothing passes through the floor above. Vertical clipping needs a flag and a
  human look.
- Related family rules: walls/door heads/columns run from 10 mm below their
  floor to 5 mm below LEVEL (sqrt(6) - 0.005); slab edges on a wall's outer face
  inset 2 mm; stair sides on a wall face pulled in 5 mm; no coplanar visible
  faces with a neighbour within ~5 mm (embed 1-2 cm instead).

## How: tool and pipeline

XCOM `art/tools/modular_fit.py` (port: `kits/xcom/`):
`scan [--only ...] [--json] [--txt]`, `check --models ids_models.json` (gate,
exit 1), `clip --id <id> --variant <v> [--vertical]`, `bands` (per-set wall bands
for the runtime snap), `fit --src scratch.gltf --dst final.gltf --id <id>`
(export hook). Clip pass: push outer skin if needed -> cut exactly on limit
planes (caps only where a volume opens, planar UV, own material) -> snap end/edge
loops that stop <= 1 cm short onto the boundary (flatten <= 3 mm bevels) ->
simplify unclean wall end zones. UVs/normals/tangents/materials carried
through; every output is a NEW file and re-sealed. `check()` has the same shape
as the independent gate's check so the batch gate can call it.

## Whitelist (reported, never clipped)

Craft and multi-tile masters cut on tile planes, vegetation, organic props,
natural-terrain details (reshape instead), corner posts and edge bars centred
on the edge by design, special hull rings (root decision), legacy drafts.
Extend with a reason.

## Gotchas

- Designed gaps and chamfers (board gaps 7-9 mm, 10 mm floor chamfers forming a
  20 mm groove) fail a strict 2.5 cm floor edge zone; decide per family whether
  to remodel or relax the rule.
- Mirrored drafts: 14 north walls had their wall on the SOUTH edge and stairs
  rose the wrong way and were built for a 3 m level; a scan of band positions
  catches these. Re-export mirrored about the tile centre; fix height scale by
  0.8165 (sqrt(6)/3).
- Clipping is a new ranked variant above the approved one; promote with an
  explicit `--only` gate pass.

## Source

- XCOM `art/team/ORCHESTRATION_OPUS55.md` ("Modular fit: allowed volume per part")
- XCOM `art/tools/modular_fit.py` docstring
- XCOM `art/review/opus_revision_queue.md` (offline clipping, fit paused,
  floors failing edge rule, mirrored draft walls)
- XCOM `art/team/environment_replacement/batches/urban26_opus/research.md`,
  `urban27_opus/research.md` (top rule, insets)
