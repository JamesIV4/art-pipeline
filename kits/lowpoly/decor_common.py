"""Origin: S:/Repos/trick-or-treat/art/team/decor_ground/batch03/decor_common.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Shared helpers for the decor_ground lane, batch03.

Reuses the yard_street/batch02 helpers (yard_common: blob, lathe, sweep, box ...) and the
pumpkins_farm/batch02 helpers (farm_lib: pumpkin_body, stem, straw_tuft, sweep ...).

    import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from decor_common import *

Adds:
  * flower_head()  low-poly daisy / mum head (centre fan + star petal ring), tucked into a surface.
  * leaf()         6-triangle pointed leaf with a raised midrib.
  * surface_points()  ray-cast points + normals on a mesh from a set of directions.
  * finish()       clean, weighted normals (optional), AO, export, review sheet, RESULT line.
"""
from __future__ import annotations

import math
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
# art-pipeline port: was `ROOT = HERE.parents[3]` (game root, only used for sys.path)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import yard_common as Y  # noqa: E402
import farm_lib as F  # noqa: E402

K = Y.K
TAU = 2 * math.pi
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

__all__ = ["Y", "F", "K", "math", "random", "Vector", "Matrix", "Euler", "bmesh", "bpy", "BVHTree", "TAU",
           "want", "frame", "flower_head", "leaf", "surface_points", "finish", "mesh_from", "sit_on_ground",
           "disc_on", "decal", "oval", "bvh", "cull_inside"]


def want(asset_id):
    return not ARGS or asset_id in ARGS


def frame(n):
    n = Vector(n).normalized()
    t = n.cross(Vector((0, 0, 1)))
    if t.length < 1e-3:
        t = n.cross(Vector((1, 0, 0)))
    t.normalize()
    b = n.cross(t).normalized()
    return n, t, b


def mesh_from(bm, name, smooth=True, sharp=None):
    return F.to_object(bm, name, smooth=smooth, sharp=sharp)


def flower_head(bm, center, normal, R, petals=12, colors=("mum_orange", "pumpkin_dark", "golden_leaf"),
                dome=0.38, tuck=0.22, spin=0.0, notch=0.68, mat="flat", cup=0.0, inner=0.42, ring_h=0.62):
    """Adds one flower head to bm. Centre fan (colors[2]), star ring of petals: petal wedges in
    colors[0], notch triangles in colors[1]. The star rim is tucked `tuck*R` below `center` along
    the normal, so the head sits in the foliage without needing a back face. 2*petals triangles."""
    n, t, b = frame(normal)
    c0 = Vector(center)
    k = petals // 2
    proj = F.uvl(bm)
    cv = bm.verts.new(c0 + n * R * dome)
    inn = []
    for i in range(k):
        a = TAU * (i + 0.5) / k + spin
        inn.append(bm.verts.new(c0 + (t * math.cos(a) + b * math.sin(a)) * R * inner + n * R * dome * ring_h))
    out = []
    for i in range(petals):
        a = TAU * i / petals + spin
        tip = i % 2 == 1
        r = R if tip else R * notch
        h = -tuck * R + (cup * R if tip else 0.0)
        out.append(bm.verts.new(c0 + (t * math.cos(a) + b * math.sin(a)) * r + n * h))
    fan, wedge, side = [], [], []
    for i in range(k):
        i2 = (i + 1) % k
        fan.append(bm.faces.new((cv, inn[i], inn[i2])))
        o0, o1, o2 = out[(2 * i + 1) % petals], out[(2 * i + 2) % petals], out[(2 * i + 3) % petals]
        side.append(bm.faces.new((inn[i], o0, o1)))
        wedge.append(bm.faces.new((inn[i], o1, inn[i2])))
        side.append(bm.faces.new((inn[i2], o1, o2)))
    # inn[i] lines up with the petal tip out[2i+1]: the two `side` triangles beside it form the petal,
    # the `wedge` triangle points at the notch between petals.
    allf = fan + wedge + side
    for f in allf:
        for loop in f.loops:
            d = loop.vert.co - c0
            loop[proj].uv = (d.dot(t) * 4, d.dot(b) * 4)
    F.paint(bm, fan, colors[2], mat)
    F.paint(bm, wedge, colors[1], mat)
    F.paint(bm, side, colors[0], mat)
    return allf


