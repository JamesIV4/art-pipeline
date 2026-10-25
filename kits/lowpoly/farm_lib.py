"""Origin: S:/Repos/trick-or-treat/art/team/pumpkins_farm/batch02/farm_lib.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Shared helpers for the pumpkins_farm lane, batch02 (v2 textured kit).

Import from a build script in this folder:
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import farm_lib as F
    K = F.K

Upgraded from batch01/pumpkin_lib.py:
  * every helper writes both UV maps of kit v2: "UVMap" (material tiling in metres) and "Tint"
    (palette cell + material layer), so everything carries a painted material.
  * pumpkin_body: plump smooth lobes (sqrt-sine lobe profile, 4-6 columns per lobe), crisp sharp
    grooves (sharp edges, no painted strips), a real stem cavity, and UVs aligned so each geometric
    lobe gets exactly one rib of the 'pumpkin' material (the texture has 4 ribs per tile).
  * stem: ridged, curled, bark-textured stem with a flared base and a pale cut end.
  * pumpkin_leaf: palmate corrugated leaf (one- or two-sided).
  * carve: tapered pocket with a pumpkin_dark rim band, glowing inner wall band and glowing floor.
  * sweep / blade / lathe / slab / bale helpers with proper material UVs.
  * finish: weighted normals (crisp bevels, soft rounds), AO, export, review sheet, report.
"""
from __future__ import annotations

import math
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import lowpoly_kit as K  # noqa: E402

TAU = 2 * math.pi


# ----------------------------------------------------------------------------- bmesh basics
def bm_new():
    bm = bmesh.new()
    K._uv_layers(bm)  # UVMap first (TEXCOORD_0), then Tint (TEXCOORD_1)
    return bm


def uvl(bm):
    return K._uv_layers(bm)[0]


def paint(bm, faces, color, mat="flat"):
    K._paint_bm(bm, color, mat, list(faces))


def set_uv(bm, face, uvs):
    proj = uvl(bm)
    for loop, uv in zip(face.loops, uvs):
        loop[proj].uv = uv


def to_object(bm, name, smooth=True, sharp=None):
    """Link a bmesh as an object. sharp=<degrees> marks edges with a larger dihedral angle sharp."""
    bm.normal_update()
    for f in bm.faces:
        f.smooth = smooth
    if sharp is not None and smooth:
        lim = math.radians(sharp)
        for e in bm.edges:
            if len(e.link_faces) == 2:
                try:
                    if e.calc_face_angle() > lim:
                        e.smooth = False
                except ValueError:
                    pass
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K._link(bpy.data.objects.new(name, me))


def auto_smooth(ob, angle=35.0, smooth=True):
    """Smooth-shade an object and mark edges above angle sharp (soft rounds, crisp creases)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    lim = math.radians(angle)
    for f in bm.faces:
        f.smooth = smooth
    for e in bm.edges:
        e.smooth = True
        if len(e.link_faces) == 2:
            try:
                if e.calc_face_angle() > lim:
                    e.smooth = False
            except ValueError:
                pass
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def bake(ob):
    """Apply an object's own transform to its mesh."""
    bpy.context.view_layer.update()
    ob.data.transform(ob.matrix_basis)
    ob.matrix_basis.identity()
    ob.data.update()
    return ob


def transform(ob, mat):
    ob.data.transform(mat)
    ob.data.update()
    return ob


def drop_to_ground(ob):
    lo = min(v.co.z for v in ob.data.vertices)
    for v in ob.data.vertices:
        v.co.z -= lo
    ob.data.update()
    return ob


