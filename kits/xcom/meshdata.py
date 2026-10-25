# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/meshdata.py (imported 2026-10-25)
# Changed: header only
"""Solids (craft coordinates) -> per-material triangle buffers in tile-local Blender coordinates.

Steps: clip every solid to the record's tile box (caps = 'section'), drop coincident opposite face pairs,
remove collinear/duplicate points, compute UVs in CRAFT coordinates (seamless across tiles), per-vertex
normals (flat or the solid's smooth normals), triangulate (convex fans), per-triangle tangents
(Blender UV space, v up; w = sign(dot(cross(N, T), dP/dv))), translate to the tile-local origin.
"""
import math

from avgeo import (H, EPS, Face, Solid, add, sub, mul, dot, cross, length, unit, poly_normal, plane_frame,
                   clip_box, bounds_tb)

# logical material key -> (glTF material, uv kind, scale or atlas cell)
WORLD = {"hull": ("AVENGER_v2_hull", (1.0, 1.0), (0.0, 0.0)),
         "hulldark": ("AVENGER_v2_hull_dark", (1.0, 1.0), (0.0, 0.0)),   # same maps, darker paint tint (sloped roof panels)
         "xpanel": ("AVENGER_v2_xpanel", (2.0, 2.0), (1.0, 1.0)),      # one X-braced plate per 2 m tile, aligned to tiles
         "greeble": ("AVENGER_v2_greeble", (2.0, 2.0), (1.0, 0.0)),
         "interior": ("AVENGER_v2_interior", (2.0, H), (1.0, 0.0)),
         "deck": ("AVENGER_v2_deck", (2.0, 2.0), (1.0, 1.0)),
         "nacelle": ("AVENGER_v2_nacelle", (1.5, 1.5), (0.0, 0.0)),
         "ramp": ("AVENGER_v2_ramp", (2.0, 2.0), (1.0, 1.0)),
         "lavpaint": ("AVENGER_v2_gear", (1.0, 1.0), (0.0, 0.0))}  # hull maps tinted lavender (P052/P053 gear)       # deck maps re-tinted rust brown (P061)
ATLAS = 2048.0
# swatch cells (x, y_from_top, w, h) in atlas pixels
SWATCH = {}
_names1 = ["section", "yellow", "orange", "purple", "lavender", "white", "red", "glass"]
_names2 = ["steel", "dark", "black", "bluelight", "hullgrey", "beige", "taupe", "rubber"]
for i, n in enumerate(_names1):
    SWATCH[n] = (i * 256, 1792, 256, 256)
for i, n in enumerate(_names2):
    SWATCH[n] = (i * 256, 1536, 256, 256)
_names3 = ["amber", "pinkpanel", "redglow", "purpledark", "lavlight", "greymid", "seat", "orangedark"]
for i, n in enumerate(_names3):
    SWATCH[n] = (i * 256, 1280, 256, 256)
# decal cells
DECAL = {"noseband": (0, 0, 2048, 512),
         "badge": (0, 512, 512, 512),
         "console_pink": (512, 512, 512, 512),
         "console_beige": (1024, 512, 512, 512),
         "mark_18": (1536, 512, 256, 256),
         "mark_red": (1792, 512, 256, 256),
         "glass": (1536, 768, 512, 512),
         "grille": (0, 1024, 512, 256),
         "intake": (512, 1024, 256, 256),
         "lights_blue": (768, 1024, 512, 256),
         "lights_amber": (1280, 1024, 512, 256),
         "vent": (1792, 1024, 256, 256)}
TRIM = "AVENGER_v2_trim"


def cell_uv(cell):
    x, y, w, h = cell
    return (x / ATLAS, 1 - (y + h) / ATLAS, (x + w) / ATLAS, 1 - y / ATLAS)


def rect_inset(r, f=0.15):
    u0, v0, u1, v1 = r
    du, dv = (u1 - u0) * f, (v1 - v0) * f
    return (u0 + du, v0 + dv, u1 - du, v1 - dv)


def clean_face(f):
    pts, nrm, uvs = list(f.pts), list(f.nrm) if f.nrm else None, list(f.uvs) if f.uvs else None
    changed = True
    while changed and len(pts) >= 3:
        changed = False
        k = len(pts)
        for i in range(k):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % k]
            if length(sub(b, a)) < 2e-6 or length(cross(sub(b, a), sub(c, b))) < 1e-9:
                del pts[i]
                if nrm: del nrm[i]
                if uvs: del uvs[i]
                changed = True
                break
    if len(pts) < 3 or length(poly_normal(pts)) < 1e-9:
        return None
    return Face(pts, f.mat, f.uv, nrm, uvs, f.tag)


def face_key(f):
    return frozenset((round(p[0], 4), round(p[1], 4), round(p[2], 4)) for p in f.pts)


def tile_box(tile):
    mx, my, mz = tile
    return (2 * mx - 1, 2 * mx + 1, -2 * my - 1, -2 * my + 1)


def collect(solids, tile, clip=True, extra_clip=None):
    x0, x1, y0, y1 = tile_box(tile)
    faces = []
    for s in solids:
        if clip:
            s = clip_box(s, x0, x1, y0, y1)
        if s is None:
            continue
        for f in s.faces:
            g = clean_face(f)
            if g is not None:
                faces.append(g)
    # remove coincident opposite pairs (internal faces between abutting convex pieces)
    groups = {}
    for i, f in enumerate(faces):
        groups.setdefault(face_key(f), []).append(i)
    drop = set()
    for idx in groups.values():
        if len(idx) >= 2:
            ns = [faces[i].normal() for i in idx]
            used = set()
            for a in range(len(idx)):
                for b in range(a + 1, len(idx)):
                    if a in used or b in used:
                        continue
                    if dot(ns[a], ns[b]) < -0.999:
                        used.update((a, b))
                        drop.update((idx[a], idx[b]))
    return [f for i, f in enumerate(faces) if i not in drop]