def leaf(bm, base, direction, length, width, up=(0, 0, 1), color="hedge", under="hedge_dark", droop=0.25,
         rib=0.25, mat="flat"):
    """Pointed leaf: base -> tip along direction, raised midrib. 6 triangles (4 top, 2 under)."""
    d = Vector(direction).normalized()
    u = Vector(up)
    s = d.cross(u)
    if s.length < 1e-4:
        s = d.cross(Vector((1, 0, 0)))
    s.normalize()
    u2 = s.cross(d).normalized()
    p0 = Vector(base)
    tip = p0 + d * length - u2 * droop * length
    mid = p0 + d * length * 0.45 - u2 * droop * length * 0.25
    L = bm.verts.new(mid - s * width / 2 - u2 * width * 0.08)
    R = bm.verts.new(mid + s * width / 2 - u2 * width * 0.08)
    M = bm.verts.new(mid + u2 * width * rib)
    B = bm.verts.new(p0)
    T = bm.verts.new(tip)
    top = [bm.faces.new((B, M, L)), bm.faces.new((L, M, T)), bm.faces.new((T, M, R)), bm.faces.new((R, M, B))]
    bot = [bm.faces.new((B, L, T)), bm.faces.new((B, T, R))]
    proj = F.uvl(bm)
    for f in top + bot:
        for loop in f.loops:
            q = loop.vert.co - p0
            loop[proj].uv = (q.dot(s) * 3, q.dot(d) * 3)
    F.paint(bm, top, color, mat)
    F.paint(bm, bot, under, mat)
    return top + bot


def disc_on(bm, center, normal, rx, ry, color, n=8, lift=0.004, dome=0.15, spin=0.0, mat="flat", up=None):
    """Flat-ish oval decal (eyes, mouths, cheeks) facing `normal`: n-gon fan, centre raised by dome*r."""
    nn = Vector(normal).normalized()
    if up is not None:
        upv = Vector(up)
        t = upv.cross(nn).normalized()  # horizontal
        b = nn.cross(t).normalized()     # up on the surface
    else:
        _, t, b = frame(nn)
    c0 = Vector(center) + nn * lift
    cv = bm.verts.new(c0 + nn * min(rx, ry) * dome)
    ring = []
    for i in range(n):
        a = TAU * i / n + spin
        ring.append(bm.verts.new(c0 + t * math.cos(a) * rx + b * math.sin(a) * ry - nn * lift * 0.8))
    fs = []
    for i in range(n):
        fs.append(bm.faces.new((cv, ring[i], ring[(i + 1) % n])))
    proj = F.uvl(bm)
    for f in fs:
        for loop in f.loops:
            q = loop.vert.co - c0
            loop[proj].uv = (q.dot(t) * 4, q.dot(b) * 4)
    F.paint(bm, fs, color, mat)
    # make sure they face outward
    for f in fs:
        f.normal_update()
        if f.normal.dot(nn) < 0:
            f.normal_flip()
    return fs