def scale_uv(ob, s, where=None):
    """Scale material UVs (denser texture on tiny parts)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    proj = uvl(bm)
    for f in bm.faces:
        if where is None or where(f.calc_center_median(), f.normal):
            for loop in f.loops:
                loop[proj].uv = loop[proj].uv * s
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def project_along(ob, along="x", where=None):
    """Box projection whose texture v axis follows a world axis where the face allows it, so
    straw strands / wood grain run along the length of a bale or board."""
    ai = "xyz".index(along)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    proj = uvl(bm)
    for f in bm.faces:
        if where is not None and not where(f.calc_center_median(), f.normal):
            continue
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        if ax == ai:
            others = [i for i in range(3) if i != ax]
            for loop in f.loops:
                p = loop.vert.co
                loop[proj].uv = (p[others[0]], p[others[1]])
            continue
        other = [i for i in range(3) if i not in (ax, ai)][0]
        for loop in f.loops:
            p = loop.vert.co
            loop[proj].uv = (p[other], p[ai])
    bm.to_mesh(ob.data)
    bm.free()
    return ob


# ----------------------------------------------------------------------------- sweep (tubes)
def _frames(pts):
    n = len(pts)
    tans = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    if n > 3 and (pts[0] - pts[-1]).length < 1e-6:  # closed loop: cyclic tangents, no kink at the seam
        tans[0] = tans[-1] = (pts[1] - pts[-2]).normalized()
    frames = []
    t0 = tans[0]
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    side = t0.cross(ref).normalized()
    for t in tans:
        side = side - t * side.dot(t)
        if side.length < 1e-6:
            side = t.cross(Vector((0, 1, 0)))
        side.normalize()
        up = t.cross(side).normalized()
        frames.append((t, side, up))
    return frames


def sweep(name, points, radii, sides=8, color="vine", mat="flat", profile=None, cap_start=True,
          cap_end=True, cap_offset=0.0, uv_scale=1.0, smooth=True, sharp=None, end_color=None,
          end_mat=None, twist=0.0, phase=0.0, flatten=1.0, rib=None, side_colors=None, side_from=0):
    """Tube along points. radii: number, list per point, or callable(t). profile(j)-> radial
    multiplier per side (star sections for ridged stems). flatten scales the 'up' axis (flat
    straps). UVs: u around and v along, in metres times uv_scale. Caps are fans whose centre is
    pushed out by cap_offset * radius (rounded ends)."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    if callable(radii):
        rr = [radii(i / max(n - 1, 1)) for i in range(n)]
    elif isinstance(radii, (int, float)):
        rr = [float(radii)] * n
    else:
        rr = list(radii)
    frames = _frames(pts)
    bm = bm_new()
    proj = uvl(bm)
    rings = []
    for i, (p, (t, side, up)) in enumerate(zip(pts, frames)):
        ring = []
        for j in range(sides):
            a = TAU * j / sides + phase + twist * i
            m = profile(j) if profile else 1.0
            ring.append(bm.verts.new(p + (side * math.cos(a) + up * math.sin(a) * flatten) * rr[i] * m))
        rings.append(ring)
    arc = [0.0]
    for i in range(1, n):
        arc.append(arc[-1] + (pts[i] - pts[i - 1]).length)
    body = []
    circ_mean = TAU * sum(rr) / n
    for i in range(n - 1):
        circ = TAU * 0.5 * (rr[i] + rr[i + 1])
        for j in range(sides):
            j2 = (j + 1) % sides
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            if rib is not None:
                # one texture rib per side (pumpkin material: 4 ribs per tile, grooves at 0.125 + k/4)
                vs = rib * sides / circ_mean
                u0, u1 = 0.125 + rib * j, 0.125 + rib * (j + 1)
                quad = ((u0, arc[i] * vs), (u1, arc[i] * vs), (u1, arc[i + 1] * vs), (u0, arc[i + 1] * vs))
                for loop, uv in zip(f.loops, quad):
                    loop[proj].uv = uv
            else:
                u0, u1 = circ * j / sides, circ * (j + 1) / sides
                for loop, uv in zip(f.loops, ((u0, arc[i]), (u1, arc[i]), (u1, arc[i + 1]), (u0, arc[i + 1]))):
                    loop[proj].uv = (uv[0] * uv_scale, uv[1] * uv_scale)
            body.append(f)
    caps = []
    for which, idx, sgn, on in (("s", 0, -1, cap_start), ("e", n - 1, 1, cap_end)):
        if not on:
            continue
        t = frames[idx][0]
        c = bm.verts.new(pts[idx] + t * sgn * rr[idx] * cap_offset)
        ring = rings[idx]
        for j in range(sides):
            j2 = (j + 1) % sides
            vs = (c, ring[j2], ring[j]) if sgn < 0 else (c, ring[j], ring[j2])
            f = bm.faces.new(vs)
            for loop in f.loops:
                d = loop.vert.co - pts[idx]
                loop[proj].uv = (d.dot(frames[idx][1]) * uv_scale, d.dot(frames[idx][2]) * uv_scale)
            caps.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    paint(bm, bm.faces, color, mat)
    if side_colors:
        for idx, f in enumerate(body):
            i, j = divmod(idx, sides)
            c = side_colors[j % len(side_colors)]
            if c and i >= side_from:
                paint(bm, [f], c, mat)
    if end_color and caps:
        paint(bm, caps, end_color, end_mat or mat)
    return to_object(bm, name, smooth=smooth, sharp=sharp)


def spiral_points(center, turns, r0, r1, rise, n, phase=0.0, axis="z"):
    out = []
    for i in range(n):
        t = i / (n - 1)
        a = phase + TAU * turns * t
        r = r0 + (r1 - r0) * t
        if axis == "z":
            out.append((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r, center[2] + rise * t))
        else:  # vertical curl in the x/z plane, drifting along y
            out.append((center[0] + math.cos(a) * r, center[1] + rise * t, center[2] + math.sin(a) * r))
    return out


def tendril(name, start, turns=1.6, r0=0.05, r1=0.015, rise=0.04, n=14, radius=0.009, color="vine",
            sides=5, phase=0.0, axis="z", lead=None):
    """Curly pig-tail tendril. lead: optional point it springs from."""
    pts = spiral_points((0, 0, 0), turns, r0, r1, rise, n, phase, axis)
    ox = start[0] - pts[0][0]
    oy = start[1] - pts[0][1]
    oz = start[2] - pts[0][2]
    pts = [(x + ox, y + oy, z + oz) for x, y, z in pts]
    if lead is not None:
        pts = [lead] + pts
    return sweep(name, pts, lambda t: radius * (1.0 - 0.45 * t), sides=sides, color=color, mat="flat",
                 cap_offset=0.6)


# ----------------------------------------------------------------------------- blade (leaf / straw ribbon)
def blade(name, points, widths, thick=0.01, color="straw", mat="flat", up=(0, 0, 1), under_color=None,
          smooth=True, crease=1.0, uv_scale=1.0):
    """Closed leaf/ribbon through points with a diamond section (left edge, top midrib, right edge,
    bottom midrib), so it reads from both sides. width 0 at the end makes a pointed tip."""
    bm = bm_new()
    proj = uvl(bm)
    pts = [Vector(p) for p in points]
    n = len(pts)
    ups = up if isinstance(up[0], (list, tuple, Vector)) else [up] * n
    rings = []
    tip = None
    arc = [0.0]
    for i in range(1, n):
        arc.append(arc[-1] + (pts[i] - pts[i - 1]).length)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        u = Vector(ups[i]).normalized()
        side = t.cross(u)
        if side.length < 1e-6:
            side = t.cross(Vector((1, 0, 0)))
        side.normalize()
        u2 = side.cross(t).normalized()
        w = widths[i]
        if w <= 1e-6 and i == n - 1:
            tip = bm.verts.new(p)
            break
        th = thick * (crease if 0 < i < n - 1 else 1.0)
        rings.append([bm.verts.new(p - side * w / 2), bm.verts.new(p + u2 * th),
                      bm.verts.new(p + side * w / 2), bm.verts.new(p - u2 * th)])
    across = [-0.5, 0.0, 0.5, 0.0]
    top_faces = []

    def uvs_for(f, i_of):
        for loop in f.loops:
            i, j = i_of[loop.vert]
            w = widths[i] if i < len(widths) else 0.0
            loop[proj].uv = (across[j] * w * uv_scale if j is not None else 0.0, arc[i] * uv_scale)

    i_of = {}
    for i, ring in enumerate(rings):
        for j, v in enumerate(ring):
            i_of[v] = (i, j)
    if tip is not None:
        i_of[tip] = (n - 1, None)
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(4):
            f = bm.faces.new((a[j], b[j], b[(j + 1) % 4], a[(j + 1) % 4]))
            uvs_for(f, i_of)
            if j in (0, 1):
                top_faces.append(f)
    f = bm.faces.new(list(reversed(rings[0])))
    uvs_for(f, i_of)
    if tip is not None:
        last = rings[-1]
        for j in range(4):
            f = bm.faces.new((last[j], tip, last[(j + 1) % 4]))
            uvs_for(f, i_of)
            if j in (0, 1):
                top_faces.append(f)
    else:
        f = bm.faces.new(rings[-1])
        uvs_for(f, i_of)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    paint(bm, bm.faces, color, mat)
    if under_color:
        paint(bm, [f for f in bm.faces if f not in top_faces], under_color, mat)
    return to_object(bm, name, smooth=smooth, sharp=60 if smooth else None)


