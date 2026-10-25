"""Origin: S:/Repos/trick-or-treat/art/team/yard_street/batch02/yard_common.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Shared helpers for the yard_street lane, batch02 (v2: polished and textured).

Import from a build script in this folder:
    import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from yard_common import *

Everything here writes BOTH uv layers the kit expects: "UVMap" (material tiling in metres) and
"Tint" (palette cell + material layer). Builders set their own seam-safe UVs instead of relying on
the kit's per-face projection:
  * sweep()   tube along a path: u runs around (metres of circumference), v along the arc length.
              Per-ring radius and an optional shape(i, angle) multiplier (root flares, lobes).
  * lathe()   revolve a (r, z) profile, one colour/material per band, optional pane columns.
  * blob()    smooth lumpy sphere with puffy lobes (leaf clusters, hedge lumps, cloud puffs).
              Its poles sit on a chosen axis so the sphere projection pinches where nobody looks.
  * rod()     capped cylinder between two points with soft chamfered ends.
  * loft()    closed cross-sections along Y (car body).
  * cull_hidden(), flatten_below(), cut_below(), paint_world(), set_mat(), reproject()
  * finish()  clean + AO + export + review sheet + gates line.
"""
from __future__ import annotations

import math
import pathlib
import subprocess
import sys

# art-pipeline port: was `ROOT = pathlib.Path(__file__).resolve().parents[4]` (game root, only used for sys.path)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit
import lowpoly_kit as K  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Euler, Matrix, Quaternion, Vector, noise  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

__all__ = ["K", "math", "Vector", "Matrix", "Euler", "noise", "want", "bake", "parent_keep", "socket",
           "sweep", "lathe", "blob", "rod", "loft", "cull_hidden", "flatten_below", "cut_below",
           "paint_world", "set_mat", "reproject", "finish", "arc", "bezier", "catmull", "new_obj",
           "ground", "transform", "box", "deform", "nz", "uv_box"]


def want(asset_id):
    return not ARGS or asset_id in ARGS


def nz(x, y, z, seed=0.0):
    """Smooth Perlin noise in -1..1."""
    return noise.noise(Vector((x + seed * 17.13, y - seed * 9.71, z + seed * 3.37)))


# ---------------------------------------------------------------- object plumbing
def new_obj(bm, name, smooth=True):
    if smooth is not None:
        for f in bm.faces:
            f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K._link(bpy.data.objects.new(name, me))


def bake(ob):
    bpy.context.view_layer.update()
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.update()
    return ob


