"""Origin: S:/Repos/trick-or-treat/art/tools/gates.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. Floating prefixes/ids, grid and ground tolerance are settings.

Cheap automated gates for exported assets. Plain Python, no Blender needed.

        python <pipeline>/tools/gates.py <asset_id> [<asset_id> ...]   # check specific assets
    python <pipeline>/tools/gates.py --all                         # every catalog asset that exists
    python <pipeline>/tools/gates.py --lane yard_street            # one lane
(run from the game root, or set ART_GAME_ROOT)

Checks each <models_out>/<path>.gltf against the game's catalog (default art/asset_catalog.json):
  exists, triangle budget, palette gate (every UV within 1/4 cell of a cell centre and not on an
  unused cell), no degenerate triangles, ground origin (min height within 3 cm of 0) unless the
  asset floats (candy, sky, lanterns that hang), required parts and sockets present.
Exit code 1 if any gate fails. Prints one line per asset plus failures.
"""
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_paths as P  # noqa: E402

ROOT = P.GAME_ROOT
CATALOG = json.loads(P.path("catalog").read_text())["assets"]
CELLS = json.loads((P.path("palette_out") / "palette_cells.json").read_text())
MODELS = P.path("models_out")
FLOATING_PREFIXES = tuple(P.setting("floating_prefixes"))
FLOATING_IDS = set(P.setting("floating_ids"))
GROUND_TOLERANCE = float(P.setting("ground_tolerance_m"))
GRID = int(P.setting("palette_grid"))
USED = {(c["col"], c["row"]) for c in CELLS.values()}
N_LAYERS = len(json.loads(P.path("materials_spec").read_text())["layers"])

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_accessor(gltf, bins, idx):
    acc = gltf["accessors"][idx]
    view = gltf["bufferViews"][acc["bufferView"]]
    fmt, size = COMP[acc["componentType"]]
    n = NCOMP[acc["type"]]
    stride = view.get("byteStride", size * n)
    data = bins[view["buffer"]]
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    out = []
    for i in range(acc["count"]):
        off = base + i * stride
        out.append(struct.unpack_from("<" + fmt * n, data, off))
    return out


def mat_mul(a, b):
    return [sum(a[r + 4 * k] * b[k + 4 * c] for k in range(4)) for c in range(4) for r in range(4)]


def node_matrix(node):
    if "matrix" in node:
        return node["matrix"]
    t = node.get("translation", [0, 0, 0])
    q = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    x, y, z, w = q
    r = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
         2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
         2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
         0, 0, 0, 1]
    for col in range(3):
        for row in range(3):
            r[col * 4 + row] *= s[col]
    r[12], r[13], r[14] = t
    return r


def apply(m, p):
    return (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
            m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
            m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])