def straw_tuft(prefix, base, direction, count=4, length=0.1, radius=0.012, spread=0.5, seed=0,
               colors=("straw", "hay", "straw_dark"), droop=0.3):
    """A little fan of tapered straw strands poking out of a surface (3-sided, slightly bent)."""
    rnd = random.Random(seed)
    d = Vector(direction).normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 1e-3:
        side = d.cross(Vector((1, 0, 0)))
    side.normalize()
    up = side.cross(d).normalized()
    out = []
    for i in range(count):
        a = (i - (count - 1) / 2) * spread / max(count - 1, 1) * 2 + rnd.uniform(-0.15, 0.15)
        b = rnd.uniform(-0.35, 0.35)
        dd = (d + side * math.tan(a) * 0.7 + up * b).normalized()
        ln = length * rnd.uniform(0.75, 1.25)
        p0 = Vector(base) - dd * 0.025
        p1 = Vector(base) + dd * ln * 0.55
        p2 = Vector(base) + dd * ln + Vector((0, 0, -droop * ln * 0.4))
        out.append(sweep(f"{prefix}{i}", [p0, p1, p2], [radius, radius * 0.8, radius * 0.25], sides=3,
                         color=colors[i % len(colors)], mat="flat", cap_start=False, cap_end=False,
                         smooth=False, phase=rnd.uniform(0, 2)))
    return out


# ----------------------------------------------------------------------------- lathe / slab / rounded box
def lathe(name, profile, segs=12, color="wood", mat="wood", band_colors=None, column_colors=None,
          cap_top=True, cap_bottom=True, smooth=True, sharp=None, top_color=None, bottom_color=None,
          top_mat=None, bottom_mat=None, phase=0.0, uv="cyl", stave=0.32, band_mats=None, flat_cols=False):
    """Surface of revolution from profile [(r, z), ...] bottom to top.
    uv='cyl': u = arc around (m), v = profile arc length (m). uv='staves': u = column * stave so each
    column is exactly one plank of the 'planks' texture (barrels, tubs)."""
    bm = bm_new()
    proj = uvl(bm)
    rings = []
    for r, z in profile:
        if r < 1e-6:  # pole: one shared vertex (faces collapse to triangles below)
            pole = bm.verts.new((0, 0, z))
            rings.append([pole] * segs)
            continue
        rings.append([bm.verts.new((math.cos(TAU * j / segs + phase) * r, math.sin(TAU * j / segs + phase) * r, z))
                      for j in range(segs)])
    arc = [0.0]
    for i in range(1, len(profile)):
        arc.append(arc[-1] + math.hypot(profile[i][0] - profile[i - 1][0], profile[i][1] - profile[i - 1][1]))
    side_faces = []
    for i in range(len(rings) - 1):
        rm = 0.5 * (profile[i][0] + profile[i + 1][0])
        for j in range(segs):
            j2 = (j + 1) % segs
            quad_v = (rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j])
            uniq = []
            for v in quad_v:
                if v not in uniq:
                    uniq.append(v)
            f = bm.faces.new(uniq)
            if len(uniq) == 3:
                proj_uv = [(v.co.x, v.co.y) for v in uniq]
                set_uv(bm, f, proj_uv)
                c = column_colors[j % len(column_colors)] if column_colors else color
                if band_colors and band_colors[i]:
                    c = band_colors[i]
                paint(bm, [f], c, band_mats[i] if band_mats and band_mats[i] else mat)
                side_faces.append(f)
                continue
            if uv == "staves":
                u0, u1 = j * stave, (j + 1) * stave
            else:
                u0, u1 = TAU * rm * j / segs, TAU * rm * (j + 1) / segs
            quad = ((u0, arc[i]), (u1, arc[i]), (u1, arc[i + 1]), (u0, arc[i + 1]))
            if uv == "around":  # texture v runs around (wrapped straw on round bales)
                quad = tuple((b, a) for a, b in quad)
            set_uv(bm, f, quad)
            c = color
            m = mat
            if column_colors:
                c = column_colors[j % len(column_colors)]
            if band_colors and band_colors[i]:
                c = band_colors[i]
            if band_mats and band_mats[i]:
                m = band_mats[i]
            paint(bm, [f], c, m)
            side_faces.append(f)
    for on, ring, col, m, rev in ((cap_bottom, rings[0], bottom_color, bottom_mat, True),
                                  (cap_top, rings[-1], top_color, top_mat, False)):
        if not on or ring[0] is ring[-1]:
            continue
        f = bm.faces.new(list(reversed(ring)) if rev else ring)
        set_uv(bm, f, [(v.co.x, v.co.y) for v in f.verts])
        paint(bm, [f], col or color, m or mat)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = to_object(bm, name, smooth=smooth, sharp=sharp)
    if flat_cols:
        # sharp vertical seams between columns (staves), smooth along each stave
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        for e in bm.edges:
            a, b = e.verts
            if abs(math.atan2(a.co.y, a.co.x) - math.atan2(b.co.y, b.co.x)) < 1e-4 and len(e.link_faces) == 2:
                e.smooth = False
        bm.to_mesh(ob.data)
        bm.free()
    return ob