def transform(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """Sets the transform (degrees) and bakes it into the mesh."""
    ob.location = Vector(loc)
    ob.rotation_euler = Euler([math.radians(a) for a in rot])
    ob.scale = Vector(scale)
    return bake(ob)


def deform(ob, fn):
    return K.deform(ob, fn)


def parent_keep(child, parent):
    bpy.context.view_layer.update()
    return K.set_parent(child, parent)


def socket(anchor, loc, parent):
    ob = K.empty(f"socket_{anchor}")
    ob.location = Vector(loc)
    return parent_keep(ob, parent)


def ground(ob):
    """Shift the mesh so its lowest vertex sits at z = 0."""
    lo = min(v.co.z for v in ob.data.vertices)
    for v in ob.data.vertices:
        v.co.z -= lo
    ob.data.update()
    return ob


def box(name, size, color, mat="flat", loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0, segments=2, smooth=None):
    """Bevelled box (smooth-shaded when bevelled so the rounded edges read soft)."""
    if smooth is None:
        smooth = bevel > 0 and segments >= 2
    ob = K.box(name, size, color=color, mat=mat, bevel=bevel, segments=segments, smooth=smooth, project="box")
    ob.location = Vector(loc)
    ob.rotation_euler = Euler([math.radians(a) for a in rot])
    if smooth and bevel > 0:
        _flat_big_faces(ob)
    return ob


def _flat_big_faces(ob):
    """Bevelled boxes shade best with sharp-ish big faces: mark the flat panels flat so the normals
    only bend across the bevels (kills the 'pillow' gradient smooth shading puts on boxes)."""
    me = ob.data
    for p in me.polygons:
        p.use_smooth = True
    # Use custom split normals via edge sharpness on edges between near-coplanar large faces is
    # overkill here; instead mark edges sharp where the dihedral angle is small but faces are big.
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    def axis_face(f):
        return max(abs(f.normal.x), abs(f.normal.y), abs(f.normal.z)) > 0.999

    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces
            if axis_face(a) or axis_face(b):
                e.smooth = False
    bm.to_mesh(me)
    bm.free()


# ---------------------------------------------------------------- painting
def _faces_world(ob, where):
    bpy.context.view_layer.update()
    mw = ob.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    faces = [f for f in bm.faces if where is None or where(mw @ f.calc_center_median(), (nm @ f.normal).normalized())]
    return bm, faces


def paint_world(ob, color, where=None, mat=None):
    """Repaint faces chosen by world-space centre/normal; mat=None keeps each face's layer."""
    bm, faces = _faces_world(ob, where)
    _, tint = K._uv_layers(bm)
    u, v = K._uv_cell(color)
    for f in faces:
        layer = K._layer(mat) if mat is not None else (int(f.loops[0][tint].uv[0]) if f.loops else 0)
        for loop in f.loops:
            loop[tint].uv = (u + layer, v)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def set_mat(ob, mat, where=None):
    """Change the material layer of faces, keeping their palette tint."""
    bm, faces = _faces_world(ob, where)
    _, tint = K._uv_layers(bm)
    L = K._layer(mat)
    for f in faces:
        for loop in f.loops:
            uu, vv = loop[tint].uv
            loop[tint].uv = (L + (uu - math.floor(uu)), vv)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def reproject(ob, mode="box", where=None):
    return K.project(ob, mode, where)


def uv_box(bm, faces, scale=1.0):
    """Per-face dominant-axis planar UVs (metres) on a bmesh."""
    proj, _ = K._uv_layers(bm)
    for f in faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for loop in f.loops:
            p = loop.vert.co
            if ax == 2:
                loop[proj].uv = (p.x * scale, p.y * scale)
            elif ax == 0:
                loop[proj].uv = ((p.y if n.x > 0 else -p.y) * scale, p.z * scale)
            else:
                loop[proj].uv = ((-p.x if n.y > 0 else p.x) * scale, p.z * scale)


# ---------------------------------------------------------------- sweep (tubes, trunks, branches)
def _frames(pts, up_hint=None):
    n = len(pts)
    tans = []
    for i in range(n):
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tans.append(t.normalized())
    t0 = tans[0]
    ref = Vector(up_hint) if up_hint is not None else (Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0)))
    nrm = (ref - t0 * ref.dot(t0)).normalized()
    frames = [(t0, nrm)]
    for i in range(1, n):
        q = tans[i - 1].rotation_difference(tans[i])
        nrm = (q @ nrm)
        nrm = (nrm - tans[i] * nrm.dot(tans[i])).normalized()
        frames.append((tans[i], nrm))
    return frames


