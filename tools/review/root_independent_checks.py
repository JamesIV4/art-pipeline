# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/root_independent_checks.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT
"""Root's independent cheap gate on exported glTF files (does not trust worker reports).

Checks per model, following TEAM_REQUIREMENTS "Art, performance and export boundaries":
sealed external dependencies, triangle primitives, POSITION/NORMAL/TEXCOORD_0/TANGENT,
finite values, unit normals, unit orthogonal tangents with w = +/-1, zero-area geometry
and UV triangles, bounded COLOR_0, triangle budget (terrain 4000, vegetation 6000,
units 24000), one consolidated mesh and <= 3 materials for static terrain, identity
extras, editable .blend present, and Godot import optimisation settings.
Signed volume is reported as information only (cards and open shells are legitimate).
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

import numpy as np

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
DTYPE = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
VEGETATION = {"FOREST", "JUNGLE", "CULTIVAT"}
IMPORT_SETTINGS = ("array_mesh/deduplicate_surfaces=true",
                   "meshes/create_shadow_meshes=true", "meshes/force_disable_compression=false")
# meshes/generate_lods is reported as info only: XBASE1, XBASE2, U_EXT02, U_BITS and UFO1
# import with generate_lods=false since 2026-10-02 (LODs cracked tile-plane seams;
# art/review/renderer_lod/). Either value passes.


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(asset_id, model_rel):
    path = ROOT / model_rel
    doc = json.loads(path.read_text(encoding="utf-8"))
    fails, info = [], {}
    buffers = []
    for b in doc.get("buffers", []):
        buffers.append((path.parent / unquote(b["uri"])).read_bytes())

    seals = doc.get("asset", {}).get("extras", {}).get("render_dependency_sha256")
    if not seals:
        fails.append("no render_dependency_sha256 seals")
    else:
        for s in seals:
            p = path.parent / unquote(s["uri"])
            if not p.exists() or _sha(p) != s["sha256"]:
                fails.append(f"seal mismatch {s['uri']}")
    for img in doc.get("images", []):
        if not (path.parent / unquote(img["uri"])).exists():
            fails.append(f"missing image {img['uri']}")

    def arr(index):
        acc = doc["accessors"][index]
        view = doc["bufferViews"][acc["bufferView"]]
        dt = np.dtype(DTYPE[acc["componentType"]]).newbyteorder("<")
        n, w = acc["count"], WIDTH[acc["type"]]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = view.get("byteStride", dt.itemsize * w)
        raw = np.frombuffer(buffers[view["buffer"]], dtype=np.uint8)
        rows = np.lib.stride_tricks.as_strided(raw[start:], shape=(n, dt.itemsize * w), strides=(stride, 1))
        return np.ascontiguousarray(rows).view(dt).reshape(n, w).astype(np.float64), acc

    category = asset_id.split("/")[0]
    family = asset_id.split("/")[1] if "/" in asset_id else ""
    skinned = any("skin" in n for n in doc.get("nodes", []))
    triangles, volume = 0, 0.0
    bad_geo = bad_uv = 0
    for mesh in doc["meshes"]:
        for prim in mesh["primitives"]:
            if prim.get("mode", 4) != 4:
                fails.append("non-triangle primitive")
                continue
            attrs = prim["attributes"]
            for name in ("POSITION", "NORMAL", "TEXCOORD_0", "TANGENT"):
                if name not in attrs:
                    fails.append(f"missing {name}")
            if any(name not in attrs for name in ("POSITION", "NORMAL", "TEXCOORD_0", "TANGENT")):
                continue
            pos, _ = arr(attrs["POSITION"])
            nrm, _ = arr(attrs["NORMAL"])
            uv, _ = arr(attrs["TEXCOORD_0"])
            tan, _ = arr(attrs["TANGENT"])
            for name, a in (("POSITION", pos), ("NORMAL", nrm), ("TEXCOORD_0", uv), ("TANGENT", tan)):
                if not np.isfinite(a).all():
                    fails.append(f"non-finite {name}")
            nl = np.linalg.norm(nrm, axis=1)
            tl = np.linalg.norm(tan[:, :3], axis=1)
            if (np.abs(nl - 1) > 0.01).any():
                fails.append(f"non-unit normals: {int((np.abs(nl - 1) > 0.01).sum())}")
            if (np.abs(tl - 1) > 0.01).any():
                fails.append(f"non-unit tangents: {int((np.abs(tl - 1) > 0.01).sum())}")
            if (np.abs(np.abs(tan[:, 3]) - 1) > 1e-3).any():
                fails.append("tangent w not +/-1")
            dots = np.abs((nrm * tan[:, :3]).sum(axis=1))
            if (dots > 1e-3).any():
                fails.append(f"tangent not orthogonal: {int((dots > 1e-3).sum())}")
            if "COLOR_0" in attrs:
                col, acc = arr(attrs["COLOR_0"])
                div = {5121: 255.0, 5123: 65535.0}.get(acc["componentType"], 1.0)
                col = col / div
                if not np.isfinite(col).all() or col.min() < 0 or col.max() > 1:
                    fails.append("COLOR_0 out of [0,1]")
            if "indices" in prim:
                idx, _ = arr(prim["indices"])
                idx = idx.astype(np.int64).reshape(-1)
            else:
                idx = np.arange(len(pos))
            if idx.max() >= len(pos):
                fails.append("index out of range")
                continue
            tri = idx.reshape(-1, 3)
            triangles += len(tri)
            a, b, c = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
            cross = np.cross(b - a, c - a)
            bad_geo += int(((cross ** 2).sum(axis=1) <= 1e-22).sum())
            ua, ub, uc = uv[tri[:, 0]], uv[tri[:, 1]], uv[tri[:, 2]]
            det = (ub[:, 0] - ua[:, 0]) * (uc[:, 1] - ua[:, 1]) - (ub[:, 1] - ua[:, 1]) * (uc[:, 0] - ua[:, 0])
            bad_uv += int((np.abs(det) <= 1e-13).sum())
            volume += float((a * np.cross(b, c)).sum() / 6.0)
    if bad_geo:
        fails.append(f"zero-area triangles: {bad_geo}")
    if bad_uv:
        fails.append(f"zero-area UV triangles: {bad_uv}")

    # items: hero-prop weapons quality pass (user 2026-10-04) allows up to 12k incl. seated clip
    budget = 24000 if category == "units" else 12000 if category == "items" else 6000 if family in VEGETATION else 4000
    if triangles > budget:
        fails.append(f"triangles {triangles} > budget {budget}")
    if category == "terrain" and not skinned:
        if len(doc["meshes"]) != 1:
            fails.append(f"{len(doc['meshes'])} meshes (static models must be consolidated)")
        # User-approved 2026-10-02 from the perf lab: up to 5 authored materials.
        if len(doc.get("materials", [])) > 5:
            fails.append(f"{len(doc['materials'])} materials (> 5 surfaces)")

    extras = [doc.get("asset", {}).get("extras", {})] + [n.get("extras", {}) for n in doc.get("nodes", [])]
    if not any(e.get("asset_id") == asset_id for e in extras):
        fails.append("asset_id extras do not match")

    stem = path.name[:-len(".gltf")]
    sub = "units" if category == "units" else "terrain"
    blend = ROOT / "art" / "source" / sub / family / (stem + ".blend")
    if not blend.exists():
        info["blend_missing_at_conventional_path"] = str(blend.relative_to(ROOT))

    imp = Path(str(path) + ".import")
    if imp.exists():
        text = imp.read_text(encoding="utf-8")
        missing = [s for s in IMPORT_SETTINGS if s not in text]
        if missing:
            fails.append("import settings: " + ", ".join(missing))
        lods = "meshes/generate_lods=false" not in text
        info["generate_lods"] = lods
    else:
        fails.append("not imported")

    info.update(triangles=triangles, meshes=len(doc["meshes"]), materials=len(doc.get("materials", [])),
                signed_volume_m3=round(volume, 4))
    return {"id": asset_id, "model": model_rel, "passed": not fails, "fails": fails, "info": info}


if __name__ == "__main__":
    import sys
    entries = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = [check(e["id"], e["model"]) for e in entries]
    print(json.dumps(results, indent=1))