def slab(name, size, loc=(0, 0, 0), color="plank", mat="planks", omit=(), rot=(0, 0, 0), colors=None,
         along=None):
    """Box that skips hidden faces. omit: any of '+x','-x','+y','-y','+z','-z'.
    colors: optional {side: palette name}. along: grain axis for project_along."""
    sx, sy, sz = (s / 2 for s in size)
    bm = bm_new()
    v = {}
    for ix in (-1, 1):
        for iy in (-1, 1):
            for iz in (-1, 1):
                v[(ix, iy, iz)] = bm.verts.new((ix * sx, iy * sy, iz * sz))
    sides = {
        "+x": [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
        "-x": [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)],
        "+y": [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)],
        "-y": [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
        "+z": [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
        "-z": [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)],
    }
    for key, quad in sides.items():
        if key in omit:
            continue
        f = bm.faces.new([v[c] for c in quad])
        paint(bm, [f], (colors or {}).get(key, color), mat)
    bm.normal_update()
    K._project_bm(bm, "box")
    ob = to_object(bm, name, smooth=False)
    ob.location = Vector(loc)
    ob.rotation_euler = [math.radians(a) for a in rot]
    bake(ob)
    if along:
        project_along(ob, along)
    return ob


def rbox(name, size, loc=(0, 0, 0), bevel=0.02, segments=2, color="wood", mat="wood", rot=(0, 0, 0),
         along=None, top_color=None):
    """Bevelled box (rounded toy edges), cleaned of degenerate tris, grain along an axis."""
    ob = K.box(name, size, color=color, loc=(0, 0, 0), bevel=bevel, segments=segments, mat=mat, project="box")
    cleanup(ob)
    if along:
        project_along(ob, along)
    if top_color:
        K.paint(ob, top_color, where=lambda c, n: n.z > 0.95)
    ob.location = Vector(loc)
    ob.rotation_euler = [math.radians(a) for a in rot]
    bake(ob)
    return ob


def dash(name, p0, p1, w=0.006, t=0.004, up=(0, -1, 0), color="charcoal", mat="flat"):
    """Cheapest stitch/line: a 4-sided capped bar (12 tris)."""
    return sweep(name, [p0, p1], w, sides=4, color=color, mat=mat, flatten=t / w, cap_offset=0.0, smooth=False,
                 phase=math.pi / 4)


def rounded_rect(w, h, r, n=2):
    """CCW rounded rectangle outline centred at 0 (n extra points per corner arc)."""
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    out = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180)):
        for k in range(n + 2):
            a = math.radians(a0 + 90 * k / (n + 1))
            out.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return out


