"""Origin: S:/Repos/trick-or-treat/art/team/candy_variety/batch03/cv_kit.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

candy_variety batch03 helpers (Blender side). Kept in the lane folder on purpose.

Reuses art/tools/lowpoly_kit.py (K) and characters_candy/batch02/dk_kit.py (D, read-only import).

loft()        rings of points -> bmesh quads/tri-fans, returns (bm, [(face, ring_i, seg_j)], caps)
mk()          bmesh -> palette-painted object (base colour + {colour: faces}), optional flat faces
lathe_rings() (r, z) profile -> rings around Z with optional twist / per-angle radius fn / squash
puffy()       a 2D outline (x right, z up) inflated into a rounded slab facing front (-Y)
decal()       a flat outline conformed onto a surface (BVH ray cast) - prints, eyes, dots
blob()        a small squashed sphere placed on a surface point along its normal
finish()      merge, recentre on the bbox centre, scale to the target size, AO, export, tiles
"""
import json
import math
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
# art-pipeline port: was `ROOT = HERE.parents[3]` (game root, only used for sys.path)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import dk_kit as D  # noqa: E402
from dk_kit import K  # noqa: E402

V = Vector
def _batch_dir():
    """Folder of the build script Blender is running (--python <script>), else the cwd.
    Added by the art-pipeline port: per-batch outputs used to sit next to this kit."""
    argv = sys.argv
    if "--python" in argv and argv.index("--python") + 1 < len(argv):
        return Path(argv[argv.index("--python") + 1]).resolve().parent
    return Path.cwd()


TILES = _batch_dir() / "tiles"
RESULTS = _batch_dir() / "results"
TAU = 2 * math.pi


# ---------------------------------------------------------------- mesh building
def loft(rings, caps=(True, True), closed=False):
    bm = bmesh.new()
    vr = [[bm.verts.new(V(p)) for p in r] for r in rings]
    info = []
    nr = len(vr)
    for i in range(nr if closed else nr - 1):
        A, B = vr[i], vr[(i + 1) % nr]
        n = max(len(A), len(B))
        for j in range(n):
            j2 = (j + 1) % n
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                f = bm.faces.new((A[0], B[j2], B[j]))
            elif len(B) == 1:
                f = bm.faces.new((A[j], A[j2], B[0]))
            else:
                f = bm.faces.new((A[j], A[j2], B[j2], B[j]))
            info.append((f, i, j))
    capf = []
    if not closed:
        if caps[0] and len(vr[0]) > 2:
            capf.append(bm.faces.new(list(reversed(vr[0]))))
        if caps[1] and len(vr[-1]) > 2:
            capf.append(bm.faces.new(vr[-1]))
    return bm, info, capf


def mk(bm, name, base, groups=None, smooth=True, flat=(), project="sphere", center=(0, 0, 0)):
    bm.normal_update()
    K._project_bm(bm, project, center=V(center))
    K._paint_bm(bm, base, "flat")
    for c, fs in (groups or {}).items():
        if c != base and fs:
            K._paint_bm(bm, c, "flat", fs)
    fl = set(flat)
    for f in bm.faces:
        f.smooth = smooth and f not in fl
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K._link(bpy.data.objects.new(name, me))


def group(info, pick):
    """pick(i, j, face) -> colour or None. Returns {colour: [faces]}."""
    g = {}
    for f, i, j in info:
        c = pick(i, j, f)
        if c:
            g.setdefault(c, []).append(f)
    return g


def lathe_rings(prof, n=16, phase=0.0, twist=None, fn=None, sx=1.0, sy=1.0):
    """prof [(r, z)]; twist(z) -> extra angle; fn(a, z, k) -> (radius mult, dz) for ring k."""
    rings = []
    for k, (r, z) in enumerate(prof):
        if r < 1e-7:
            rings.append([V((0, 0, z))])
            continue
        ring = []
        for j in range(n):
            a = TAU * j / n + phase + (twist(z) if twist else 0.0)
            m, dz = fn(a, z, k) if fn else (1.0, 0.0)
            ring.append(V((math.cos(a) * r * m * sx, math.sin(a) * r * m * sy, z + dz)))
        rings.append(ring)
    return rings


def rot_bm(bm, axis, deg):
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(deg), 3, axis))