def sweep(name, points, radii, color="bark", mat="bark", sides=10, smooth=True, caps=(True, True),
          shape=None, cap_color=None, up_hint=None, phase=0.0, v_scale=1.0, colors=None):
    """Tube through points with per-point radii (number or list). shape(i, angle) -> radius factor.
    colors: optional fn(i_band, j_col) -> (color, mat) for per-face paint."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * n
    frames = _frames(pts, up_hint)
    bm = bmesh.new()
    proj, tint = K._uv_layers(bm)
    rings, rad_ring = [], []
    for i, (p, (t, nr)) in enumerate(zip(pts, frames)):
        b = t.cross(nr)
        ring, rr = [], []
        for j in range(sides):
            a = 2 * math.pi * j / sides + phase
            k = shape(i, a) if shape else 1.0
            r = radii[i] * k
            ring.append(bm.verts.new(p + (nr * math.cos(a) + b * math.sin(a)) * r))
            rr.append(r)
        rings.append(ring)
        rad_ring.append(sum(rr) / len(rr))
    s = [0.0]
    for i in range(1, n):
        s.append(s[-1] + (pts[i] - pts[i - 1]).length)
    side_faces = []
    for i in range(n - 1):
        for j in range(sides):
            j1 = (j + 1) % sides
            f = bm.faces.new((rings[i][j], rings[i][j1], rings[i + 1][j1], rings[i + 1][j]))
            uvs = [(j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1)]
            for loop, (jj, ii) in zip(f.loops, uvs):
                loop[proj].uv = (2 * math.pi * rad_ring[ii] * jj / sides, s[ii] * v_scale)
            side_faces.append((f, i, j))
    cap_faces = []
    for end, ok in ((0, caps[0]), (n - 1, caps[1])):
        if not ok:
            continue
        ring = rings[end] if end == n - 1 else list(reversed(rings[end]))
        f = bm.faces.new(ring)
        t, nr = frames[end]
        b = t.cross(nr)
        for loop in f.loops:
            d = loop.vert.co - pts[end]
            loop[proj].uv = (d.dot(nr), d.dot(b))
        cap_faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    K._paint_bm(bm, color, mat)
    if cap_color:
        K._paint_bm(bm, cap_color, mat, cap_faces)
    if colors:
        groups = {}
        for f, i, j in side_faces:
            cm = colors(i, j)
            if cm:
                groups.setdefault(cm, []).append(f)
        for (c, m), fs in groups.items():
            K._paint_bm(bm, c, m, fs)
    for f in bm.faces:
        f.smooth = smooth
    for f in cap_faces:
        f.smooth = False  # caps stay flat-shaded so tube ends look crisp
    return new_obj(bm, name, None)


def rod(name, a, b, radius, color, mat="metal", sides=8, chamfer=0.25, smooth=True, radius_b=None, caps=True):
    """Capped cylinder between a and b with soft chamfered ends (chamfer = fraction of radius)."""
    a, b = Vector(a), Vector(b)
    d = (b - a)
    L = d.length
    dn = d.normalized()
    rb = radius if radius_b is None else radius_b
    if chamfer > 0 and L > 4 * radius * chamfer:
        c = radius * chamfer
        pts = [a, a + dn * c, b - dn * c, b]
        rad = [radius * (1 - chamfer * 0.7), radius, rb, rb * (1 - chamfer * 0.7)]
    else:
        pts, rad = [a, b], [radius, rb]
    return sweep(name, pts, rad, color=color, mat=mat, sides=sides, smooth=smooth, caps=(caps, caps))


# ---------------------------------------------------------------- lathe
def lathe(name, profile, colors="wood", mats="flat", segments=12, smooth=True, cap_bottom=True, cap_top=True,
          cap_colors=None, cap_mats=None, phase=0.0, angles=None, band_cols=None, loc=(0, 0, 0), rot=(0, 0, 0),
          scale=(1, 1, 1), sharp_bands=()):
    """Revolve [(r, z), ...] bottom to top around Z. colors/mats: one value or one per band.
    band_cols: {band: [colour per column]} (panes). sharp_bands: band indices shaded flat."""
    if angles is not None:
        segments = len(angles)
    nb = len(profile) - 1
    if isinstance(colors, str):
        colors = [colors] * nb
    if isinstance(mats, str):
        mats = [mats] * nb
    band_cols = band_cols or {}
    if cap_colors is None:
        cap_colors = (colors[0], colors[-1])
    if cap_mats is None:
        cap_mats = (mats[0], mats[-1])
    bm = bmesh.new()
    proj, tint = K._uv_layers(bm)
    ang = [(math.radians(angles[j]) if angles is not None else 2 * math.pi * j / segments) + phase for j in range(segments)]
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)) for a in ang])
    s = [0.0]
    for i in range(1, len(profile)):
        s.append(s[-1] + math.hypot(profile[i][0] - profile[i - 1][0], profile[i][1] - profile[i - 1][1]))
    groups = {}
    flat_faces = []

    def u_of(i, jj):
        a = ang[jj % segments] + (2 * math.pi if jj >= segments else 0.0)
        return (a - phase) * max(profile[i][0], 0.0)

    for i in range(nb):
        r0, r1 = rings[i], rings[i + 1]
        for j in range(segments):
            j1 = (j + 1) % segments
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[j1], r1[j]))
                ids = [(i, j + 0.5), (i + 1, j + 1), (i + 1, j)]
            elif len(r1) == 1:
                f = bm.faces.new((r0[j], r0[j1], r1[0]))
                ids = [(i, j), (i, j + 1), (i + 1, j + 0.5)]
            else:
                f = bm.faces.new((r0[j], r0[j1], r1[j1], r1[j]))
                ids = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            for loop, (ii, jj) in zip(f.loops, ids):
                if jj != int(jj):
                    a = (ang[int(jj) % segments] + ang[(int(jj) + 1) % segments] + (2 * math.pi if int(jj) + 1 >= segments else 0)) / 2
                    uu = (a - phase) * profile[ii][0]
                else:
                    uu = u_of(ii, int(jj))
                loop[proj].uv = (uu, s[ii])
            col = band_cols[i][j] if i in band_cols else colors[i]
            groups.setdefault((col, mats[i]), []).append(f)
            if i in sharp_bands:
                flat_faces.append(f)
    caps = []
    for idx, ok, rev in ((0, cap_bottom, True), (len(rings) - 1, cap_top, False)):
        if ok and len(rings[idx]) > 1:
            f = bm.faces.new(list(reversed(rings[idx])) if rev else rings[idx])
            for loop in f.loops:
                loop[proj].uv = (loop.vert.co.x, loop.vert.co.y)
            k = 0 if rev else 1
            groups.setdefault((cap_colors[k], cap_mats[k]), []).append(f)
            caps.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for (c, m), fs in groups.items():
        K._paint_bm(bm, c, m, fs)
    for f in bm.faces:
        f.smooth = smooth
    for f in caps + flat_faces:
        f.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = K._link(bpy.data.objects.new(name, me))
    ob.location = Vector(loc)
    ob.rotation_euler = Euler([math.radians(a) for a in rot])
    ob.scale = Vector(scale)
    return ob


# ---------------------------------------------------------------- blobs
def blob(name, radius, color, mat="leaves", loc=(0, 0, 0), scale=(1, 1, 1), segments=12, rings=8, lobes=0,
         lobe_amp=0.18, lobe_pow=3.0, noise_amp=0.05, noise_freq=1.6, seed=0, axis="X", smooth=True,
         lobe_dirs=None, rot=(0, 0, 0), uvmode="sphere"):
    """Smooth lumpy sphere baked to world space. The UV-sphere poles sit on `axis` (default X, i.e.
    the left/right silhouette where the projection pinch is least visible). lobes > 0 adds puffy
    sub-bumps (leaf clusters, cloud billows). Records its inner ellipsoid for cull_hidden()."""
    import random
    rnd = random.Random(seed * 7919 + 13)
    if lobe_dirs is None and lobes:
        lobe_dirs = []
        for _ in range(lobes):
            z = rnd.uniform(-0.35, 1.0)
            a = rnd.uniform(0, 2 * math.pi)
            r = math.sqrt(max(0.0, 1 - z * z))
            lobe_dirs.append(Vector((math.cos(a) * r, math.sin(a) * r, z)))
    lobe_dirs = [Vector(d).normalized() for d in (lobe_dirs or [])]
    # local frame: pole axis
    if axis == "X":
        P, A, B = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    elif axis == "Y":
        P, A, B = Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))
    else:
        P, A, B = Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))
    bm = bmesh.new()
    proj, _ = K._uv_layers(bm)

    def disp(d):
        k = 1.0
        for ld in lobe_dirs:
            k += lobe_amp * max(0.0, d.dot(ld)) ** lobe_pow
        if noise_amp:
            k += noise_amp * nz(d.x * noise_freq, d.y * noise_freq, d.z * noise_freq, seed)
        return k

    verts = []
    south = None
    latv = []
    for i in range(rings + 1):
        lat = -math.pi / 2 + math.pi * i / rings
        latv.append(lat)
        if i == 0 or i == rings:
            d = P * math.sin(lat)
            verts.append([bm.verts.new(d * radius * disp(d))])
            continue
        row = []
        for j in range(segments):
            az = 2 * math.pi * j / segments
            d = P * math.sin(lat) + (A * math.cos(az) + B * math.sin(az)) * math.cos(lat)
            row.append(bm.verts.new(d * radius * disp(d)))
        verts.append(row)
    R = radius
    for i in range(rings):
        r0, r1 = verts[i], verts[i + 1]
        for j in range(segments):
            j1 = (j + 1) % segments
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[j1], r1[j]))
                ids = [(i, j + 0.5), (i + 1, j + 1), (i + 1, j)]
            elif len(r1) == 1:
                f = bm.faces.new((r0[j], r0[j1], r1[0]))
                ids = [(i, j), (i, j + 1), (i + 1, j + 0.5)]
            else:
                f = bm.faces.new((r0[j], r0[j1], r1[j1], r1[j]))
                ids = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            for loop, (ii, jj) in zip(f.loops, ids):
                loop[proj].uv = (2 * math.pi * jj / segments * R * math.cos(latv[ii]) ** 0.5, latv[ii] * R)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    K._paint_bm(bm, color, mat)
    ob = new_obj(bm, name, smooth)
    ob.location = Vector(loc)
    ob.rotation_euler = Euler([math.radians(a) for a in rot])
    ob.scale = Vector(scale)
    inner = radius * (1 - noise_amp) * 0.96
    ob["ell"] = [loc[0], loc[1], loc[2], inner * scale[0], inner * scale[1], inner * scale[2]]
    bake(ob)
    if uvmode == "box":  # world-space per-face planar UVs: no pole swirl (busy textures hide the seams)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.normal_update()
        uv_box(bm, bm.faces)
        bm.to_mesh(ob.data)
        bm.free()
    return ob


def cull_hidden(objs, margin=1.0, zmin=None):
    """Delete faces of each blob whose every vertex is inside another blob's inner ellipsoid."""
    ells = [(o, o.get("ell")) for o in objs]
    for ob in objs:
        others = [list(e) for o, e in ells if o is not ob and e is not None]
        if not others:
            continue
        bm = bmesh.new()
        bm.from_mesh(ob.data)

        def inside(co):
            if zmin is not None and co.z < zmin:
                return False
            for cx, cy, cz, rx, ry, rz in others:
                if ((co.x - cx) / rx) ** 2 + ((co.y - cy) / ry) ** 2 + ((co.z - cz) / rz) ** 2 < margin:
                    return True
            return False

        dead = [f for f in bm.faces if all(inside(v.co) for v in f.verts)]
        bmesh.ops.delete(bm, geom=dead, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    return objs


def flatten_below(ob, z0, k=0.25):
    """Squash every vertex below z0 toward the plane (soft flattened bottom, no cut)."""
    for v in ob.data.vertices:
        if v.co.z < z0:
            v.co.z = z0 - (z0 - v.co.z) * k
    ob.data.update()
    return ob


def cut_below(ob, z=0.0, cap_color=None, cap_mat="flat", keep="above"):
    bake(ob)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1 if keep == "above" else -1),
                           clear_inner=True)
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary:
        res = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
        if cap_color:
            K._paint_bm(bm, cap_color, cap_mat, res["faces"])
        uv_box(bm, res["faces"])
        for f in res["faces"]:
            f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for v in bm.verts:
        if abs(v.co.z - z) < 1e-5:
            v.co.z = z
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