def board(name, p0, p1, w, h, r=0.01, n=1, up=(0, 0, 1), color="wood", mat="wood", caps=(True, True),
          end_color=None, smooth=True, uv_scale=1.0, end_mat=None):
    """Straight board/beam from p0 to p1 with a rounded-rectangle section (w across, h along `up`).
    Grain (texture v) runs along the board. caps=(start, end) skips hidden end caps."""
    p0, p1 = Vector(p0), Vector(p1)
    t = (p1 - p0).normalized()
    u = Vector(up)
    side = t.cross(u)
    if side.length < 1e-6:
        side = t.cross(Vector((1, 0, 0)))
    side.normalize()
    u2 = side.cross(t).normalized()
    outline = rounded_rect(w, h, r, n)
    bm = bm_new()
    proj = uvl(bm)
    ln = (p1 - p0).length
    rings = []
    for p in (p0, p1):
        rings.append([bm.verts.new(p + side * a + u2 * b) for a, b in outline])
    per = [0.0]
    for i in range(1, len(outline) + 1):
        a, b = outline[i - 1], outline[i % len(outline)]
        per.append(per[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    m = len(outline)
    sides_f = []
    for j in range(m):
        j2 = (j + 1) % m
        f = bm.faces.new((rings[0][j], rings[0][j2], rings[1][j2], rings[1][j]))
        set_uv(bm, f, ((per[j] * uv_scale, 0), (per[j + 1] * uv_scale, 0), (per[j + 1] * uv_scale, ln * uv_scale),
                       (per[j] * uv_scale, ln * uv_scale)))
        sides_f.append(f)
    capf = []
    for k, on in enumerate(caps):
        if on:
            ring = rings[k]
            f = bm.faces.new(list(reversed(ring)) if k == 0 else ring)
            set_uv(bm, f, [(a * uv_scale, b * uv_scale) for a, b in outline] if k == 1 else
                   [(a * uv_scale, b * uv_scale) for a, b in reversed(outline)])
            capf.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    paint(bm, bm.faces, color, mat)
    if end_color and capf:
        paint(bm, capf, end_color, end_mat or mat)
    if capf:
        bmesh.ops.triangulate(bm, faces=capf, quad_method="BEAUTY", ngon_method="BEAUTY")
    return to_object(bm, name, smooth=smooth, sharp=50)


# ----------------------------------------------------------------------------- pumpkin body
def pumpkin_body(name, width=0.6, height=0.45, lobes=8, spl=5, rings=14, groove=0.12, plump=0.5,
                 fullness=0.72, flatness=0.8, top_dimple=0.06, dimple_w=0.4, bottom_dimple=0.015,
                 lumps=0.04, seed=1, twist=0.0, lopsided=0.0, lop_dir=0.0, lean=(0.0, 0.0), flat_top=None,
                 belly=1.0, color="pumpkin", mat="pumpkin", top_color=None, loc=(0, 0, 0), sharp_grooves=True,
                 rib_tiles=0.25, rot_z=0.0, lobe_h=0.0, bottom_color=None):
    """Lobed pumpkin, base at z=0 (before loc), front groove/lobe orientation via rot_z (degrees).

    spl: columns per lobe (groove vertex + spl-1 lobe vertices). plump < 1 rounds the lobes
    (sqrt-sine profile) so they read as fat soft cushions with a crisp V groove.
    fullness < 1 makes the side profile boxier; flatness < 1 flattens top and bottom.
    top_dimple (m) sinks the stem cavity; dimple_w is its width as a fraction of the radius.
    flat_top: fraction of height above which the surface is squashed flat (walkable tops).
    lobe_h: per-lobe height variation (fraction). UVs: each lobe spans rib_tiles of the texture
    (the 'pumpkin' material has 4 ribs per tile, grooves at u = 0.125 + k/4)."""
    rnd = random.Random(seed)
    R = width / 2.0
    lobe_scale = [1.0 + lumps * rnd.uniform(-1, 1) for _ in range(lobes)]
    lobe_hs = [1.0 + lobe_h * rnd.uniform(-1, 1) for _ in range(lobes)]
    segs = lobes * spl
    rz = math.radians(rot_z)

    def lobe_mod(t):
        return 1.0 - groove * (1.0 - math.sin(math.pi * t) ** plump)

    def lobe_val(arr, L, t):
        # smooth blend between neighbouring lobes, equal at the groove
        a, b, c = arr[L - 1], arr[L], arr[(L + 1) % lobes]
        if t < 0.5:
            w = 0.5 - t
            return b + (a - b) * w * w * 2
        w = t - 0.5
        return b + (c - b) * w * w * 2

    # profile (crest), bottom pole k=0 .. top pole k=rings
    prof = []
    for k in range(rings + 1):
        phi = math.pi * k / rings
        u = -math.cos(phi)
        p = math.sin(phi) ** fullness if 0 < k < rings else 0.0
        z = 0.5 + 0.5 * math.copysign(abs(u) ** flatness, u)
        prof.append((p, z))
    zs = [z for _, z in prof]
    lo, hi = min(zs), max(zs)

    def zmap(z):
        zn = min(max((z - lo) / (hi - lo), 0.0), 1.0)
        return zn ** belly * height

    bm = bm_new()
    proj = uvl(bm)
    grid = []
    for k in range(rings + 1):
        p, z = prof[k]
        zz0 = zmap(z)
        if k == 0 or k == rings:
            grid.append(None)
            continue
        row = []
        for j in range(segs):
            L, f = divmod(j, spl)
            t = f / spl
            theta = TAU * (L + t) / lobes + twist * (zz0 / height - 0.5) + rz
            s = lobe_val(lobe_scale, L, t)
            hs = lobe_val(lobe_hs, L, t)
            r = R * p * lobe_mod(t) * s
            r *= 1.0 + lopsided * math.cos(theta - lop_dir)
            zz = zz0
            # stem cavity / base dimple
            if zz0 > 0.5 * height:
                zz = zz0 * hs - top_dimple * math.exp(-(p / dimple_w) ** 2)
            elif zz0 < 0.5 * height:
                zz = zz0 + bottom_dimple * math.exp(-(p / (dimple_w * 0.8)) ** 2)
            if flat_top is not None and zz > flat_top * height:
                zz = flat_top * height + (zz - flat_top * height) * 0.25
            co = Vector((math.cos(theta) * r + lean[0] * zz, math.sin(theta) * r + lean[1] * zz, zz))
            row.append(bm.verts.new(co))
        grid.append(row)
    tz = height - top_dimple
    if flat_top is not None and tz > flat_top * height:
        tz = flat_top * height + (tz - flat_top * height) * 0.25
    top = bm.verts.new((lean[0] * tz, lean[1] * tz, tz))
    bot = bm.verts.new((0, 0, bottom_dimple))

    # v coordinate: arc length along the crest profile, scaled like u (isotropic speckles)
    lobe_w = TAU * R / lobes
    vs = rib_tiles / lobe_w
    crest = [Vector((0, 0, bottom_dimple))]
    for k in range(1, rings):
        p, z = prof[k]
        crest.append(Vector((R * p, 0, zmap(z))))
    crest.append(Vector((0, 0, tz)))
    arcv = [0.0]
    for k in range(1, len(crest)):
        arcv.append(arcv[-1] + (crest[k] - crest[k - 1]).length)
    arcv = [a * vs for a in arcv]

    def u_of(j):
        return 0.125 + rib_tiles * j / spl

    top_faces, bot_faces = [], []
    for k in range(1, rings - 1):
        a, b = grid[k], grid[k + 1]
        for j in range(segs):
            j2 = (j + 1) % segs
            f = bm.faces.new((a[j], a[j2], b[j2], b[j]))
            set_uv(bm, f, ((u_of(j), arcv[k]), (u_of(j + 1), arcv[k]), (u_of(j + 1), arcv[k + 1]),
                           (u_of(j), arcv[k + 1])))
    for j in range(segs):
        j2 = (j + 1) % segs
        f = bm.faces.new((top, grid[rings - 1][j], grid[rings - 1][j2]))
        set_uv(bm, f, ((u_of(j + 0.5), arcv[rings]), (u_of(j), arcv[rings - 1]), (u_of(j + 1), arcv[rings - 1])))
        top_faces.append(f)
        f = bm.faces.new((bot, grid[1][j2], grid[1][j]))
        set_uv(bm, f, ((u_of(j + 0.5), arcv[0]), (u_of(j + 1), arcv[1]), (u_of(j), arcv[1])))
        bot_faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    paint(bm, bm.faces, color, mat)
    if top_color:
        paint(bm, top_faces, top_color, mat)
    if bottom_color:
        paint(bm, bot_faces, bottom_color, mat)
    for f in bm.faces:
        f.smooth = True
    if sharp_grooves:
        groove_verts = set()
        for k in range(1, rings):
            for j in range(0, segs, spl):
                groove_verts.add(grid[k][j])
        for e in bm.edges:
            a, b = e.verts
            if a in groove_verts and b in groove_verts:
                e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = K._link(bpy.data.objects.new(name, me))
    ob.location = Vector(loc)
    ob["top"] = (lean[0] * tz, lean[1] * tz, tz)
    return ob


def top_point(body):
    bpy.context.view_layer.update()
    return body.matrix_world @ Vector(body["top"])


def stem(name, base, height=0.16, radius=0.04, color="stem_brown", mat="bark", curl=0.07, lean_dir=0.0,
         ridges=5, rings=7, flare=1.8, tip_ratio=0.8, cut_color="caramel", uv_scale=3.0, hook=0.6,
         sink=0.025):
    """Ridged, curling stem rising from base. The spine leans toward lean_dir and hooks over at the
    top (hook > 0); the section alternates ridge/furrow; the cut end is a pale disc."""
    bx, by, bz = base
    d = Vector((math.cos(lean_dir), math.sin(lean_dir), 0))
    pts = []
    for i in range(rings):
        t = i / (rings - 1)
        bend = curl * t * t
        drop = hook * curl * t ** 4
        pts.append(Vector((bx, by, bz - sink)) + d * bend + Vector((0, 0, height * t - drop)))

    def rad(t):
        base_r = radius * (1 + (flare - 1) * max(0.0, 1 - t / 0.28) ** 2)
        return base_r * (1 - (1 - tip_ratio) * t)

    sides = ridges * 2
    ob = sweep(name, pts, rad, sides=sides, color=color, mat=mat, profile=lambda j: 1.0 if j % 2 == 0 else 0.8,
               cap_start=False, cap_end=True, cap_offset=-0.15, uv_scale=uv_scale, smooth=True, sharp=50,
               end_color=cut_color, end_mat="wood")
    return ob


def pumpkin_leaf(name, size=0.2, color="vine", under="vine_dark", lobes=5, n=30, cup=0.25, corrugate=0.09,
                 two_sided=False, thick=0.01, vein_color=None, mat="flat", gap=0.6, sharp=70):
    """Palmate pumpkin leaf in local XY, petiole notch at -X, centre at origin, facing +Z.
    Corrugated (tips up, sinuses down) so the lobes catch light. Returns the object."""
    bm = bm_new()
    proj = uvl(bm)

    def outline(a):
        # a in (-pi, pi]; notch at +-pi (petiole side)
        lobe = 0.5 + 0.5 * math.cos(lobes * (a - 0.0))
        r = 0.72 + 0.28 * lobe ** 0.8
        notch = math.exp(-((abs(a) - math.pi) / (gap * 0.5)) ** 2)
        return size * r * (1 - 0.55 * notch)

    c = bm.verts.new((size * -0.05, 0, 0))
    mid, out = [], []
    for i in range(n):
        a = -math.pi + TAU * (i + 0.5) / n
        r = outline(a)
        lobe = math.cos(lobes * a)
        for ring, fr in ((mid, 0.5), (out, 1.0)):
            rr = r * fr
            z = cup * size * fr * fr + corrugate * size * lobe * fr
            ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z)))
    tops = []
    for i in range(n):
        i2 = (i + 1) % n
        tops.append(bm.faces.new((c, mid[i], mid[i2])))
        tops.append(bm.faces.new((mid[i], out[i], out[i2], mid[i2])))
    if two_sided:
        cb = bm.verts.new(c.co - Vector((0, 0, thick)))
        midb = [bm.verts.new(v.co - Vector((0, 0, thick))) for v in mid]
        outb = [bm.verts.new(v.co - Vector((0, 0, thick * 0.3))) for v in out]
        unders = []
        for i in range(n):
            i2 = (i + 1) % n
            unders.append(bm.faces.new((cb, midb[i2], midb[i])))
            unders.append(bm.faces.new((midb[i], midb[i2], outb[i2], outb[i])))
            unders.append(bm.faces.new((out[i], outb[i], outb[i2], out[i2])))
    for f in bm.faces:
        set_uv(bm, f, [(v.co.x, v.co.y) for v in f.verts])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in tops:
        if f.normal.z < 0:
            bmesh.ops.reverse_faces(bm, faces=[f])
    paint(bm, bm.faces, under if two_sided else color, mat)
    paint(bm, tops, color, mat)
    if vein_color:
        # faces straddling each lobe midline (vein) get the vein tint
        veins = []
        for i in range(n):
            a = -math.pi + TAU * (i + 1.0) / n
            if math.cos(lobes * a) > 0.93 and abs(a) < math.pi - gap * 0.6:
                veins.append(tops[2 * i])
                veins.append(tops[2 * i + 1])
        paint(bm, veins, vein_color, mat)
    return to_object(bm, name, smooth=True, sharp=sharp)