def xf(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """Set an object transform (degrees). K.merge bakes it."""
    ob.location = V(loc)
    ob.rotation_euler = [math.radians(a) for a in rot]
    ob.scale = V(scale)
    return ob


def sphere(name, r, color, loc=(0, 0, 0), scale=(1, 1, 1), seg=10, rings=7, rot=(0, 0, 0)):
    return K.sphere(name, r, color=color, loc=loc, scale=scale, segments=seg, rings=rings, rot=rot)


def stick(name, length, r=0.014, color="lolly_white", top=(0, 0, 0), direction=(0, 0, -1), verts=6):
    """Stick from 'top' running along direction."""
    d = V(direction).normalized()
    ob = K.cylinder(name, r, length, color=color, verts=verts, smooth=True)
    D.put(ob, V(top) + d * (length / 2), d)
    return ob


def tube(name, pts, radii, sides=8, color="lolly_white", twist=0.0, pick=None, warp=None, up=None):
    """Tube through pts whose face columns spiral by 'twist' radians per ring, so pick(i, j) can colour
    whole columns as clean helical stripes. warp(a, i) -> radius multiplier (a in the untwisted frame)."""
    pts = [V(p) for p in pts]
    if isinstance(radii, (int, float)):
        radii = [radii] * len(pts)
    frames = D._frames(pts)
    if up is not None:
        t0, n0, b0 = frames[0]
        u = (V(up) - t0 * V(up).dot(t0)).normalized()
        ang = math.atan2(u.dot(b0), u.dot(n0))
        frames = [(t, n * math.cos(ang) + b * math.sin(ang), -n * math.sin(ang) + b * math.cos(ang)) for t, n, b in frames]
    rings = []
    for i, (p, r, (t, n, b)) in enumerate(zip(pts, radii, frames)):
        if r < 1e-6:
            rings.append([p])
            continue
        ring = []
        for j in range(sides):
            a0 = TAU * j / sides
            a = a0 + twist * i
            k = warp(a, i) if warp else 1.0
            ring.append(p + (n * math.cos(a) + b * math.sin(a)) * r * k)
        rings.append(ring)
    bm, info, caps = loft(rings)
    g = group(info, pick) if pick else {}
    return mk(bm, name, color, g, smooth=True, flat=caps, project="sphere")


def sweep(name, pts, radii, sides=8, color="candy_cherry", paint=None, closed=False, warp=None, up=None):
    pnt = (lambda i, j: (lambda c: (c, "flat") if c else None)(paint(i, j))) if paint else None
    return D.sweep(name, pts, radii, sides=sides, color=color, mat="flat", project="sphere", smooth=True,
                   closed=closed, warp=warp, center=(0, 0, 0), up=up, paint=pnt)


# ---------------------------------------------------------------- 2D outlines (x right, y up), CCW
def ccw(pts):
    a = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else list(reversed(pts))


def ngon(n, r=1.0, phase=0.0, sx=1.0, sy=1.0):
    return [(math.cos(TAU * i / n + phase) * r * sx, math.sin(TAU * i / n + phase) * r * sy) for i in range(n)]


def star_pts(n=5, r1=1.0, r2=0.48):
    return [(math.cos(math.pi / 2 + i * math.pi / n) * (r1 if i % 2 == 0 else r2),
             math.sin(math.pi / 2 + i * math.pi / n) * (r1 if i % 2 == 0 else r2)) for i in range(2 * n)]


def heart_pts(n=22):
    pts = []
    for i in range(n):
        t = TAU * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x / 16.5, (y + 2.5) / 16.5))
    return ccw(pts)


_BAT_R = [(0.16, -0.10), (0.32, -0.30), (0.50, -0.09), (0.70, -0.27), (1.0, 0.14), (0.62, 0.21), (0.30, 0.30),
          (0.17, 0.22), (0.15, 0.50), (0.06, 0.32)]
BAT = ccw([(0.0, -0.36)] + _BAT_R + [(0.0, 0.29)] + [(-x, y) for x, y in reversed(_BAT_R)])
_BS_R = [(0.22, -0.1), (0.48, -0.3), (0.62, -0.06), (1.0, 0.16), (0.52, 0.26), (0.2, 0.24), (0.16, 0.52), (0.06, 0.32)]
BAT_SIMPLE = ccw([(0.0, -0.38)] + _BS_R + [(0.0, 0.3)] + [(-x, y) for x, y in reversed(_BS_R)])