def check(asset):
    path = MODELS / f"{asset['path']}.gltf"
    fails = []
    if not path.exists():
        return {"id": asset["id"], "pass": False, "fails": ["missing export"], "tris": 0}
    gltf = json.loads(path.read_text())
    bins = [(path.parent / b["uri"]).read_bytes() for b in gltf.get("buffers", [])]
    names = {n.get("name", "") for n in gltf.get("nodes", [])}
    tris = 0
    degenerate = 0
    off_palette = 0
    bad_layer = 0
    untextured_flags = set()
    missing_ao = set()
    min_y = math.inf
    nodes = gltf.get("nodes", [])
    world = {}

    def walk(i, parent):
        m = mat_mul(parent, node_matrix(nodes[i]))
        world[i] = m
        for c in nodes[i].get("children", []):
            walk(c, m)

    ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    for scene in gltf.get("scenes", []):
        for root in scene.get("nodes", []):
            walk(root, ident)
    for ni, node in enumerate(nodes):
        if "mesh" not in node:
            continue
        m = world.get(ni, ident)
        for prim in gltf["meshes"][node["mesh"]]["primitives"]:
            pos = read_accessor(gltf, bins, prim["attributes"]["POSITION"])
            idx = read_accessor(gltf, bins, prim["indices"]) if "indices" in prim else [(i,) for i in range(len(pos))]
            idx = [i[0] for i in idx]
            tris += len(idx) // 3
            wpos = [apply(m, p) for p in pos]
            min_y = min(min_y, min(p[1] for p in wpos))
            for t in range(0, len(idx) - 2, 3):
                a, b, c = (wpos[idx[t]], wpos[idx[t + 1]], wpos[idx[t + 2]])
                u = [b[k] - a[k] for k in range(3)]
                v = [c[k] - a[k] for k in range(3)]
                cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
                if math.sqrt(sum(x * x for x in cr)) < 1e-8:
                    degenerate += 1
            attrs = prim["attributes"]
            if "TEXCOORD_0" not in attrs:
                fails.append("no UVs")
                continue
            textured = "TEXCOORD_1" in attrs
            if textured:
                untextured_flags.discard("x")
                if "COLOR_0" not in attrs:
                    missing_ao.add(1)
            else:
                untextured_flags.add("legacy")
            tint_key = "TEXCOORD_1" if textured else "TEXCOORD_0"
            for u, v in read_accessor(gltf, bins, attrs[tint_key]):
                layer = int(math.floor(u)) if textured else 0
                if textured and not (0 <= layer < N_LAYERS):
                    bad_layer += 1
                u = u - math.floor(u) if textured else u
                cx, cy = u * GRID, v * GRID
                col, row = int(math.floor(cx)), int(math.floor(cy))
                if abs(cx - (col + 0.5)) > 0.25 or abs(cy - (row + 0.5)) > 0.25 or (col, row) not in USED:
                    off_palette += 1
    if tris > asset["tris"]:
        fails.append(f"triangles {tris} > budget {asset['tris']}")
    if off_palette:
        fails.append(f"palette gate: {off_palette} UVs off palette cell centres")
    if bad_layer:
        fails.append(f"material gate: {bad_layer} UVs name a material layer outside 0..{N_LAYERS - 1}")
    if missing_ao:
        fails.append("no AO vertex colours (COLOR_0); call K.bake_ao before export")
    warnings = ["untextured legacy export (no Tint UV); rebuild with lowpoly_kit v2"] if "legacy" in untextured_flags else []
    if degenerate:
        fails.append(f"{degenerate} degenerate triangles")
    # Hanging/wall assets (origin at the hang point) opt out of the ground gate with "floating": true.
    floating = (asset["path"].startswith(FLOATING_PREFIXES) or asset["id"] in FLOATING_IDS
                or asset.get("floating", False))
    if not floating and abs(min_y) > GROUND_TOLERANCE:
        fails.append(f"origin not at ground: min height {min_y:.3f} m")
    for part in asset.get("parts", []):
        if part not in names:
            fails.append(f"missing part node '{part}'")
    for s in asset.get("sockets", []):
        if f"socket_{s}" not in names:
            fails.append(f"missing socket_{s}")
    return {"id": asset["id"], "pass": not fails, "fails": fails, "tris": tris, "warnings": warnings}


def main(argv):
    if "--all" in argv:
        targets = [a for a in CATALOG if (MODELS / f"{a['path']}.gltf").exists()]
    elif "--lane" in argv:
        lane = argv[argv.index("--lane") + 1]
        targets = [a for a in CATALOG if a["lane"] == lane]
    else:
        ids = set(argv)
        targets = [a for a in CATALOG if a["id"] in ids]
        unknown = ids - {a["id"] for a in targets}
        if unknown:
            print("unknown ids:", ", ".join(sorted(unknown)))
    ok = True
    for asset in targets:
        r = check(asset)
        ok &= r["pass"]
        print(f"{'PASS' if r['pass'] else 'FAIL'} {r['id']:<24} tris {r['tris']:>5}/{asset['tris']}")
        for f in r["fails"]:
            print(f"     - {f}")
        for w in r.get("warnings", []):
            print(f"     ~ {w}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