def seat(ob, target, x, y, yaw_deg, lift=0.008, tilt=0.0, z_from=5.0):
    """Seat a +Z-facing part (leaf) on target's surface at (x, y): ray straight down, align local Z to
    the surface normal (blended toward up by 1 - tilt... tilt adds extra pitch in degrees along the
    yaw direction), local X along yaw. Bakes into the mesh."""
    bpy.context.view_layer.update()
    tree = target if isinstance(target, BVHTree) else BVHTree.FromObject(target, bpy.context.evaluated_depsgraph_get())
    loc, nrm, _, _ = tree.ray_cast(Vector((x, y, z_from)), Vector((0, 0, -1)))
    if loc is None:
        loc, nrm = Vector((x, y, 0)), Vector((0, 0, 1))
    yaw = math.radians(yaw_deg)
    xd = Vector((math.cos(yaw), math.sin(yaw), 0))
    if tilt:
        nrm = (Matrix.Rotation(math.radians(tilt), 3, Vector((0, 0, 1)).cross(xd).normalized()) @ nrm).normalized()
    xa = (xd - nrm * xd.dot(nrm)).normalized()
    ya = nrm.cross(xa)
    m = Matrix((xa, ya, nrm)).transposed().to_4x4()
    m.translation = loc + nrm * lift
    return transform(ob, m)


def drape(ob, target, x, y, yaw_deg, lift=0.008, relief=1.0):
    """Lay a +Z-facing part (leaf built around its origin) over target: rotate by yaw, move to (x, y)
    and drop every vertex onto the surface below it (keeping its own z relief), so leaves hug curved
    pumpkin shoulders instead of jutting out as flat planes."""
    bpy.context.view_layer.update()
    tree = target if isinstance(target, BVHTree) else BVHTree.FromObject(target, bpy.context.evaluated_depsgraph_get())
    transform(ob, Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(yaw_deg), 4, "Z"))
    for v in ob.data.vertices:
        loc, _, _, _ = tree.ray_cast(Vector((v.co.x, v.co.y, 10.0)), Vector((0, 0, -1)))
        base = loc.z if loc is not None else 0.0
        v.co.z = base + lift + v.co.z * relief
    ob.data.update()
    return ob


def place(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    m = Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot]).to_matrix().to_4x4() @ Matrix.Scale(scale, 4)
    return transform(ob, m)


# ----------------------------------------------------------------------------- 2D outline helpers
def _area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def ccw(poly):
    return poly if _area(poly) > 0 else list(reversed(poly))


def offset_poly(poly, d, clamp=2.5):
    """Inward offset of a CCW polygon by d (miter, clamped)."""
    poly = ccw(poly)
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        bis = n0 + n1
        if bis.length < 1e-6:
            bis = n0
        bis.normalize()
        cosh = max(bis.dot(n0), 1.0 / clamp)
        q = p1 + bis * (d / cosh)
        out.append((q.x, q.y))
    return out


