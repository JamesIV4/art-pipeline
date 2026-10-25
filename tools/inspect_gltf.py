"""Reports bounds, sockets, palette cells used (and which are glow), and per-cell bounds for
exported catalog assets. Plain Python, no Blender.

Origin: S:/Repos/trick-or-treat/art/team/landmarks/batch03/inspect_gltf.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py; grid from the palette_grid setting.

    python <pipeline>/tools/inspect_gltf.py <asset_id> [<cell> ...]
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates  # noqa: E402
import pipeline_paths as P  # noqa: E402

CELLS = json.loads((P.path("palette_out") / "palette_cells.json").read_text())
BYPOS = {(c["col"], c["row"]): n for n, c in CELLS.items()}
GRID = int(P.setting("palette_grid"))


def main(aid, focus):
    asset = next(a for a in gates.CATALOG if a["id"] == aid)
    path = gates.MODELS / f"{asset['path']}.gltf"
    g = json.loads(path.read_text())
    bins = [(path.parent / b["uri"]).read_bytes() for b in g["buffers"]]
    lo, hi = [1e9] * 3, [-1e9] * 3
    cells = {}
    for node in g["nodes"]:
        if "mesh" not in node:
            if node.get("name", "").startswith("socket_"):
                print("socket", node["name"], node.get("translation"))
            continue
        for prim in g["meshes"][node["mesh"]]["primitives"]:
            pos = gates.read_accessor(g, bins, prim["attributes"]["POSITION"])
            tint = gates.read_accessor(g, bins, prim["attributes"]["TEXCOORD_1"])
            for p, (u, v) in zip(pos, tint):
                for k in range(3):
                    lo[k] = min(lo[k], p[k])
                    hi[k] = max(hi[k], p[k])
                u -= math.floor(u)
                name = BYPOS.get((int(u * GRID), int(v * GRID)), "?")
                b = cells.setdefault(name, [[1e9] * 3, [-1e9] * 3, 0])
                for k in range(3):
                    b[0][k] = min(b[0][k], p[k])
                    b[1][k] = max(b[1][k], p[k])
                b[2] += 1
    f = lambda xs: "(" + ", ".join(f"{x:.3f}" for x in xs) + ")"  # noqa: E731
    print(f"{aid}: bounds min {f(lo)} max {f(hi)} size {f([h - l for l, h in zip(lo, hi)])}  (glTF Y-up)")
    print("glow cells:", sorted(n for n in cells if n.startswith("glow_")))
    print("cells:", sorted(cells))
    for n in focus:
        if n in cells:
            print(f"  {n}: min {f(cells[n][0])} max {f(cells[n][1])} verts {cells[n][2]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