def face_uvs(f, n):
    if f.uv == "pre" and f.uvs and f.mat in WORLD:
        return [tuple(u) for u in f.uvs], None
    t, b = plane_frame(n)
    if isinstance(f.uv, tuple) and f.uv[0] in ("rect", "swatch"):
        if f.uv[0] == "rect":
            (u0, v0, u1, v1), (t0, t1, b0, b1) = f.uv[1], f.uv[2]
        else:
            u0, v0, u1, v1 = f.uv[1]
            t0, t1, b0, b1 = bounds_tb(f.pts, n)
        dt, db = max(t1 - t0, 1e-6), max(b1 - b0, 1e-6)
        return [(u0 + (dot(p, t) - t0) / dt * (u1 - u0), v0 + (dot(p, b) - b0) / db * (v1 - v0)) for p in f.pts], None
    return None, (t, b)


def build(solids, tile, clip=True):
    """Returns {gltf_material: dict(pos, nrm, uv, tan, idx)} in tile-local Blender coordinates, plus stats."""
    faces = collect(solids, tile, clip)
    mx, my, mz = tile
    origin = (2.0 * mx, -2.0 * my, mz * H)
    out = {}
    for f in faces:
        n = f.normal()
        key = f.mat
        if key in WORLD:
            mat, (su, sv), (ou, ov) = WORLD[key]
        else:
            mat = TRIM
        uvs, frame = face_uvs(f, n)
        if uvs is None:
            if key in WORLD:
                t, b = frame
                uvs = [((dot(p, t) + ou) / su, (dot(p, b) + ov) / sv) for p in f.pts]
            else:
                cell = SWATCH.get(key, SWATCH["hullgrey"])
                u0, v0, u1, v1 = rect_inset(cell_uv(cell), 0.2)
                t0, t1, b0, b1 = bounds_tb(f.pts, n)
                t, b = frame
                dt, db = max(t1 - t0, 1e-6), max(b1 - b0, 1e-6)
                uvs = [(u0 + (dot(p, t) - t0) / dt * (u1 - u0), v0 + (dot(p, b) - b0) / db * (v1 - v0)) for p in f.pts]
        nr = [unit(v) for v in f.nrm] if f.nrm else [n] * len(f.pts)
        buf = out.setdefault(mat, {"pos": [], "nrm": [], "uv": [], "tan": [], "idx": []})
        base = len(buf["pos"])
        # face-level tangent from the first well-conditioned triangle
        T = None
        tris = [(0, i, i + 1) for i in range(1, len(f.pts) - 1)]
        for (a, b_, c) in tris:
            p0, p1, p2 = f.pts[a], f.pts[b_], f.pts[c]
            w0, w1, w2 = uvs[a], uvs[b_], uvs[c]
            e1, e2 = sub(p1, p0), sub(p2, p0)
            du1, dv1, du2, dv2 = w1[0] - w0[0], w1[1] - w0[1], w2[0] - w0[0], w2[1] - w0[1]
            det = du1 * dv2 - du2 * dv1
            if abs(det) > 1e-12:
                r = 1.0 / det
                T = mul(sub(mul(e1, dv2), mul(e2, dv1)), r)
                Bv = mul(sub(mul(e2, du1), mul(e1, du2)), r)
                break
        if T is None:
            T, Bv = plane_frame(n)
        for p, nv, w in zip(f.pts, nr, uvs):
            t = sub(T, mul(nv, dot(nv, T)))
            if length(t) < 1e-8:
                t = plane_frame(nv)[0]
            t = unit(t)
            s = 1.0 if dot(cross(nv, t), Bv) >= 0 else -1.0
            buf["pos"].append(sub(p, origin))
            buf["nrm"].append(nv)
            buf["uv"].append((w[0], w[1]))
            buf["tan"].append((t[0], t[1], t[2], s))
        for (a, b_, c) in tris:
            buf["idx"].append((base + a, base + b_, base + c))
    # drop degenerate triangles (geometry or UV)
    for mat, buf in out.items():
        keep = []
        for (a, b_, c) in buf["idx"]:
            pa, pb, pc = buf["pos"][a], buf["pos"][b_], buf["pos"][c]
            ar = length(cross(sub(pb, pa), sub(pc, pa)))
            ua, ub, uc = buf["uv"][a], buf["uv"][b_], buf["uv"][c]
            det = (ub[0] - ua[0]) * (uc[1] - ua[1]) - (ub[1] - ua[1]) * (uc[0] - ua[0])
            if ar > 1e-9 and abs(det) > 1e-12:
                keep.append((a, b_, c))
        buf["idx"] = keep
    return out


def stats(bufs):
    tris = sum(len(b["idx"]) for b in bufs.values())
    pts = [p for b in bufs.values() for p in b["pos"]]
    lo = [min(p[i] for p in pts) for i in range(3)] if pts else [0, 0, 0]
    hi = [max(p[i] for p in pts) for i in range(3)] if pts else [0, 0, 0]
    return {"triangles": tris, "materials": sorted(bufs), "bounds_blender_local": [lo, hi]}