def is_simple(poly):
    n = len(poly)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            c, d = poly[j], poly[(j + 1) % n]
            if (cross(a, b, c) * cross(a, b, d) < 0) and (cross(c, d, a) * cross(c, d, b) < 0):
                return False
    return True


def circle(cx, cz, r, n=12, sx=1.0, sz=1.0, rot=0.0):
    return [(cx + math.cos(TAU * i / n + rot) * r * sx, cz + math.sin(TAU * i / n + rot) * r * sz)
            for i in range(n)]


def rounded_triangle(cx, cz, w, h, tilt=0.0, round_=0.18, point_down=False, arc_pts=0):
    """Cute triangle eye: apex up (or down), corners chamfered (arc_pts adds points per corner)."""
    if point_down:
        corners = [(-w / 2, h / 2), (w / 2, h / 2), (0, -h / 2)]
    else:
        corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (0, h / 2)]
    corners = ccw(corners)
    out = []
    for i in range(3):
        a, b, c = Vector(corners[i - 1]), Vector(corners[i]), Vector(corners[(i + 1) % 3])
        p0 = b + (a - b) * round_
        p2 = b + (c - b) * round_
        out.append(tuple(p0))
        for k in range(arc_pts):
            t = (k + 1) / (arc_pts + 1)
            q = p0 * (1 - t) ** 2 + b * 2 * t * (1 - t) + p2 * t * t
            out.append(tuple(q))
        out.append(tuple(p2))
    ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    return [(cx + x * ct - z * st, cz + x * st + z * ct) for x, z in out]


def arc_band(cx, cz, w, h, thick, n=9, up=True, tip=0.4, grow=0.0):
    """Crescent band (closed-eye arc). up=True draws '^', False draws 'u'. grow offsets outward."""
    s = 1 if up else -1
    g = grow
    outer, inner = [], []
    for i in range(1, n - 1):
        t = i / (n - 1)
        x = -w / 2 + w * t
        bump = math.sin(math.pi * t)
        taper = tip + (1 - tip) * math.sin(math.pi * t)
        half = thick * 0.5 * taper + g
        outer.append((cx + x, cz + s * (h * bump + half)))
        inner.append((cx + x, cz + s * (h * bump - half)))
    left = (cx - w / 2 - g, cz)
    right = (cx + w / 2 + g, cz)
    return ccw([left] + outer + [right] + list(reversed(inner)))


def grin(cx, cz, w, top_sag, depth, n=11, teeth=(), tooth_w=0.05, tooth_h=0.04, lift=(0.0, 0.0), grow=0.0,
         lower_teeth=()):
    """Crescent smile with optional square teeth hanging from the upper lip (uncut pumpkin)."""
    g = grow
    hw = w / 2

    def corner(x):
        t = (x - (cx - hw)) / w
        return lift[0] * (1 - t) ** 3 + lift[1] * t ** 3

    def q_of(x):
        return max(0.0, 1 - ((x - cx) / hw) ** 2)

    def zu(x):
        return cz - top_sag * q_of(x) + corner(x)

    def zl(x):
        q = q_of(x)
        return cz - top_sag * q - (depth - top_sag) * q ** 0.75 + corner(x)

    xs = [cx - hw + w * i / (n - 1) for i in range(1, n - 1)]
    groups = []
    for x in xs:
        if any(abs(x - (cx + tc)) < tooth_w / 2 + 0.025 for tc in teeth):
            continue
        sq = min(1.0, 3 * q_of(x))
        groups.append((x, [(x, zu(x) + g * sq)]))
    for tc in teeth:
        x0 = cx + tc - tooth_w / 2 + g
        x1 = cx + tc + tooth_w / 2 - g
        groups.append((x0, [(x0, zu(x0) + g), (x0, zu(x0) - tooth_h + g), (x1, zu(x1) - tooth_h + g),
                            (x1, zu(x1) + g)]))
    groups.sort(key=lambda it: it[0])
    upper = [p for _, pts in groups for p in pts]
    lgroups = []
    for x in xs:
        if any(abs(x - (cx + tc)) < tooth_w / 2 + 0.025 for tc in lower_teeth):
            continue
        sq = min(1.0, 3 * q_of(x))
        lgroups.append((x, [(cx + (x - cx) * 0.97, zl(x) - g * sq)]))
    for tc in lower_teeth:
        x0 = cx + tc - tooth_w / 2 + g
        x1 = cx + tc + tooth_w / 2 - g
        lgroups.append((x0, [(x0, zl(x0) - g), (x0, zl(x0) + tooth_h - g), (x1, zl(x1) + tooth_h - g),
                             (x1, zl(x1) - g)]))
    lgroups.sort(key=lambda it: it[0])
    lower = [p for _, pts in lgroups for p in pts]
    left = (cx - hw - g, zu(cx - hw))
    right = (cx + hw + g, zu(cx + hw))
    return ccw([left] + upper + [right] + list(reversed(lower)))


def shape_of(fn, **kw):
    return lambda g: fn(grow=g, **kw)


def convex_shape(poly):
    """Grow-aware convex outline: grows/shrinks by scaling about the centroid so the inradius
    changes by g. Never self-intersects and keeps the vertex count."""
    poly = ccw(poly)
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cz = sum(p[1] for p in poly) / n
    inr = 1e9
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        e = (b - a)
        if e.length < 1e-9:
            continue
        nrm = Vector((-e.y, e.x)).normalized()
        inr = min(inr, abs((Vector((cx, cz)) - a).dot(nrm)))

    def shape(g):
        s = max(0.05, 1.0 + g / inr)
        return [(cx + (x - cx) * s, cz + (z - cz) * s) for x, z in poly]
    return shape