# ---------------------------------------------------------------- loft (car body)
def loft(name, sections, color, mat="metal", smooth=True, caps=True, colors=None):
    """sections: list of (y, [(x, z), ...]) closed rings with the same point count, ordered along +Y.
    UV: u = perimeter length, v = y."""
    bm = bmesh.new()
    proj, _ = K._uv_layers(bm)
    rings = []
    per = []
    for y, ring in sections:
        rings.append([bm.verts.new((x, y, z)) for x, z in ring])
        acc = [0.0]
        for k in range(1, len(ring) + 1):
            a, b = ring[k - 1], ring[k % len(ring)]
            acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        per.append(acc)
    m = len(sections[0][1])
    side = []
    for i in range(len(rings) - 1):
        for j in range(m):
            j1 = (j + 1) % m
            f = bm.faces.new((rings[i][j], rings[i][j1], rings[i + 1][j1], rings[i + 1][j]))
            side.append((f, i, j))
            for loop, (ii, jj) in zip(f.loops, [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]):
                loop[proj].uv = (per[ii][jj], sections[ii][0])
    capf = []
    if caps:
        capf.append(bm.faces.new(list(reversed(rings[0]))))
        capf.append(bm.faces.new(rings[-1]))
        uv_box(bm, capf)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    K._paint_bm(bm, color, mat)
    if colors:
        groups = {}
        for f, i, j in side:
            cm = colors(i, j)
            if cm:
                groups.setdefault(cm, []).append(f)
        for (c, mm), fs in groups.items():
            K._paint_bm(bm, c, mm, fs)
    for f in bm.faces:
        f.smooth = smooth
    for f in capf:
        f.smooth = False
    return new_obj(bm, name, None)


