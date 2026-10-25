# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/gltf_opacity.py (imported 2026-10-25)
# Changed: header only
"""Base-level glTF alpha sampling in PIL's native top-left image convention."""
import math

REPEAT, CLAMP, MIRROR = 10497, 33071, 33648
NEAREST, LINEAR = 9728, 9729


def _index(i, size, wrap):
    if wrap == REPEAT:
        return i % size
    if wrap == CLAMP:
        return min(size - 1, max(0, i))
    if wrap == MIRROR:
        p = i % (2 * size)
        return p if p < size else 2 * size - 1 - p
    raise ValueError(f"Unknown glTF wrapping mode:{wrap}")


def sample_alpha(image, uv, sampler=None):
    sampler = sampler or {}
    sx, sy = sampler.get("wrapS", REPEAT), sampler.get("wrapT", REPEAT)
    mode = sampler.get("magFilter", LINEAR)
    assert mode in (NEAREST, LINEAR)
    w, h = image.size
    # glTF(0,0) and PIL(0,0) are both top-left. Do NOT flip V here.
    def pixel(x, y):
        value = image.getpixel((_index(x, w, sx), _index(y, h, sy)))
        return (value[3] / 255) if len(value) == 4 else 1.0
    u, v = uv
    if mode == NEAREST:
        return pixel(math.floor(u * w), math.floor(v * h))
    x, y = u * w - .5, v * h - .5
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    return sum(pixel(ix + dx, iy + dy) * (fx if dx else 1-fx) * (fy if dy else 1-fy)
               for dx in (0, 1) for dy in (0, 1))


def material_alpha(material, texture_alpha=1.0, vertex_alpha=1.0):
    if material.get("alphaMode", "OPAQUE") == "OPAQUE":
        return 1.0
    factor = material.get("pbrMetallicRoughness", {}).get("baseColorFactor", [1, 1, 1, 1])[3]
    return texture_alpha * factor * vertex_alpha


def mask_visible(material, alpha):
    assert material.get("alphaMode") == "MASK"
    return alpha >= material.get("alphaCutoff", .5)