def pumpkin_pts(n=18):
    pts = []
    for i in range(n):
        a = TAU * i / n
        notch = 1 - 0.13 * max(0.0, math.sin(a)) ** 8 - 0.08 * max(0.0, -math.sin(a)) ** 8
        pts.append((math.cos(a) * 1.15 * notch, math.sin(a) * 0.9 * notch))
    return ccw(pts)


def ghost_pts(n_top=9, waves=3):
    pts = []
    for i in range(n_top + 1):                      # dome from right to left
        a = math.pi * i / n_top
        pts.append((math.cos(a) * 0.62, 0.15 + math.sin(a) * 0.75))
    pts += [(-0.66, -0.25), (-0.72, -0.62)]
    for k in range(waves * 2 + 1):                  # wavy hem left to right
        x = -0.72 + 1.44 * k / (waves * 2)
        pts.append((x, -0.62 if k % 2 == 0 else -0.46))
    pts += [(0.66, -0.25)]
    return ccw(pts)


def inset2d(pts, d):
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = V(pts[i - 1] + (0,)), V(pts[i] + (0,)), V(pts[(i + 1) % n] + (0,))
        e1 = (p1 - p0).normalized()
        e2 = (p2 - p1).normalized()
        n1 = V((-e1.y, e1.x, 0))
        n2 = V((-e2.y, e2.x, 0))
        m = n1 + n2
        if m.length < 1e-6:
            m = n1
        m.normalize()
        k = max(m.dot(n1), 0.35)
        q = p1 + m * (d / k)
        out.append((q.x, q.y))
    return out


# ---------------------------------------------------------------- puffy slab
def puffy(name, outline, size, thick, color, edge=0.3, groups_fn=None, front_color=None, back_color=None):
    """outline unit coords -> slab in the XZ plane, |x| up to size/2-ish, thickness along Y.
    edge: inset of the faces relative to thickness (rounded rim)."""
    pts = ccw([(x * size / 2, y * size / 2) for x, y in outline])
    # rounded rim: the face outlines are the outline scaled about its centroid (a similar polygon, so it
    # never self-intersects even for concave shapes such as hearts, bats and ghosts)
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    k = max(0.62, 1 - thick * edge / (size * 0.42))
    ins = [(cx + (x - cx) * k, cz + (z - cz) * k) for x, z in pts]
    t = thick / 2

    def ring(p2, y):
        return [V((x, y, z)) for x, z in p2]
    rings = [ring(ins, -t), ring(pts, -t * 0.35), ring(pts, t * 0.35), ring(ins, t)]
    bm, info, caps = loft(rings)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    g = {}
    if front_color:
        g.setdefault(front_color, []).append(caps[0])
    if back_color:
        g.setdefault(back_color, []).append(caps[1])
    if groups_fn:
        for c, fs in groups_fn(info).items():
            g.setdefault(c, []).extend(fs)
    return mk(bm, name, color, g, smooth=True, flat=caps, project="box")


# ---------------------------------------------------------------- surface decals
def tree_of(objs):
    bpy.context.view_layer.update()
    verts, polys = [], []
    for o in objs:
        mw = o.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def surf(tree, origin, direction, dist=3.0):
    loc, nrm, _, _ = tree.ray_cast(V(origin), V(direction).normalized(), dist)
    return loc, nrm


def decal(tree, origin, direction, outline, size, color, up=(0, 0, 1), off=0.004, name="decal", spin=0.0,
          flatten=None, sub=0):
    """Conform a flat outline (unit coords, CCW) onto the surface hit by a ray. Returns object or None.
    sub: edge cuts before conforming (large decals on curved bodies, so the triangles don't sink)."""
    loc, nrm = surf(tree, origin, direction)
    if loc is None:
        return None
    n = nrm.normalized()
    u_up = V(up)
    v = u_up - n * u_up.dot(n)
    if v.length < 1e-5:
        v = n.orthogonal()
    v.normalize()
    if spin:
        v = Matrix.Rotation(math.radians(spin), 3, n) @ v
    u = v.cross(n)
    bm = bmesh.new()
    vs = [bm.verts.new(loc + (u * x + v * y) * (size / 2)) for x, y in ccw(list(outline))]
    f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f])
    if sub:
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=sub, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
    if flatten is None:
        for vt in bm.verts:
            h, hn = surf(tree, vt.co + n * 0.06, -n, 0.2)
            vt.co = (h + n * off) if h is not None else (vt.co + n * off)
    else:
        for vt in bm.verts:
            vt.co = vt.co + n * off
    return mk(bm, name, color, smooth=False, project="box")


