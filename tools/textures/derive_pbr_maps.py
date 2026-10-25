# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/derive_pbr_maps.py (imported 2026-10-25)
# Changed: header only (CLI paths)
"""Derive missing PBR maps (tangent-space normal + roughness, optional ORM) from an albedo texture.

Root-owned (2026-10-06, user request: "generate normal maps for units lacking them"). The user's Tripo
unit models ship with an albedo only, and some have a normal map. This makes the missing maps the same way
for every unit, so the results are consistent and can later be compared with a PBR-capable generator.

Method (albedo-derived detail, no high-poly source exists):
- UV island mask rasterised from the model's TEXCOORD_0. Pixels outside the islands are filled by
  push-pull, so filtering never drags the background across island edges (no seam lines).
- Height = luminance band-passed at several scales (difference of Gaussians), so bright reads as raised
  and dark crevices as recessed. Large shading gradients baked into the albedo are removed by the band-pass.
- Normal = Sobel gradient of that height, glTF / OpenGL convention (+X right, +Y up / green up).
- Roughness = a per-material base +/- local contrast (crevices rougher, raised highlights smoother).
- ORM = (AO, roughness, metallic). AO comes from --ao (e.g. a geometry AO bake from Blender), else 1.
Outside the islands: flat normal, base roughness.

    python art/tools/derive_pbr_maps.py --model unit.glb --albedo albedo.png --out-dir DIR --name UNIT \
        [--ao ao.png] [--size 2048] [--strength 2.5] [--rough-base 0.6] [--rough-var 0.18] [--metallic 0]

Writes DIR/NAME_normal.webp, DIR/NAME_roughness.webp, DIR/NAME_orm.webp (8-bit lossless WebP) and
DIR/NAME_pbr_preview.png. It never overwrites an existing file.
"""
import argparse
import json
import struct
from pathlib import Path

import cv2
import numpy as np

COMPONENTS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load_gltf(path):
    path = Path(path)
    if path.suffix.lower() == ".glb":
        data = path.read_bytes()
        n = struct.unpack_from("<I", data, 12)[0]
        doc = json.loads(data[20:20 + n])
        off = 20 + n
        bin_chunk = data[off + 8: off + 8 + struct.unpack_from("<I", data, off)[0]] if off < len(data) else b""
        buffers = [bin_chunk]
    else:
        doc = json.loads(path.read_text(encoding="utf-8"))
        buffers = [(path.parent / b["uri"]).read_bytes() for b in doc["buffers"]]
    return doc, buffers


def accessor(doc, buffers, idx):
    a = doc["accessors"][idx]
    bv = doc["bufferViews"][a["bufferView"]]
    dtype = COMPONENTS[a["componentType"]]
    width = WIDTH[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0)
    raw = buffers[bv.get("buffer", 0)]
    itemsize = np.dtype(dtype).itemsize * width
    if stride and stride != itemsize:
        rows = np.frombuffer(raw, np.uint8, count=stride * (a["count"] - 1) + itemsize, offset=start)
        out = np.lib.stride_tricks.as_strided(rows, (a["count"], itemsize), (stride, 1)).copy()
        arr = out.view(dtype).reshape(a["count"], width)
    else:
        arr = np.frombuffer(raw, dtype, count=a["count"] * width, offset=start).reshape(a["count"], width)
    if a.get("normalized") and dtype != np.float32:
        arr = arr.astype(np.float32) / np.iinfo(dtype).max
    return arr.astype(np.float32) if dtype == np.float32 or a.get("normalized") else arr


def island_mask(doc, buffers, size):
    mask = np.zeros((size, size), np.uint8)
    for mesh in doc.get("meshes", []):
        for prim in mesh["primitives"]:
            if "TEXCOORD_0" not in prim["attributes"]:
                continue
            uv = accessor(doc, buffers, prim["attributes"]["TEXCOORD_0"])
            idx = accessor(doc, buffers, prim["indices"]).reshape(-1).astype(np.int64) if "indices" in prim \
                else np.arange(len(uv))
            tri = uv[idx].reshape(-1, 3, 2)
            pts = np.round(np.mod(tri, 1.0) * (size - 1)).astype(np.int32)   # glTF UV origin = image top-left
            cv2.fillPoly(mask, list(pts), 255)
    return cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)


