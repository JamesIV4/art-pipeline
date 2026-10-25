"""Origin: S:/Repos/trick-or-treat/art/team/characters_candy/batch03/dk_kit.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Lane helpers for characters_candy batch03 (copied from batch02). Kept out of art/tools on purpose.

mesh()      bmesh -> painted, projected, linked object (projection centre configurable)
lathe()     revolve an (r, z) profile around local Z (poles where r == 0); optional per-vertex warp
sweep()     tube through points with per-point radii, parallel-transport frames, optional profile
            warp fn(angle, i) -> radius multiplier (rope twist, flattened sections)
stitches()  little tent-shaped stitch dashes on a surface [(point, tangent, normal), ...]
bvh()/hit() ray casting against an object's world-space surface
put()       orient an object: local Z along a direction, local Y toward an up hint, plus roll
part()      merge pieces into one named object whose origin sits at a joint (identity rotation)
attach()    parent without a parent-inverse matrix (clean glTF local translations)
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit
import lowpoly_kit as K  # noqa: E402

V = Vector


# ---------------------------------------------------------------- mesh building
def mesh(bm, name, color, mat="flat", project="sphere", smooth=True, center=None, loc=(0, 0, 0), extra=()):
    """extra: [(faces, color, mat)] painted over the base colour."""
    bm.normal_update()
    if center is None:
        lo = V((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), min(v.co.z for v in bm.verts)))
        hi = V((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), max(v.co.z for v in bm.verts)))
        center = (lo + hi) / 2
    K._project_bm(bm, project, center=V(center))
    K._paint_bm(bm, color, mat)
    for faces, c2, m2 in extra:
        K._paint_bm(bm, c2, m2, faces)
    for f in bm.faces:
        f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = K._link(bpy.data.objects.new(name, me))
    ob.location = V(loc)
    return ob


def lathe(name, prof, segs=16, color="dragon_teal", mat="felt", project="sphere", loc=(0, 0, 0),
          warp=None, smooth=True, phase=0.0, center=None):
    """prof: [(r, z), ...] bottom to top. r == 0 makes a pole. warp(Vector) -> Vector in local space."""
    bm = bmesh.new()
    rings = []
    for r, z in prof:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((math.cos(2 * math.pi * j / segs + phase) * r,
                                        math.sin(2 * math.pi * j / segs + phase) * r, z)) for j in range(segs)])
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(segs):
            j2 = (j + 1) % segs
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                bm.faces.new((A[0], B[j2], B[j]))
            elif len(B) == 1:
                bm.faces.new((A[j], A[j2], B[0]))
            else:
                bm.faces.new((A[j], A[j2], B[j2], B[j]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    if warp:
        for v in bm.verts:
            v.co = warp(v.co.copy())
    return mesh(bm, name, color, mat, project, smooth, center=center, loc=loc)


def _frames(pts, closed=False):
    n = len(pts)
    tans = []
    for i in range(n):
        if closed:
            t = pts[(i + 1) % n] - pts[(i - 1) % n]
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tans.append(t.normalized())
    up = V((0, 0, 1)) if abs(tans[0].z) < 0.9 else V((1, 0, 0))
    nrm = (up - tans[0] * up.dot(tans[0])).normalized()
    frames = []
    for i, t in enumerate(tans):
        if i:
            nrm = (nrm - t * nrm.dot(t)).normalized()
        frames.append((t, nrm, t.cross(nrm)))
    return frames


def sweep(name, pts, radii, sides=8, color="dragon_teal", mat="felt", project="sphere", smooth=True,
          closed=False, warp=None, center=None, up=None, paint=None):
    """warp(angle, i) -> radius multiplier. Ends with radius 0 become poles, others get flat caps.
    paint(i, j) -> (color, mat) or None recolours the face between rings i, i+1 and sides j, j+1
    (side 0 starts at the frame normal, which 'up' can aim)."""
    pts = [V(p) for p in pts]
    if isinstance(radii, (int, float)):
        radii = [radii] * len(pts)
    frames = _frames(pts, closed)
    if up is not None:   # rotate every frame so the first normal faces 'up'
        t0, n0, b0 = frames[0]
        u = V(up)
        u = (u - t0 * u.dot(t0)).normalized()
        ang = math.atan2(u.dot(b0), u.dot(n0))
        frames = [(t, n * math.cos(ang) + b * math.sin(ang), -n * math.sin(ang) + b * math.cos(ang)) for t, n, b in frames]
    bm = bmesh.new()
    rings = []
    for i, (p, r, (t, n, b)) in enumerate(zip(pts, radii, frames)):
        if r < 1e-6:
            rings.append([bm.verts.new(p)])
            continue
        ring = []
        for j in range(sides):
            a = 2 * math.pi * j / sides
            k = warp(a, i) if warp else 1.0
            ring.append(bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * r * k))
        rings.append(ring)
    count = len(rings) if closed else len(rings) - 1
    groups = {}
    for i in range(count):
        A, B = rings[i], rings[(i + 1) % len(rings)]
        for j in range(sides):
            j2 = (j + 1) % sides
            if len(A) == 1:
                f = bm.faces.new((A[0], B[j2], B[j]))
            elif len(B) == 1:
                f = bm.faces.new((A[j], A[j2], B[0]))
            else:
                f = bm.faces.new((A[j], A[j2], B[j2], B[j]))
            cm = paint(i, j) if paint else None
            if cm:
                groups.setdefault(cm, []).append(f)
    if not closed:
        if len(rings[0]) > 1:
            bm.faces.new(list(reversed(rings[0])))
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1])
    extra = [(fs, c, m) for (c, m), fs in groups.items()]
    return mesh(bm, name, color, mat, project, smooth, center=center, extra=extra)


def stitches(name, items, length=0.018, width=0.006, height=0.0035, color="dragon_teal_dark", sink=0.003):
    """Tent-shaped stitch dashes (6 tris each). items: [(point, tangent, normal)]."""
    bm = bmesh.new()
    for p, t, n in items:
        p, t, n = V(p), V(t), V(n).normalized()
        t = (t - n * t.dot(n)).normalized()
        b = n.cross(t)
        L, W = length / 2, width / 2
        base = [bm.verts.new(p - n * sink + t * sx * L + b * sy * W) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        ridge = [bm.verts.new(p + n * height + t * sx * (L - W * 0.6)) for sx in (-1, 1)]
        faces = [(base[0], base[1], ridge[1], ridge[0]), (base[2], base[3], ridge[0], ridge[1]),
                 (base[1], base[2], ridge[1]), (base[3], base[0], ridge[0])]
        for fv in faces:
            f = bm.faces.new(fv)
            f.normal_update()
            if f.normal.dot(f.calc_center_median() - (p - n * sink)) < 0:
                f.normal_flip()
    return mesh(bm, name, color, "flat", "box", smooth=False)


# ---------------------------------------------------------------- surfaces
def bvh(ob):
    bpy.context.view_layer.update()
    mw = ob.matrix_world
    verts = [mw @ v.co for v in ob.data.vertices]
    polys = [list(p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def hit(tree, origin, direction, dist=10.0):
    loc, nrm, _, _ = tree.ray_cast(V(origin), V(direction).normalized(), dist)
    return loc, nrm


def ring_on(tree, center, axis_u, axis_v, ru, rv, count, ray_dir, back=1.0, offset=0.0, start=0.0, arc=2 * math.pi):
    """Points on a surface: an ellipse (ru, rv) around center in the (axis_u, axis_v) plane, cast along
    ray_dir from 'back' metres behind. Returns [(point, tangent, normal)]."""
    c, u, v, d = V(center), V(axis_u), V(axis_v), V(ray_dir).normalized()
    out = []
    closed = arc >= 2 * math.pi - 1e-6
    for i in range(count):
        a = start + arc * (i / count if closed else i / max(count - 1, 1))
        q = c + u * math.cos(a) * ru + v * math.sin(a) * rv
        loc, nrm = hit(tree, q - d * back, d, back * 3)
        if loc is None:
            continue
        tan = -u * math.sin(a) * ru + v * math.cos(a) * rv
        out.append((loc + nrm * offset, tan, nrm))
    return out


# ---------------------------------------------------------------- orientation and rig
def look(z_dir, up=(0, 0, 1), roll=0.0):
    z = V(z_dir).normalized()
    u = V(up)
    x = u.cross(z)
    if x.length < 1e-6:
        x = V((1, 0, 0)).cross(z)
    x.normalize()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed()
    if roll:
        m = m @ Matrix.Rotation(math.radians(roll), 3, "Z")
    return m


def put(ob, loc, z_dir, up=(0, 0, 1), roll=0.0, scale=(1, 1, 1)):
    m = look(z_dir, up, roll).to_4x4()
    ob.matrix_world = Matrix.Translation(V(loc)) @ m @ Matrix.Diagonal(V(scale)).to_4x4()
    return ob


def part(objs, name, joint):
    if "--pieces" in sys.argv:
        print("  ", name, ", ".join(f"{o.name}:{tris(o)}" for o in objs))
    ob = K.merge(objs, name)
    j = V(joint)
    ob.data.transform(Matrix.Translation(-j))
    ob.location = j
    return ob


def attach(child, parent):
    bpy.context.view_layer.update()
    world = child.matrix_world.translation.copy()
    pw = parent.matrix_world.translation.copy()
    child.parent = parent
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.location = world - pw
    bpy.context.view_layer.update()
    return child


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)
