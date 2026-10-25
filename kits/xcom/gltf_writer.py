# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/gltf_writer.py (imported 2026-10-25)
# Changed: header only (stdlib glTF writer, no paths)
"""Minimal GLTF_SEPARATE writer (Y-up) for one consolidated static mesh with external shared textures.

Blender (X east, Y north, Z up) -> glTF (X, Z, -Y). UV v flipped (glTF origin top-left). Tangent w kept
(proper rotation). Images are referenced by relative path; a texture whose .png is missing but whose
.webp exists is referenced through EXT_texture_webp. asset.extras gets render_dependency_sha256
(.bin + every image) before the .gltf is written.
"""
import hashlib
import json
import os
import struct
from pathlib import Path


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _resolve_image(path):
    p = Path(path)
    if p.exists():
        return p, False
    w = p.with_suffix(".webp")
    if w.exists():
        return w, True
    raise FileNotFoundError(path)


def write(gltf_path, bufs, materials, extras, node_name):
    """bufs: {mat_name: dict(pos, nrm, uv, tan, idx)}; materials: {mat_name: dict(albedo, normal, orm, emissive?,
    base_factor, emissive_factor, metallic, roughness)} with absolute image paths."""
    gltf_path = Path(gltf_path)
    bin_path = gltf_path.with_suffix(".bin")
    for p in (gltf_path, bin_path):
        if p.exists():
            raise FileExistsError(p)
    blob = bytearray()
    views, accessors, prims = [], [], []
    images, textures, mats = [], [], []
    img_index = {}
    use_webp = False

    def view(data, target=None):
        while len(blob) % 4:
            blob.append(0)
        off = len(blob)
        blob.extend(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        views.append(v)
        return len(views) - 1

    def tex(path):
        nonlocal use_webp
        rp, webp = _resolve_image(path)
        if str(rp) not in img_index:
            uri = os.path.relpath(rp, gltf_path.parent).replace("\\", "/")
            images.append({"uri": uri, "mimeType": "image/webp" if webp else "image/png", "name": rp.name})
            t = {"sampler": 0}
            if webp:
                t = {"sampler": 0, "extensions": {"EXT_texture_webp": {"source": len(images) - 1}}}
                use_webp = True
            else:
                t["source"] = len(images) - 1
            textures.append(t)
            img_index[str(rp)] = len(textures) - 1
        return img_index[str(rp)]

    for mi, (name, b) in enumerate(sorted(bufs.items())):
        if not b["idx"]:
            continue
        m = materials[name]
        md = {"name": name, "pbrMetallicRoughness": {"baseColorTexture": {"index": tex(m["albedo"])},
                                                     "metallicRoughnessTexture": {"index": tex(m["orm"])},
                                                     "metallicFactor": m.get("metallic", 1.0),
                                                     "roughnessFactor": m.get("roughness", 1.0)},
              "normalTexture": {"index": tex(m["normal"])},
              "occlusionTexture": {"index": tex(m["orm"])}}
        if m.get("base_factor"):
            md["pbrMetallicRoughness"]["baseColorFactor"] = list(m["base_factor"]) + [1.0]
        if m.get("emissive"):
            md["emissiveTexture"] = {"index": tex(m["emissive"])}
            md["emissiveFactor"] = list(m.get("emissive_factor", (1.0, 1.0, 1.0)))
        if m.get("extras"):
            md["extras"] = m["extras"]
        mats.append(md)
        pos = [(p[0], p[2], -p[1]) for p in b["pos"]]
        nrm = [(n[0], n[2], -n[1]) for n in b["nrm"]]
        tan = [(t[0], t[2], -t[1], t[3]) for t in b["tan"]]
        uv = [(u[0], 1.0 - u[1]) for u in b["uv"]]
        idx = [i for tri in b["idx"] for i in tri]
        n = len(pos)
        a_pos = len(accessors)
        accessors.append({"bufferView": view(struct.pack(f"<{3 * n}f", *[c for p in pos for c in p]), 34962),
                          "componentType": 5126, "count": n, "type": "VEC3",
                          "min": [min(p[i] for p in pos) for i in range(3)], "max": [max(p[i] for p in pos) for i in range(3)]})
        accessors.append({"bufferView": view(struct.pack(f"<{3 * n}f", *[c for p in nrm for c in p]), 34962),
                          "componentType": 5126, "count": n, "type": "VEC3"})
        accessors.append({"bufferView": view(struct.pack(f"<{4 * n}f", *[c for p in tan for c in p]), 34962),
                          "componentType": 5126, "count": n, "type": "VEC4"})
        accessors.append({"bufferView": view(struct.pack(f"<{2 * n}f", *[c for p in uv for c in p]), 34962),
                          "componentType": 5126, "count": n, "type": "VEC2"})
        big = n > 65535
        accessors.append({"bufferView": view(struct.pack(f"<{len(idx)}{'I' if big else 'H'}", *idx), 34963),
                          "componentType": 5125 if big else 5123, "count": len(idx), "type": "SCALAR"})
        prims.append({"attributes": {"POSITION": a_pos, "NORMAL": a_pos + 1, "TANGENT": a_pos + 2, "TEXCOORD_0": a_pos + 3},
                      "indices": a_pos + 4, "material": len(mats) - 1, "mode": 4})
    bin_path.write_bytes(bytes(blob))
    doc = {"asset": {"version": "2.0", "generator": "AVENGER v2 writer (art/team/avenger_v2/common/gltf_writer.py)"},
           "scene": 0, "scenes": [{"nodes": [0]}],
           "nodes": [{"name": node_name, "mesh": 0, "extras": {"asset_id": extras["asset_id"]}}],
           "meshes": [{"name": node_name, "primitives": prims}],
           "materials": mats, "textures": textures, "images": images,
           "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
           "accessors": accessors, "bufferViews": views,
           "buffers": [{"uri": bin_path.name, "byteLength": len(blob)}]}
    if use_webp:
        doc["extensionsUsed"] = ["EXT_texture_webp"]
        doc["extensionsRequired"] = ["EXT_texture_webp"]
    deps = [{"uri": bin_path.name, "sha256": _sha(bin_path)}]
    for im in images:
        deps.append({"uri": im["uri"], "sha256": _sha(gltf_path.parent / im["uri"])})
    doc["asset"]["extras"] = dict(extras, render_dependency_sha256=deps)
    gltf_path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return {"gltf": str(gltf_path), "bin": str(bin_path), "gltf_sha256": _sha(gltf_path), "bin_sha256": _sha(bin_path),
            "images": [im["uri"] for im in images]}