def push_pull(img, mask):
    """Fill img where mask == 0 from the valid pixels (coarse-to-fine average)."""
    valid = (mask > 0).astype(np.float32)
    levels = []
    v, w = img * valid[..., None] if img.ndim == 3 else img * valid, valid
    while min(w.shape[:2]) > 4:
        levels.append((v, w))
        v = cv2.resize(v, (v.shape[1] // 2, v.shape[0] // 2), interpolation=cv2.INTER_AREA)
        w = cv2.resize(w, (w.shape[1] // 2, w.shape[0] // 2), interpolation=cv2.INTER_AREA)
    fill = v / np.maximum(w if v.ndim == 2 else w[..., None], 1e-6)
    for v, w in reversed(levels):
        up = cv2.resize(fill, (v.shape[1], v.shape[0]), interpolation=cv2.INTER_LINEAR)
        ww = w if v.ndim == 2 else w[..., None]
        fill = np.where(ww > 0.999, v / np.maximum(ww, 1e-6), (v + up * (1 - ww)) / 1.0)
    return fill


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help=".glb/.gltf whose TEXCOORD_0 uses this albedo")
    ap.add_argument("--albedo", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--ao", default="", help="optional AO map (e.g. a Blender geometry AO bake)")
    ap.add_argument("--size", type=int, default=2048)
    ap.add_argument("--strength", type=float, default=1.4, help="normal strength (slope per height std)")
    ap.add_argument("--skin-soften", type=float, default=0.3,
                    help="normal strength multiplier on skin-coloured texels (skin must not read lumpy); 1 = off")
    ap.add_argument("--rough-base", type=float, default=0.6)
    ap.add_argument("--rough-var", type=float, default=0.18)
    ap.add_argument("--metallic", type=float, default=0.0)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = {k: out_dir / f"{args.name}_{k}" for k in ("normal.webp", "roughness.webp", "orm.webp", "pbr_preview.png")}
    for p in outs.values():
        if p.exists():
            raise SystemExit(f"refusing to overwrite {p}")

    size = args.size
    albedo = cv2.imread(args.albedo, cv2.IMREAD_COLOR)
    if albedo is None:
        raise SystemExit(f"cannot read {args.albedo}")
    albedo = cv2.resize(albedo, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    doc, buffers = load_gltf(args.model)
    mask = island_mask(doc, buffers, size)

    srgb = albedo[..., ::-1]                                   # BGR -> RGB
    lin = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    lum = (0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]) ** (1 / 2.2)
    lum = push_pull(lum, mask)

    k = size / 2048.0
    height = np.zeros_like(lum)
    # fine bands only: weave, stitching, seams and plate edges; broad bands mostly re-read the albedo's baked
    # shading as lumps
    for sigma, weight in ((0.7, 1.0), (1.4, 0.7), (2.8, 0.3)):
        s1, s2 = sigma * k, sigma * k * 2.5
        band = cv2.GaussianBlur(lum, (0, 0), s1) - cv2.GaussianBlur(lum, (0, 0), s2)
        height += weight * band
    inside = mask > 0
    height /= max(float(height[inside].std()), 1e-6)

    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    # skin-coloured texels (warm hue, moderate saturation) get a softened normal
    hsv = cv2.cvtColor((albedo * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[..., 0] * 2.0, hsv[..., 1] / 255.0, hsv[..., 2] / 255.0
    skin = ((h >= 4) & (h <= 32) & (s >= 0.18) & (s <= 0.7) & (v >= 0.35)).astype(np.float32)
    skin = cv2.GaussianBlur(skin, (0, 0), 3.0 * k)
    strength = args.strength * (1.0 - skin * (1.0 - args.skin_soften))
    n = np.dstack([-gx * strength, gy * strength, np.ones_like(gx)])   # image y is down = -v
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    n[~inside] = (0.0, 0.0, 1.0)
    normal = np.clip((n * 0.5 + 0.5) * 255.0 + 0.5, 0, 255).astype(np.uint8)

    local = lum - cv2.GaussianBlur(lum, (0, 0), 8.0 * k)
    local /= max(float(local[inside].std()), 1e-6)
    rough = np.clip(args.rough_base - args.rough_var * np.clip(local, -1.5, 1.5) / 1.5, 0.04, 1.0)
    rough[~inside] = args.rough_base
    rough8 = np.clip(rough * 255.0 + 0.5, 0, 255).astype(np.uint8)

    if args.ao:
        ao = cv2.imread(args.ao, cv2.IMREAD_GRAYSCALE)
        ao = cv2.resize(ao, (size, size), interpolation=cv2.INTER_AREA)
    else:
        ao = np.full((size, size), 255, np.uint8)
    metal = np.full((size, size), int(round(args.metallic * 255)), np.uint8)

    webp = [cv2.IMWRITE_WEBP_QUALITY, 101]                      # 101 = lossless
    cv2.imwrite(str(outs["normal.webp"]), normal[..., ::-1], webp)
    cv2.imwrite(str(outs["roughness.webp"]), rough8, webp)
    cv2.imwrite(str(outs["orm.webp"]), np.dstack([metal, rough8, ao]), webp)   # BGR -> R=AO, G=rough, B=metal

    third = size // 2
    prev = np.hstack([
        cv2.resize((albedo * 255).astype(np.uint8), (third, third)),
        cv2.resize(normal[..., ::-1], (third, third)),
        cv2.resize(cv2.cvtColor(rough8, cv2.COLOR_GRAY2BGR), (third, third)),
        cv2.resize(cv2.cvtColor(ao, cv2.COLOR_GRAY2BGR), (third, third)),
    ])
    cv2.imwrite(str(outs["pbr_preview.png"]), prev)
    print(f"{args.name}: islands {inside.mean():.1%} of the atlas; wrote", ", ".join(p.name for p in outs.values()))


if __name__ == "__main__":
    main()