# ----------------------------------------------------------------------------- carving
def carve(body, features, depth=0.05, inset=0.02, rim_color="pumpkin_dark", rim_frac=0.4, rim_w=0.012,
          wall_glow="glow_jack", floor_color="glow_jack"):
    """Cut recessed pockets into body (closed mesh at identity transform) from the front (-Y).

    Each feature: {"shape": grow-aware callable or "outline": [(x, z)...], "color": floor glow,
    "wall": inner-wall glow, "inset": float, "depth": float}. Pocket = rim band (pumpkin_dark, the
    cut rind) from the surface to rim_frac of the depth, then a glowing inner wall band, then a
    glowing floor that follows the surface curvature. The wall tapers in by `inset`, so the floor
    and inner walls face the camera and the glow reads from the gameplay angle."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(body, dg)

    def hit(x, z):
        loc, nrm, idx, dist = tree.ray_cast(Vector((x, -5.0, z)), Vector((0, 1, 0)))
        if loc is None:
            raise RuntimeError(f"carve ray missed body at x={x:.3f} z={z:.3f}")
        return loc

    me = bpy.data.meshes.new("_cutter")
    acc = bmesh.new()
    for k, feat in enumerate(features):
        bm = bm_new()
        shape = feat["shape"] if "shape" in feat else convex_shape(feat["outline"])
        outline = shape(0.0)
        d = feat.get("depth", depth)
        ins = feat.get("inset", inset)
        rf = feat.get("rim_frac", rim_frac)
        rw = feat.get("rim_w", rim_w)
        outer2d = shape(0.004)
        mid2d = shape(-rw)
        floor2d = shape(-ins)
        assert len(outer2d) == len(floor2d) == len(outline) == len(mid2d), "shape topology changed with grow"
        for label, poly in (("outline", outline), ("outer", outer2d), ("mid", mid2d), ("floor", floor2d)):
            if not is_simple(poly):
                print(f"WARN carve feature {k}: {label} polygon self-intersects")
        S = [hit(x, z) for x, z in outer2d]
        y_front = min(s.y for s in S) - 0.03
        F = [Vector((x, y_front, z)) for x, z in outer2d]
        M = []
        B = []
        for (x, z), (mx, mz), s in zip(floor2d, mid2d, S):
            h = hit(x, z)
            yb = max(h.y, s.y) + d
            B.append(Vector((x, yb, z)))
            M.append(Vector((mx, s.y + (yb - s.y) * rf, mz)))
        fv = [bm.verts.new(p) for p in F]
        mv = [bm.verts.new(p) for p in M]
        bv = [bm.verts.new(p) for p in B]
        n = len(outline)
        rim = [bm.faces.new((fv[i], fv[(i + 1) % n], mv[(i + 1) % n], mv[i])) for i in range(n)]
        inner = [bm.faces.new((mv[i], mv[(i + 1) % n], bv[(i + 1) % n], bv[i])) for i in range(n)]
        front = bm.faces.new(fv)
        floor = bm.faces.new(list(reversed(bv)))
        paint(bm, rim + [front], feat.get("rim", rim_color), "flat")
        paint(bm, inner, feat.get("wall", wall_glow), "flat")
        paint(bm, [floor], feat.get("color", floor_color), "flat")
        caps = [f for f in bm.faces if len(f.verts) > 4]
        bmesh.ops.triangulate(bm, faces=caps, quad_method="BEAUTY", ngon_method="EAR_CLIP")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if bm.calc_volume(signed=True) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.normal_update()
        K._project_bm(bm, "box")
        bm.to_mesh(me)
        bm.free()
        acc.from_mesh(me)
    for f in acc.faces:
        f.smooth = False
    acc.to_mesh(me)
    acc.free()
    cutter = K._link(bpy.data.objects.new("_cutter", me))
    mod = body.modifiers.new("carve", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    new_me = bpy.data.meshes.new_from_object(body.evaluated_get(dg))
    if len(new_me.polygons) < len(body.data.polygons) * 0.8:
        raise RuntimeError(f"carve: boolean lost geometry ({len(body.data.polygons)} -> {len(new_me.polygons)} faces)")
    body.modifiers.remove(mod)
    old = body.data
    body.data = new_me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(me)
    cleanup(body)
    return body


# ----------------------------------------------------------------------------- cleanup / finish
def cleanup(ob, min_area=2e-7):
    """Triangulate ngons (beauty) and remove degenerate/sliver triangles so gates stay clean."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method="BEAUTY", ngon_method="BEAUTY")
    for _ in range(4):
        bad = [f for f in bm.faces if f.calc_area() < min_area]
        if not bad:
            break
        edges = set()
        for f in bad:
            e = min(f.edges, key=lambda e: e.calc_length())
            edges.add(e)
        bmesh.ops.collapse(bm, edges=[e for e in edges if e.is_valid], uvs=True)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def degenerate_count(objects):
    bpy.context.view_layer.update()
    n = 0
    for ob in objects:
        for o in [ob] + list(ob.children_recursive):
            if o.type != "MESH":
                continue
            me = o.data
            me.calc_loop_triangles()
            for t in me.loop_triangles:
                a, b, c = (o.matrix_world @ me.vertices[i].co for i in t.vertices)
                if (b - a).cross(c - a).length < 1e-8:
                    n += 1
    return n


def weighted_normals(ob):
    """Face-area weighted normals (applied on export): big flat faces stay flat, bevels round."""
    mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
    mod.mode = "FACE_AREA"
    mod.keep_sharp = True
    mod.weight = 50
    return mod


def finish(objects, rel_path, sheet_name, weighted=True, ao_radius=0.8):
    tris = K.tri_count(objects)
    deg = degenerate_count(objects)
    if weighted:
        for ob in objects:
            if ob.type == "MESH":
                weighted_normals(ob)
    K.bake_ao(objects, radius=ao_radius)
    # Godot re-imports only when the .gltf JSON changes (geometry lives in the .bin), so stamp each
    # build into the node extras to force a fresh import for the in-engine preview.
    import time
    for ob in objects:
        ob["build"] = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time() % 1:.4f}"
    out = K.export(objects, rel_path)
    sheet = K.review_sheet(objects, sheet_name)
    print(f"RESULT {sheet_name} tris={tris} degenerate={deg} gltf={out} sheet={sheet}")
    return tris


def run(builds):
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(builds)
    for a in args:
        builds[a]()


def loop_twist(per_ring, steps, sides):
    """Twist per ring for a closed swept loop so the end ring lines up with the start ring."""
    unit = TAU / sides
    k = max(1, round(per_ring * steps / unit))
    return k * unit / steps
