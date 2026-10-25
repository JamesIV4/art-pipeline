"""Origin: S:/Repos/trick-or-treat/art/team/monsters/batch03/mon_kit.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Lane helpers for monsters / batch03 (monster roster + nests, lowpoly_kit v2 textured).

Reuses the finished batch02 helper libraries of two other lanes (read-only imports):
  farm_lib (pumpkins_farm/batch02)   F.sweep / F.lathe / F.pumpkin_body / F.stem / F.pumpkin_leaf /
                                      F.carve / F.tendril / F.cleanup / outline helpers
  dk_kit   (characters_candy/batch02) D.lathe / D.sweep / D.stitches / D.put / D.look / D.part / D.attach

Coordinates: Blender, Z up, front = -Y (glTF/Godot +Z). g2b() converts game (x, y up, z front)
to Blender (x, -z, y); the C++ pivots are given in game coordinates.

Monster rig (contract with the lead):
  empty root '<asset_id>' at the origin, children 'body' (origin = root) and optional 'part_a' /
  'part_b' whose origins sit at their pivots (identity rotation).
Nests: one merged mesh object '<asset_id>', origin at the ground centre.
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

import dk_kit as D  # noqa: E402
import farm_lib as F  # noqa: E402

K = F.K
V = Vector
TAU = 2 * math.pi
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FLAGS = {a for a in ARGS if a.startswith("--")}
IDS = [a for a in ARGS if not a.startswith("--")]


def run(builds):
    """builds: {key: fn}. Builds the keys named on the command line (all when none)."""
    for key in (IDS or list(builds)):
        builds[key]()


def g2b(p):
    return V((p[0], -p[2], p[1]))


def b2g(p):
    return (round(p[0], 4), round(p[2], 4), round(-p[1], 4))


# ---------------------------------------------------------------- shapes
def ell_prof(rings):
    out = []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        out.append((0.0 if i in (0, rings) else math.sin(phi), -math.cos(phi)))
    return out


def blob(name, center, rad, segs=12, rings=8, color="pumpkin", mat="flat", project="sphere", warp=None, rot=None):
    """Smooth ellipsoid (poles on local Z). warp(Vector unit-space co) -> Vector applied before scaling.
    rot: optional Matrix (3x3) applied after scaling."""
    rad = V(rad)

    def w(c):
        if warp:
            c = warp(c)
        c = V((c.x * rad.x, c.y * rad.y, c.z * rad.z))
        if rot is not None:
            c = rot @ c
        return c
    ob = D.lathe(name, ell_prof(rings), segs, color=color, mat=mat, project=project, warp=w, center=(0, 0, 0))
    ob.location = V(center)
    return ob


def lathe(name, prof, segs=12, color="pumpkin", mat="flat", project="cyl", loc=(0, 0, 0), warp=None, center=None):
    return D.lathe(name, prof, segs, color=color, mat=mat, project=project, loc=loc, warp=warp, center=center)


def catmull(points, per=3):
    """Catmull-Rom through points, `per` samples per segment (endpoints kept)."""
    P = [V(p) for p in points]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(V(P[-2]))
    return out


def band_lathe(name, prof, segs=16, colors=("cream",), mats=("fabric",), project="cyl", warp=None, center=None,
               smooth=True):
    """Lathe whose profile points carry a band id: prof = [(r, z, band), ...] bottom to top (r == 0
    makes a pole). The faces between point i and i+1 take band prof[i][2]: colour colors[band %
    len], material mats[band % len]. warp(Vector) -> Vector deforms the finished surface."""
    bm = bmesh.new()
    rings = []
    for r, z, _ in prof:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((math.cos(TAU * j / segs) * r, math.sin(TAU * j / segs) * r, z)) for j in range(segs)])
    groups = {}
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(segs):
            j2 = (j + 1) % segs
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                f = bm.faces.new((A[0], B[j2], B[j]))
            elif len(B) == 1:
                f = bm.faces.new((A[j], A[j2], B[0]))
            else:
                f = bm.faces.new((A[j], A[j2], B[j2], B[j]))
            groups.setdefault(prof[i][2], []).append(f)
    if len(rings[0]) > 1:
        groups.setdefault(prof[0][2], []).append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        groups.setdefault(prof[-2][2], []).append(bm.faces.new(rings[-1]))
    if warp:
        for v in bm.verts:
            v.co = warp(v.co.copy())
    bm.normal_update()
    if center is None:
        zs = [v.co.z for v in bm.verts]
        center = (0, 0, (min(zs) + max(zs)) / 2)
    K._project_bm(bm, project, center=V(center))
    for band, faces in groups.items():
        K._paint_bm(bm, colors[band % len(colors)], mats[band % len(mats)], faces)
    for f in bm.faces:
        f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K._link(bpy.data.objects.new(name, me))


def wrap_prof(z0, z1, rfn, bands, groove=0.12, start_band=0, pole_bottom=False, pole_top=False):
    """Bandage profile from z0 to z1: each band bulges between grooves. rfn(z) -> base radius.
    Returns [(r, z, band)] for band_lathe."""
    out = []
    if pole_bottom:
        out.append((0.0, z0 - 0.002, start_band))
    for k in range(bands):
        za = z0 + (z1 - z0) * k / bands
        zb = z0 + (z1 - z0) * (k + 1) / bands
        b = start_band + k
        out.append((rfn(za) * (1 - groove * 0.5), za, b))
        out.append((rfn(za + (zb - za) * 0.2) * 1.0, za + (zb - za) * 0.2, b))
        out.append((rfn(za + (zb - za) * 0.8) * 1.0, za + (zb - za) * 0.8, b))
    out.append((rfn(z1) * (1 - groove * 0.5), z1, start_band + bands - 1))
    if pole_top:
        out.append((0.0, z1 + 0.002, start_band + bands - 1))
    return out


def tube(name, pts, radii, sides=8, color="vine", mat="flat", **kw):
    return F.sweep(name, pts, radii, sides=sides, color=color, mat=mat, **kw)


def ellipsoid_pt(c, rad, x, z, front=True):
    """Point on the front (-Y) or back of an axis-aligned ellipsoid at (x, z), with its normal."""
    c, rad = V(c), V(rad)
    q = 1 - ((x - c.x) / rad.x) ** 2 - ((z - c.z) / rad.z) ** 2
    y = c.y + (-1 if front else 1) * rad.y * math.sqrt(max(q, 0.0))
    p = V((x, y, z))
    n = V(((p.x - c.x) / rad.x ** 2, (p.y - c.y) / rad.y ** 2, (p.z - c.z) / rad.z ** 2)).normalized()
    return p, n


def ellipsoid_dir(c, rad, d):
    c, rad, d = V(c), V(rad), V(d).normalized()
    s = 1.0 / math.sqrt((d.x / rad.x) ** 2 + (d.y / rad.y) ** 2 + (d.z / rad.z) ** 2)
    p = c + d * s
    n = V(((p.x - c.x) / rad.x ** 2, (p.y - c.y) / rad.y ** 2, (p.z - c.z) / rad.z ** 2)).normalized()
    return p, n


def bvh(*objs):
    bpy.context.view_layer.update()
    verts, polys = [], []
    for ob in objs:
        mw = ob.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in ob.data.vertices]
        polys += [[base + i for i in p.vertices] for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def surf(tree, origin, direction, dist=10.0):
    """Ray hit (point, normal) or (None, None)."""
    loc, nrm, _, _ = tree.ray_cast(V(origin), V(direction).normalized(), dist)
    return loc, nrm


def put(ob, loc, z_dir, up=(0, 0, 1), roll=0.0, scale=(1, 1, 1)):
    return D.put(ob, loc, z_dir, up=up, roll=roll, scale=scale)


def bake(ob):
    bpy.context.view_layer.update()
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.update()
    return ob


def xform(ob, m):
    ob.data.transform(m)
    ob.data.update()
    return ob


def mirror_x(ob, name=None):
    """Mirror an object across X in place (winding flipped back so normals stay outward)."""
    bake(ob)
    ob.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    if name:
        ob.name = name
    return ob


def cone(name, h, r, segs=8, color="bone", mat="flat", bend=0.0, tip=0.0, lo=False):
    """Soft rounded cone/horn pointing up local Z, base at z=0. bend curls it toward +Y.
    lo=True: a cheap 3-ring spike (straw strands, small fangs)."""
    if lo:
        prof = [(r, 0.0), (r * 0.6, h * 0.5), (0.0, h)]
    else:
        prof = [(r, -0.01), (r, 0.0), (r * 0.9, h * 0.3), (r * 0.66, h * 0.6), (r * 0.38, h * 0.84),
                (max(tip, r * 0.12), h * 0.96), (0.0, h)]
    return D.lathe(name, prof, segs, color=color, mat=mat, project="cyl",
                   warp=(lambda c: V((c.x, c.y + bend * (c.z / h) ** 2 * h, c.z))) if bend else None)


def disc(name, r, depth, segs=12, color="ink", mat="flat"):
    return K.cylinder(name, r, depth, color=color, mat=mat, verts=segs)


# ---------------------------------------------------------------- faces
def eye_cute(prefix, p, n, w, h, d=None, roll=0.0, color="ink", hl="eye_white", glint=None, sink=0.004,
             segs=12, rings=6):
    """Big glossy cartoon eye on a surface point p with normal n: a domed ink oval, a big highlight
    up-left (as seen from the front) and a small one low-right; optional coloured glint at the
    bottom (glow_* for spooky-cute)."""
    d = d or min(w, h) * 0.45
    eye = blob(prefix, (0, 0, 0), (w, h, d), segs=segs, rings=rings, color=color)
    put(eye, V(p) - V(n) * sink, n, roll=roll)
    M = D.look(n, roll=roll)

    def on(lx, ly, lift=0.0015):
        lz = d * math.sqrt(max(1 - (lx / w) ** 2 - (ly / h) ** 2, 0.0))
        return V(p) - V(n) * sink + M @ V((lx, ly, lz)) + V(n) * lift, (M @ V((lx / w ** 2, ly / h ** 2, lz / d ** 2))).normalized()
    out = [eye]
    if glint:
        q, qn = on(0.0, -h * 0.58, 0.0)
        g = blob(prefix + "_gl", (0, 0, 0), (w * 0.55, h * 0.24, d * 0.22), segs=8, rings=4, color=glint)
        put(g, q, qn, roll=roll)
        out.append(g)
    q, qn = on(-w * 0.32, h * 0.34)
    a = blob(prefix + "_h1", (0, 0, 0), (w * 0.4, h * 0.33, d * 0.2), segs=8, rings=4, color=hl)
    put(a, q, qn, roll=roll)
    q, qn = on(w * 0.36, -h * 0.18)
    b = blob(prefix + "_h2", (0, 0, 0), (w * 0.18, h * 0.15, d * 0.16), segs=6, rings=3, color=hl)
    put(b, q, qn, roll=roll)
    return out + [a, b]


def eye_glow(prefix, p, n, w, h, glow="glow_jack_hot", pupil="ink", pw=0.42, ph=0.62, roll=0.0, sink=0.004,
             look=(0.0, 0.0), segs=12):
    """Glowing eye: an emissive oval with a dark pupil and a white glint."""
    d = min(w, h) * 0.35
    eye = blob(prefix, (0, 0, 0), (w, h, d), segs=segs, rings=5, color=glow)
    put(eye, V(p) - V(n) * sink, n, roll=roll)
    M = D.look(n, roll=roll)

    def on(lx, ly, lift=0.0015):
        lz = d * math.sqrt(max(1 - (lx / w) ** 2 - (ly / h) ** 2, 0.0))
        return V(p) - V(n) * sink + M @ V((lx, ly, lz)) + V(n) * lift, (M @ V((lx / w ** 2, ly / h ** 2, lz / d ** 2))).normalized()
    out = [eye]
    if pupil:
        q, qn = on(look[0] * w, look[1] * h, 0.0)
        pp = blob(prefix + "_p", (0, 0, 0), (w * pw, h * ph, d * 0.35), segs=8, rings=4, color=pupil)
        put(pp, q, qn, roll=roll)
        q, qn = on(look[0] * w - w * pw * 0.35, look[1] * h + h * ph * 0.4, 0.004)
        g = blob(prefix + "_g", (0, 0, 0), (w * pw * 0.38, h * ph * 0.3, d * 0.15), segs=6, rings=3, color="eye_white")
        put(g, q, qn, roll=roll)
        out += [pp, g]
    return out


def smile(name, p, n, w, h, thick, color="ink", up=True, depth=0.008, roll=0.0, n_pts=9):
    """Crescent smile prism laid on a surface (corners up when up=True)."""
    pts = []
    for i in range(n_pts):
        t = i / (n_pts - 1)
        x = -w / 2 + w * t
        s = math.sin(math.pi * t)
        pts.append((x, (-h * s if up else h * s) - thick * 0.5 * (0.35 + 0.65 * s)))
    for i in range(n_pts - 2, 0, -1):
        t = i / (n_pts - 1)
        x = -w / 2 + w * t
        s = math.sin(math.pi * t)
        pts.append((x, (-h * s if up else h * s) + thick * 0.5 * (0.35 + 0.65 * s)))
    pts = F.ccw(pts)
    ob = K.polygon_prism(name, pts, depth, color=color, mat="flat")
    put(ob, V(p) - V(n) * depth * 0.6, n, roll=roll)
    return ob


def cheek(name, p, n, w, h, color="cheek_pink", roll=0.0, segs=8, rings=3):
    ob = blob(name, (0, 0, 0), (w, h, min(w, h) * 0.25), segs=segs, rings=rings, color=color)
    put(ob, V(p) - V(n) * 0.002, n, roll=roll)
    return ob


def bone(name, a, b, r, color="bone", mat="flat", knob=1.55, sides=8, knob_segs=8, knob_rings=5):
    """Cartoon bone: a waisted shaft between a and b with a double knob at each end."""
    a, b = V(a), V(b)
    d = (b - a)
    t = d.normalized()
    pts = [a.lerp(b, k) for k in (0.0, 0.5, 1.0)]
    rr = [r * 1.05, r * 0.82, r * 1.05]
    parts = [tube(name + "_shaft", pts, rr, sides=sides, color=color, mat=mat, cap_start=False, cap_end=False)]
    side = t.cross(V((0, 0, 1)))
    if side.length < 0.1:
        side = t.cross(V((1, 0, 0)))
    side.normalize()
    for e, s in ((a, -1), (b, 1)):
        for k in (-1, 1):
            parts.append(blob(f"{name}_k{s}{k}", e + side * k * r * 0.75 + t * s * r * 0.25, (r * knob * 0.62,) * 3,
                              segs=knob_segs, rings=knob_rings, color=color, mat=mat))
    return K.merge(parts, name)


def plate(name, outline, th, color, mat="flat", bevel=0.01, segments=1, project="box", center=(0, 0, 0)):
    """Flat slab from a 2D outline [(x, z), ...] in the XZ plane, th thick along Y, rim bevelled."""
    outline = [V(p) for p in F.ccw([tuple(p) for p in outline])]
    bm = bmesh.new()
    front = [bm.verts.new((p.x, -th / 2, p.y)) for p in outline]
    back = [bm.verts.new((p.x, th / 2, p.y)) for p in outline]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    k = len(outline)
    for i in range(k):
        bm.faces.new((front[i], back[i], back[(i + 1) % k], front[(i + 1) % k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bevel > 0:
        rim = [e for e in bm.edges if abs(e.verts[0].co.y - e.verts[1].co.y) < 1e-6]
        bmesh.ops.bevel(bm, geom=rim, offset=bevel, segments=segments, profile=0.5, affect="EDGES", clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY",
                          ngon_method="EAR_CLIP")
    return D.mesh(bm, name, color, mat, project, smooth=True, center=center)


def seam(name, target, center, radius, n=22, zig=0.02, color="glow_jack", tube_r=0.012, lift=0.003, sides=3):
    """Zig-zag glowing seam ringing a point on top of target (rays straight down)."""
    tree = target if isinstance(target, BVHTree) else bvh(target)
    pts = []
    c = V(center)
    for i in range(n + 1):
        a = TAU * i / n
        r = radius + (zig if i % 2 else -zig)
        loc, nrm = surf(tree, (c.x + math.cos(a) * r, c.y + math.sin(a) * r, c.z + 3.0), (0, 0, -1))
        pts.append(loc + nrm * lift)
    return F.sweep(name, pts, tube_r, sides=sides, color=color, mat="flat", cap_start=False, cap_end=False, smooth=False)


def ground_path(pts, z=0.0):
    return [V((p[0], p[1], z if len(p) < 3 else p[2])) for p in pts]


# ---------------------------------------------------------------- rig + finish
def part(objs, name, joint_game):
    if "--pieces" in FLAGS:
        print("  ", name, ", ".join(f"{o.name}:{D.tris(o)}" for o in objs))
    ob = K.merge(objs, name)
    j = g2b(joint_game)
    ob.data.transform(Matrix.Translation(-j))
    ob.location = j
    return ob


def rig(asset_id, body_objs, parts=None):
    """parts: {'part_a': (objs, pivot_game), ...}. Returns the root empty."""
    root = K.empty(asset_id, (0, 0, 0))
    if "--pieces" in FLAGS:
        print("   body", ", ".join(f"{o.name}:{D.tris(o)}" for o in body_objs))
    body = K.merge(body_objs, "body")
    D.attach(body, root)
    for name, (objs, pivot) in (parts or {}).items():
        p = part(objs, name, pivot)
        D.attach(p, root)
    return root


def _meshes(root):
    return [o for o in [root] + list(root.children_recursive) if o.type == "MESH"]


def finish(root, asset_id, ao_radius=0.35, ao_strength=0.85, ground_ao=True, sheet=True, weighted=False,
           preview_lift=0.0):
    """preview_lift: with --lift on the command line the root is raised this much (review only:
    floating assets are half buried by the engine preview). Always re-export without it."""
    meshes = _meshes(root)
    for o in meshes:
        F.cleanup(o)
        if weighted:
            F.weighted_normals(o)
    deg = F.degenerate_count([root])
    bpy.context.view_layer.update()
    report = []
    for o in meshes:
        report.append(f"{o.name}:{D.tris(o)}@{b2g(o.matrix_world.translation)}")
    lo = V((1e9, 1e9, 1e9))
    hi = V((-1e9, -1e9, -1e9))
    for o in meshes:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = V((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = V((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
    K.bake_ao([root], samples=32, radius=ao_radius, strength=ao_strength, ground=ground_ao)
    if "--lift" in FLAGS and preview_lift:
        root.location.z += preview_lift
        print("WARN exported LIFTED for preview only; re-export without --lift")
    import time
    root["build"] = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time() % 1:.4f}"
    out = K.export([root], f"monsters/{asset_id}")
    sh = K.review_sheet([root], asset_id) if (sheet and "--nosheet" not in FLAGS) else None
    tris = K.tri_count([root])
    size = hi - lo
    print(f"RESULT {asset_id} tris={tris} degenerate={deg} size(x,y_up,z)=({size.x:.2f},{size.z:.2f},{size.y:.2f}) "
          f"minz={lo.z:.3f} maxz={hi.z:.3f} parts=[{'; '.join(report)}] gltf={out} sheet={sh}")
    return tris


def clip_below(ob, z=0.0):
    """Drop everything under the ground plane (open bottoms are never seen)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1), clear_inner=True)
    for v in bm.verts:
        if abs(v.co.z - z) < 1e-5:
            v.co.z = z
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def nest_finish(objs, asset_id, ao_radius=0.8, ao_strength=0.9, weighted=False, clip=True):
    ob = K.merge(objs, asset_id)
    root = ob
    if clip:
        clip_below(ob)
    F.cleanup(ob)
    if weighted:
        F.weighted_normals(ob)
    return finish(root, asset_id, ao_radius=ao_radius, ao_strength=ao_strength)


def rnd(seed):
    return random.Random(seed)