def blob(name, tree, origin, direction, r, color, flat=0.55, seg=6, rings=4, sink=0.3):
    loc, nrm = surf(tree, origin, direction)
    if loc is None:
        return None
    ob = K.sphere(name, r, color=color, segments=seg, rings=rings, smooth=True)
    D.put(ob, loc - nrm * r * flat * sink, nrm, scale=(1, 1, flat))
    return ob


def toward_axis_x(x, ang, rad=0.6):
    """Ray (origin, dir) hitting a body laid along X at angle ang (0 = front -Y, 90 = top)."""
    a = math.radians(ang)
    o = V((x, -math.cos(a) * rad, math.sin(a) * rad))
    return o, V((x, 0, 0)) - o


def toward_center(dirv, rad=0.8, center=(0, 0, 0)):
    d = V(dirv).normalized()
    return V(center) + d * rad, -d


def fib_dirs(n, seed=0, jitter=0.0):
    rnd = random.Random(seed)
    out = []
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        a = g * i + rnd.uniform(-jitter, jitter)
        out.append(V((math.cos(a) * r, math.sin(a) * r, z)))
    return out


# ---------------------------------------------------------------- finishing
def bbox(ob):
    xs = [v.co for v in ob.data.vertices]
    lo = V((min(c.x for c in xs), min(c.y for c in xs), min(c.z for c in xs)))
    hi = V((max(c.x for c in xs), max(c.y for c in xs), max(c.z for c in xs)))
    return lo, hi


def render_tile(ob, aid, frame=0.75, res=256):
    TILES.mkdir(exist_ok=True)
    K._preview_colors([ob])
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "STUDIO"
    sh.color_type = "VERTEX"
    sh.show_shadows = False
    sh.show_cavity = False
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.color = (0.03, 0.035, 0.09)
    cd = bpy.data.cameras.new("tilecam")
    cd.type = "ORTHO"
    cd.ortho_scale = frame
    cam = K._link(bpy.data.objects.new("tilecam", cd))
    scene.camera = cam
    for k, yaw in enumerate((-25, 65)):
        p = math.radians(30)
        y = math.radians(yaw)
        d = V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
        cam.location = d * 5
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(TILES / f"{aid}_{k}.png")
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    prev = ob.data.color_attributes.get("Preview")
    if prev:
        ob.data.color_attributes.remove(prev)


def finish(parts, aid, size, tier, args, budget):
    ob = K.merge(parts, aid)
    lo, hi = bbox(ob)
    ob.data.transform(Matrix.Translation(-(lo + hi) / 2))
    ext = max(hi - lo)
    ob.data.transform(Matrix.Scale(size / ext, 4))
    # triangulate here (export would anyway) and drop zero-area slivers from collinear n-gon corners
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
    bad = [f for f in bm.faces if f.calc_area() < 1e-8]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    lo, hi = bbox(ob)
    tris = K.tri_count([ob])
    K.bake_ao([ob], samples=32, radius=0.1, strength=0.6, ground=False)
    if "--lift" in args:     # REVIEW ONLY (engine preview stands the origin on the grass); re-export without
        ob.data.transform(Matrix.Translation((0, 0, -lo.z + 0.25)))
    K.export([ob], f"candy/{aid}")
    if "--notile" not in args:
        render_tile(ob, aid, frame=0.75 if tier < 2 else 0.75)
    if "--sheet" in args:
        K.review_sheet([ob], aid)
    RESULTS.mkdir(exist_ok=True)
    dims = [round(x, 3) for x in (hi - lo)]
    (RESULTS / f"{aid}.json").write_text(json.dumps({"id": aid, "tris": tris, "budget": budget, "tier": tier,
                                                      "dims": dims}))
    flag = "" if tris <= budget else "  OVER BUDGET"
    print(f"BUILT {aid:<32} tier {tier} tris {tris:>4}/{budget} dims {dims}{flag}")
    return ob
