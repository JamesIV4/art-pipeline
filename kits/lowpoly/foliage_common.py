"""Origin: S:/Repos/trick-or-treat/art/team/foliage/batch03/foliage_common.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Shared helpers for the foliage lane, batch03.

Builds on art/team/yard_street/batch02/yard_common.py (sweep, blob, catmull, cull_hidden, ...).

Foliage here is made of many small closed leaf shapes instead of smooth lumpy blobs:
  * maple_outline() / leaf_outline()   2D leaf silhouettes (pointed 5-lobe maple, simple leaf)
  * Acc                                 appends leaves/polys straight into one bmesh, records a
                                        per-vertex *shading normal* for every leaf vertex
  * Acc.leaf()                          one leaf = two opposite-facing faces (the toon shader culls
                                        back faces and has no alpha), slight cup along the midrib
  * finish_foliage()                    AO baked along the shading normals, then those normals are
                                        written as custom split normals (exported to glTF), so a
                                        crown of hundreds of cards shades like one soft volume while
                                        its silhouette breaks into leaves.
"""
from __future__ import annotations

import math
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit
import yard_common as Y  # noqa: E402
from yard_common import *  # noqa: E402,F401,F403

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

K = Y.K


# ---------------------------------------------------------------- leaf outlines
def maple_outline(rnd=None, jitter=0.0):
    """Pointed five-lobe maple leaf, star-shaped around its vein centre. CCW, centred, max dim 1.
    Returns (points, base) where base is the petiole point (local 2D)."""
    rnd = rnd or random.Random(0)
    # (angle deg, radius) around the vein centre; tips and notches alternate, base notch at -90
    spec = [(-90, 0.08), (-30, 0.42), (0, 0.29), (30, 0.56), (58, 0.31), (75, 0.49), (90, 0.64), (105, 0.49),
            (122, 0.31), (150, 0.56), (180, 0.29), (210, 0.42)]
    pts = []
    for a, r in spec:
        if jitter:
            a += rnd.uniform(-5, 5) * jitter
            r *= 1.0 + rnd.uniform(-0.1, 0.1) * jitter
        pts.append((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r))
    return _norm_outline(pts)


def maple_serrated(rnd=None, jitter=0.0):
    """Real maple silhouette: three main lobes (top, left, right) with a serration tooth on each
    flank, two small lower lobes, petiole notch at the base. 14 points, CCW, centred, max dim 1."""
    rnd = rnd or random.Random(0)
    spec = [(-90, 0.06), (-48, 0.28), (-18, 0.2), (20, 0.53), (39, 0.39), (55, 0.24), (73, 0.44), (90, 0.6),
            (107, 0.44), (125, 0.24), (141, 0.39), (160, 0.53), (198, 0.2), (228, 0.28)]
    pts = []
    for i, (a, r) in enumerate(spec):
        if jitter and i:
            a += rnd.uniform(-4, 4) * jitter
            r *= 1.0 + rnd.uniform(-0.08, 0.08) * jitter
        pts.append((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r))
    return _norm_outline(pts)


def maple_simple(rnd=None, jitter=0.0):
    """Cheaper maple (10 points): same three main lobes + two small lower lobes, no serration."""
    rnd = rnd or random.Random(0)
    spec = [(-90, 0.06), (-48, 0.28), (-18, 0.2), (20, 0.53), (55, 0.25), (90, 0.6), (125, 0.25), (160, 0.53),
            (198, 0.2), (228, 0.28)]
    pts = []
    for i, (a, r) in enumerate(spec):
        if jitter and i:
            a += rnd.uniform(-4, 4) * jitter
            r *= 1.0 + rnd.uniform(-0.08, 0.08) * jitter
        pts.append((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r))
    return _norm_outline(pts)


def maple_halves(rnd=None, jitter=0.0):
    """Maple outline split along the midrib: (right_half, left_half) CCW polygons in normalized 2D,
    each closing through the vein centre. The base is outline[0], the top tip outline[6]."""
    rnd = rnd or random.Random(0)
    spec = [(-90, 0.08), (-32, 0.46), (0, 0.29), (30, 0.57), (58, 0.31), (75, 0.49), (90, 0.64), (105, 0.49),
            (122, 0.31), (150, 0.57), (180, 0.29), (212, 0.46)]
    pts = []
    for i, (a, r) in enumerate(spec):
        if jitter and i not in (0, 6):
            a += rnd.uniform(-5, 5) * jitter
            r *= 1.0 + rnd.uniform(-0.1, 0.1) * jitter
        pts.append((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r))
    pts.append((0.0, 0.0))  # vein centre
    pts = _norm_outline_with(pts, pts[:-1])
    c = pts.pop()
    right = pts[0:7] + [c]
    left = pts[6:12] + [pts[0], c]
    return right, left