# ---------------------------------------------------------------- curves
def arc(center, radius, a0, a1, n, plane="XZ", radius_end=None):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        r = radius if radius_end is None else radius + (radius_end - radius) * t
        if plane == "XZ":
            pts.append((center[0] + math.cos(a) * r, center[1], center[2] + math.sin(a) * r))
        elif plane == "YZ":
            pts.append((center[0], center[1] + math.cos(a) * r, center[2] + math.sin(a) * r))
        else:
            pts.append((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r, center[2]))
    return pts


def bezier(p0, p1, p2, n=6, p3=None):
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    out = []
    for i in range(n + 1):
        t = i / n
        if p3 is None:
            p = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2
        else:
            q3 = Vector(p3)
            p = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * q3
        out.append(tuple(p))
    return out


def catmull(points, per=3):
    """Catmull-Rom through points, `per` samples per segment (smooth trunks/branches)."""
    P = [Vector(p) for p in points]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                                    (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(tuple(P[-2]))
    return out


# ---------------------------------------------------------------- hand-off
def clean(ob, dist=1e-5):
    if ob.type != "MESH":
        return ob
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    dead = [f for f in bm.faces if f.calc_area() < 1e-8]
    if dead:
        bmesh.ops.delete(bm, geom=dead, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def finish(objects, rel_path, asset_id, ao_radius=0.8, ao_strength=0.9, ground_ao=True, sheet=True):
    for ob in objects:
        for o in [ob] + list(ob.children_recursive):
            clean(o)
    K.bake_ao(objects, samples=32, radius=ao_radius, strength=ao_strength, ground=ground_ao)
    out = K.export(objects, rel_path)
    tris = K.tri_count(objects)
    sh = K.review_sheet(objects, asset_id) if sheet else None
    print(f"ASSET {asset_id} tris={tris} gltf={out} sheet={sh}")
    return tris