def decal(bm, tree, center, normal, outline, color, lift=0.003, up=(0, 0, 1), mat="flat", dome=0.0):
    """Polygon decal conforming to a surface (BVH `tree`): outline = [(x, y)] in metres on the
    surface plane (x right, y up as seen from the front, i.e. looking along -normal). Every vertex is
    ray-projected onto the surface and lifted by `lift`; the centre fan vertex is domed by `dome`."""
    nn = Vector(normal).normalized()
    upv = Vector(up)
    xr = upv.cross(nn).normalized()       # viewer's right when looking at the surface
    yu = nn.cross(xr).normalized()

    def project(p):
        h = tree.ray_cast(p + nn * 0.2, -nn, 0.5)
        if h[0] is None:
            return p
        return h[0] + h[1].normalized() * lift

    c0 = Vector(center)
    cx = sum(x for x, _ in outline) / len(outline)
    cy = sum(y for _, y in outline) / len(outline)
    cv = bm.verts.new(project(c0 + xr * cx + yu * cy) + nn * dome)
    ring = [bm.verts.new(project(c0 + xr * x + yu * y)) for x, y in outline]
    fs = []
    m = len(ring)
    for i in range(m):
        f = bm.faces.new((cv, ring[i], ring[(i + 1) % m]))
        f.normal_update()
        if f.normal.dot(nn) < 0:
            f.normal_flip()
        fs.append(f)
    proj = F.uvl(bm)
    for f in fs:
        for loop in f.loops:
            q = loop.vert.co - c0
            loop[proj].uv = (q.dot(xr) * 4, q.dot(yu) * 4)
    F.paint(bm, fs, color, mat)
    return fs


def oval(rx, ry, n=10, rot=0.0, cut=None):
    """Ellipse outline; cut='top' flattens the top half (open-mouth D shape)."""
    pts = []
    for i in range(n):
        a = TAU * i / n
        x, y = math.cos(a) * rx, math.sin(a) * ry
        if cut == "top" and y > 0:
            y *= 0.12
        c, s = math.cos(rot), math.sin(rot)
        pts.append((x * c - y * s, x * s + y * c))
    return pts


def cull_inside(parts, containers, margin=0.002):
    """Delete faces of each part whose vertices all lie inside one of the (closed) containers
    (nearest-surface normal test), plus faces lying flat on the ground plane. Saves triangles on
    overlapping blobs."""
    trees = [(c, bvh(c)) for c in containers]
    for ob in parts:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        mw = ob.matrix_world

        def inside(co):
            p = mw @ co
            for c, t in trees:
                if c is ob:
                    continue
                loc, nrm, _, _ = t.find_nearest(p)
                if loc is not None and (p - loc).dot(nrm) < -margin:
                    return True
            return False

        flags = {v: inside(v.co) for v in bm.verts}
        dead = [f for f in bm.faces if all(flags[v] for v in f.verts)
                or all(abs((mw @ v.co).z) < 1e-4 for v in f.verts)]
        bmesh.ops.delete(bm, geom=dead, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    return parts


def bvh(ob):
    bpy.context.view_layer.update()
    return BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())


def surface_points(ob, dirs, origin, far=3.0):
    """Cast rays from origin + d*far back toward origin; returns [(point, normal)] on ob's surface."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(ob, dg)
    mw = ob.matrix_world
    out = []
    o = Vector(origin)
    for d in dirs:
        d = Vector(d).normalized()
        start = o + d * far
        hit = tree.ray_cast(mw.inverted() @ start, (-d))
        if hit[0] is not None:
            out.append((mw @ hit[0], (mw.to_3x3() @ hit[1]).normalized()))
    return out


def sit_on_ground(ob, z=0.0):
    """Clamp everything below z onto the plane and delete faces lying on it."""
    for v in ob.data.vertices:
        if v.co.z < z:
            v.co.z = z
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    dead = [f for f in bm.faces if all(abs(v.co.z - z) < 1e-5 for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def finish(objects, rel_path, asset_id, ao_radius=0.6, ao_strength=0.9, weighted=False, ground_ao=True):
    for ob in objects:
        for o in [ob] + list(ob.children_recursive):
            if o.type == "MESH":
                Y.clean(o)
                F.cleanup(o)
    if weighted:
        for ob in objects:
            if ob.type == "MESH":
                F.weighted_normals(ob)
    tris = K.tri_count(objects)
    deg = F.degenerate_count(objects)
    K.bake_ao(objects, samples=32, radius=ao_radius, strength=ao_strength, ground=ground_ao)
    out = K.export(objects, rel_path)
    sheet = K.review_sheet(objects, asset_id)
    print(f"RESULT {asset_id} tris={tris} degenerate={deg} gltf={out} sheet={sheet}")
    return tris