def _norm_outline_with(pts, ref):
    xs = [p[0] for p in ref]
    ys = [p[1] for p in ref]
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    s = max(max(xs) - min(xs), max(ys) - min(ys))
    return [((x - cx) / s, (y - cy) / s) for x, y in pts]


def leaf_outline(n=6, width=0.5):
    """Simple pointed oval leaf along +Y (bush leaves). n points total (even)."""
    pts = []
    half = n // 2
    for i in range(n):
        t = i / n * 2 * math.pi - math.pi / 2
        x = math.cos(t) * width * 0.5
        y = math.sin(t) * 0.5
        if abs(math.sin(t)) > 0.99:  # pointier tip/base
            y *= 1.12 if y > 0 else 1.0
        pts.append((x, y))
    return _norm_outline(pts)


def _norm_outline(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    s = max(max(xs) - min(xs), max(ys) - min(ys))
    out = [((x - cx) / s, (y - cy) / s) for x, y in pts]
    return out


def rand_unit(rnd):
    while True:
        v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if 0.05 < v.length <= 1.0:
            return v.normalized()


def fib_dirs(n, rnd=None, jitter=0.25):
    rnd = rnd or random.Random(0)
    out = []
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        a = g * i + rnd.uniform(-jitter, jitter)
        out.append(Vector((math.cos(a) * r, math.sin(a) * r, z)))
    return out


# ---------------------------------------------------------------- accumulator
class Acc:
    """Appends geometry to a bmesh (optionally seeded from an existing mesh object) and remembers a
    shading normal for every vertex it creates."""

    def __init__(self, ob=None):
        self.bm = bmesh.new()
        self.ob = ob
        if ob is not None:
            self.bm.from_mesh(ob.data)
        self.proj, self.tint = K._uv_layers(self.bm)
        self.shade = {}  # BMVert -> Vector
        self.ao = {}  # BMVert -> fixed AO value (skips ray casting)
        self.new_faces = []

    def _cell(self, color, mat):
        u, v = K._uv_cell(color)
        return (u + K._layer(mat), v)

    def poly(self, pts, color, mat="flat", shade=None, uv=None, smooth=True, ao=None):
        """One face through world points. shade: list of normals (per point) or one normal."""
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        f = self.bm.faces.new(vs)
        cell = self._cell(color, mat)
        for i, loop in enumerate(f.loops):
            loop[self.tint].uv = cell
            loop[self.proj].uv = uv[i] if uv else (0.0, 0.0)
        f.smooth = smooth
        if shade is not None:
            if isinstance(shade, list):  # one normal per point
                for v, s in zip(vs, shade):
                    self.shade[v] = Vector(s).normalized()
            else:
                s = Vector(shade).normalized()
                for v in vs:
                    self.shade[v] = s
        if ao is not None:
            for v in vs:
                self.ao[v] = ao
        self.new_faces.append(f)
        return f, vs

    def leaf(self, center, normal, tip_dir, size, color, mat="flat", shade=None, outline=None, cup=0.08,
             double=True, back_color=None, droop=0.0, stretch=1.0, ao=None):
        """A flat-ish leaf card (outline in its plane), cupped along the midrib, two-sided.
        normal: plane normal of the front face. tip_dir: roughly where the tip points.
        shade: shading normal for both faces (default: the plane normal)."""
        n = Vector(normal).normalized()
        t = Vector(tip_dir)
        t = (t - n * t.dot(n))
        if t.length < 1e-4:
            t = n.orthogonal()
        t.normalize()
        b = t.cross(n)  # right-hand: (b, t, n) so CCW outline faces +n
        c = Vector(center)
        outline = outline or maple_outline()
        pts = []
        for x, y in outline:
            y2 = y * stretch
            off = n * (cup * size * (2 * x) ** 2) - n * (droop * size * max(y2, 0.0) ** 2 * 2)
            pts.append(c + (b * x + t * y2) * size + off)
        uv = [(x * size, y * size * stretch) for x, y in outline]
        sh = Vector(shade).normalized() if shade is not None else n
        self.poly(pts, color, mat, shade=sh, uv=uv, ao=ao)
        if double:
            self.poly(list(reversed(pts)), back_color or color, mat, shade=sh, uv=list(reversed(uv)), ao=ao)

    def shade_existing(self, pred, normal=(0.0, 0.0, -1.0), ao=0.35):
        """Give pre-existing (base mesh) vertices matching pred(co) a fixed shading normal and AO.
        Filler cores use a downward normal so no light from above ever lights or glints on them:
        they read as pure inner shadow between the leaves."""
        n = Vector(normal).normalized()
        k = 0
        for v in self.bm.verts:
            if v not in self.shade and pred(v.co):
                self.shade[v] = n
                self.ao[v] = ao
                k += 1
        return k

    def triangulate_new(self):
        faces = [f for f in self.new_faces if f.is_valid and len(f.verts) > 3]
        for f in faces:
            f.normal_update()  # new faces have no normal yet; ear clipping projects along it
        if faces:
            bmesh.ops.triangulate(self.bm, faces=faces, quad_method="BEAUTY", ngon_method="EAR_CLIP")
        self.new_faces = []

    def to_object(self, name=None):
        """Writes into self.ob (or a new object). Returns (object, {vert_index: shade normal})."""
        self.triangulate_new()
        self.bm.verts.index_update()
        shade = {v.index: n for v, n in self.shade.items() if v.is_valid}
        self.fixed_ao = {v.index: a for v, a in self.ao.items() if v.is_valid}
        if self.ob is None:
            me = bpy.data.meshes.new(name or "foliage")
            self.ob = K._link(bpy.data.objects.new(name or "foliage", me))
        self.bm.to_mesh(self.ob.data)
        self.bm.free()
        self.ob.data.update()
        return self.ob, shade


# ---------------------------------------------------------------- AO + normals + export
def bake_ao_shade(ob, shade, samples=32, radius=0.8, strength=0.9, ground=True, offset=0.03,
                  extra=None, fixed=None):
    """Per-vertex AO like K.bake_ao, but rays leave each leaf vertex around its shading normal.
    extra(vertex_co, ao) -> ao lets a builder add a gradient (e.g. darker crown interior)."""
    me = ob.data
    verts = [v.co.copy() for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons(verts, polys)
    dirs = K._hemisphere(samples)
    attr = me.color_attributes.get("AO") or me.color_attributes.new("AO", "FLOAT_COLOR", "POINT")
    fixed = fixed or {}
    for v in me.vertices:
        if v.index in fixed:
            a = fixed[v.index]
            attr.data[v.index].color = (a, a, a, 1.0)
            continue
        p = v.co
        n = shade.get(v.index)
        is_leaf = n is not None
        if n is None:
            n = v.normal.copy()
        t = n.orthogonal().normalized()
        b = n.cross(t)
        occ = 0.0
        start = p + n * (offset if is_leaf else 0.006)
        for d in dirs:
            w = t * d.x + b * d.y + n * d.z
            if ground and w.z < -1e-4 and (-p.z / w.z) <= radius and p.z >= -0.01:
                occ += 1.0
                continue
            hit = bvh.ray_cast(start, w, radius)
            if hit[0] is not None:
                occ += 1.0 - (hit[3] / radius) * 0.5
        ao = 1.0 - strength * occ / len(dirs)
        if extra:
            ao = extra(p, ao, is_leaf)
        attr.data[v.index].color = (ao, ao, ao, 1.0)
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = me.color_attributes.active_color_index


def apply_shade_normals(ob, shade):
    me = ob.data
    nrm = [tuple(shade[i]) if i in shade else (0.0, 0.0, 0.0) for i in range(len(me.vertices))]
    me.normals_split_custom_set_from_vertices(nrm)
    me.update()


def finish_foliage(ob, shade, rel_path, asset_id, ao_radius=0.8, ao_strength=0.9, ground=True, extra=None,
                   sheet=True, fixed_ao=None):
    bake_ao_shade(ob, shade, radius=ao_radius, strength=ao_strength, ground=ground, extra=extra, fixed=fixed_ao)
    apply_shade_normals(ob, shade)
    out = K.export([ob], rel_path)
    tris = K.tri_count([ob])
    sh = K.review_sheet([ob], asset_id) if sheet else None
    print(f"ASSET {asset_id} tris={tris} gltf={out} sheet={sh}")
    return tris


def merged_base(parts, name):
    """Merge sweep/blob parts into one object and triangulate it (Y.clean) before leaves go on."""
    ob = K.merge(parts, name)
    Y.clean(ob)
    return ob
