# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/guns_v2/lib/gltf_io.py (imported 2026-10-25)
# Changed: header only (byte-identical copy also in items_opus55/lib)
"""Minimal glTF readers for the items_opus55 seal/gate scripts (system Python + numpy)."""
import json
from pathlib import Path
from urllib.parse import unquote

import numpy as np

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load(path):
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    bins = [(path.parent / unquote(b["uri"])).read_bytes() for b in doc["buffers"]]
    return doc, bins


def accessor(doc, bins, i, raw=False):
    a = doc["accessors"][i]
    v = doc["bufferViews"][a["bufferView"]]
    dt = COMP[a["componentType"]]
    w = WIDTH[a["type"]]
    start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = v.get("byteStride", 0)
    data = bins[v["buffer"]]
    n = a["count"]
    if stride and stride != np.dtype(dt).itemsize * w:
        arr = np.array([np.frombuffer(data, dt, w, start + k * stride) for k in range(n)])
    else:
        arr = np.frombuffer(data, dt, n * w, start).reshape(n, w)
    return arr if raw else arr.astype(np.float64)


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def node_local(n):
    if "matrix" in n:
        return np.array(n["matrix"], np.float64).reshape(4, 4).T
    M = np.eye(4)
    R = quat_mat(n.get("rotation", [0, 0, 0, 1]))
    S = np.diag(n.get("scale", [1, 1, 1]))
    M[:3, :3] = R @ S
    M[:3, 3] = n.get("translation", [0, 0, 0])
    return M


def world_matrices(doc):
    parent = {}
    for i, n in enumerate(doc["nodes"]):
        for c in n.get("children", []):
            parent[c] = i
    out = {}

    def w(i):
        if i in out:
            return out[i]
        M = node_local(doc["nodes"][i])
        if i in parent:
            M = w(parent[i]) @ M
        out[i] = M
        return M
    for i in range(len(doc["nodes"])):
        w(i)
    return out, parent


def mesh_nodes(doc):
    return [(i, n) for i, n in enumerate(doc["nodes"]) if "mesh" in n]


def world_positions(doc, bins):
    """All mesh vertices in item (scene) space, per mesh node."""
    W, _ = world_matrices(doc)
    res = {}
    for i, n in mesh_nodes(doc):
        P = []
        for prim in doc["meshes"][n["mesh"]]["primitives"]:
            p = accessor(doc, bins, prim["attributes"]["POSITION"])
            P.append(p)
        P = np.vstack(P)
        M = W[i]
        res[n.get("name", str(i))] = (P @ M[:3, :3].T) + M[:3, 3]
    return res
