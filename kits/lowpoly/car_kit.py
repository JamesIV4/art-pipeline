"""Origin: S:/Repos/trick-or-treat/art/team/vehicles/batch03/car_kit.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Shared builders for the vehicles lane, batch03 (decorative parked cars, rebuilt from scratch).

Reuses landmarks/batch03/lm_common.py (-> yard_street/batch02/yard_common.py helpers) and adds:
  * fillet_outline()  closed 2D polygon with rounded corners (side profile of a car body)
  * lower_body()      side profile lofted across X with per-vertex rounding radii: crisp concave
                      wheel arches with dark wheel wells, planar flat-shaded side panels, soft
                      bubbly top/nose/tail edges, optional recessed pickup bed
  * cabin()           greenhouse lofted up Z from rounded-rect rings; window bands are recessed
                      2.5 cm (dark glass) with chrome reveals; pillars are the un-recessed parts
  * glass streaks, door seams (flat ribbons on the body), wheels, lamps, bumpers, plates, jacks
Coordinates: Blender metres, Z up, front faces -Y, origin at the ground centre.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit
from lm_common import *  # noqa: E402,F401,F403
from lm_common import ARGS, ellipse, ribbed, stroke  # noqa: E402,F401
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Quaternion  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

PAINT_MAT = "flat"  # glossy toy paint: no brush texture on car bodies (metal read as hairline streaks)
GLASS = "shadow_navy"
STREAK = "foil_silver"
CHROME = "silver"
WELL = "charcoal"


# ------------------------------------------------------------------ small utils
def V2(y, z):
    return Vector((y, z))


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def mkobj(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K._link(bpy.data.objects.new(name, me))


def orient(ob, loc, direction, up=(0, 0, 1), roll=0.0):
    """Rotate an object built facing local +Z so that +Z points along `direction`, then bake."""
    d = Vector(direction).normalized()
    q = Vector((0, 0, 1)).rotation_difference(d)
    if roll:
        q = q @ Quaternion((0, 0, 1), math.radians(roll))
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = q
    ob.location = Vector(loc)
    return bake(ob)


class Surf:
    """Ray caster over a set of baked objects."""

    def __init__(self, objs):
        verts, polys = [], []
        for o in objs:
            base = len(verts)
            verts += [o.matrix_world @ v.co for v in o.data.vertices]
            polys += [[base + i for i in p.vertices] for p in o.data.polygons]
        self.bvh = BVHTree.FromPolygons(verts, polys)

    def hit(self, origin, direction, far=10.0):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized(), far)
        return loc, nrm

    def side(self, sx, y, z):
        """Point on the body side (sx = +-1) at (y, z), cast inward from outside."""
        return self.hit((sx * 3.0, y, z), (-sx, 0, 0))

    def end(self, sy, x, z):
        """Point on the nose (sy=-1) or tail (sy=+1) at (x, z)."""
        return self.hit((x, sy * 4.0, z), (0, -sy, 0))

    def top(self, x, y):
        return self.hit((x, y, 4.0), (0, 0, -1))


def scale_uv(ob, k):
    """Scale the material UVs (bigger, softer brush strokes on large painted panels)."""
    uv = ob.data.uv_layers.get("UVMap")
    if uv:
        for d in uv.data:
            d.uv = (d.uv[0] * k, d.uv[1] * k)
    return ob


def ribbon(name, pts, outs, width, color, mat="flat", lift=0.004):
    """Flat strip lying on a surface (door seams, trims): pts along the path, outs = surface normals."""
    bm = bmesh.new()
    proj, _ = K._uv_layers(bm)
    n = len(pts)
    L, R = [], []
    for i in range(n):
        t = (Vector(pts[min(i + 1, n - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        o = Vector(outs[i]).normalized()
        b = o.cross(t).normalized()
        p = Vector(pts[i]) + o * lift
        L.append(bm.verts.new(p - b * width / 2))
        R.append(bm.verts.new(p + b * width / 2))
    s = 0.0
    for i in range(n - 1):
        f = bm.faces.new((L[i], R[i], R[i + 1], L[i + 1]))
        f.normal_update()
        if f.normal.dot(Vector(outs[i])) < 0:
            f.normal_flip()
        seg = (Vector(pts[i + 1]) - Vector(pts[i])).length
        for loop in f.loops:
            loop[proj].uv = (s + (seg if loop.vert in (L[i + 1], R[i + 1]) else 0.0), 0.0 if loop.vert in L else width)
        s += seg
    K._paint_bm(bm, color, mat)
    for f in bm.faces:
        f.smooth = False
    return mkobj(bm, name)


def quad(name, pts, out, color, mat="flat"):
    """One flat polygon (glass streaks); winding fixed so it faces `out`."""
    bm = bmesh.new()
    proj, _ = K._uv_layers(bm)
    vs = [bm.verts.new(Vector(p)) for p in pts]
    f = bm.faces.new(vs)
    f.normal_update()
    if f.normal.dot(Vector(out)) < 0:
        f.normal_flip()
    uv_box(bm, [f])
    K._paint_bm(bm, color, mat)
    f.smooth = False
    return mkobj(bm, name)


# ------------------------------------------------------------------ outline
def fillet_outline(corners):
    """corners: [(y, z, r, nseg)] of a closed polygon. r = 0 keeps the point. Returns [Vector2]."""
    n = len(corners)
    out = []
    for i in range(n):
        P = V2(*corners[i][:2])
        A = V2(*corners[i - 1][:2])
        B = V2(*corners[(i + 1) % n][:2])
        r, ns = corners[i][2], corners[i][3]
        if r <= 0 or ns <= 0:
            out.append(P)
            continue
        u1, u2 = (A - P).normalized(), (B - P).normalized()
        ang = math.acos(max(-1.0, min(1.0, u1.dot(u2))))
        if ang > math.pi - 0.02:
            out.append(P)
            continue
        t = r / math.tan(ang / 2)
        tmax = 0.6 * min((A - P).length, (B - P).length)
        if t > tmax:
            t = tmax
            r = t * math.tan(ang / 2)
        p1, p2 = P + u1 * t, P + u2 * t
        C = P + (u1 + u2).normalized() * (r / math.sin(ang / 2))
        a1 = math.atan2(p1.y - C.y, p1.x - C.x)
        a2 = math.atan2(p2.y - C.y, p2.x - C.x)
        d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(ns + 1):
            a = a1 + d * k / ns
            out.append(C + V2(math.cos(a), math.sin(a)) * r)
    # drop near-duplicates
    clean_pts = [out[0]]
    for p in out[1:]:
        if (p - clean_pts[-1]).length > 1e-4:
            clean_pts.append(p)
    if (clean_pts[0] - clean_pts[-1]).length < 1e-4:
        clean_pts.pop()
    return clean_pts


def arch_points(ya, zc, R, zb, n, front_to_back=False):
    """Interior points of a wheel-arch arc that meets the sill line z = zb (traversed rear -> front
    by default, i.e. angles increasing over the top)."""
    dy = math.sqrt(max(R * R - (zc - zb) ** 2, 1e-6))
    a0 = math.atan2(zb - zc, dy)
    a1 = math.pi - a0
    pts = []
    for k in range(1, n):
        a = a0 + (a1 - a0) * k / n
        pts.append((ya + math.cos(a) * R, zc + math.sin(a) * R, 0, 0))
    mouth_r = (ya + dy, zb)
    mouth_f = (ya - dy, zb)
    return mouth_r, pts, mouth_f


def profile_corners(spec):
    """spec: dict with keys
       front_bottom, nose_top, cowl, top_pts (list of extra top corners), tail_top, tail_bottom,
       zb, arches [(ya, zc, R, n)], mouth_r
    Returns the corner list, ordered front-bottom -> nose -> top -> tail -> bottom (rear arch, front arch)."""
    c = [spec["front_bottom"], spec["nose_top"]] + spec["top"] + [spec["tail_top"], spec["tail_bottom"]]
    zb = spec["zb"]
    for ya, zc, R, n in sorted(spec["arches"], key=lambda a: -a[0]):
        mr, pts, mf = arch_points(ya, zc, R, zb, n)
        c.append((mr[0], mr[1], spec.get("mouth_r", 0.05), 2))
        c += pts
        c.append((mf[0], mf[1], spec.get("mouth_r", 0.05), 2))
    return c


def outline_normals(pts):
    """Outward normals (2D) of a closed outline, made CCW first. Returns (pts, normals, convex)."""
    area = 0.0
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        area += a.x * b.y - b.x * a.y
    if area < 0:
        pts = list(reversed(pts))
    nrm, convex = [], []
    for i in range(n):
        a, p, b = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1, e2 = (p - a).normalized(), (b - p).normalized()
        n1, n2 = V2(e1.y, -e1.x), V2(e2.y, -e2.x)
        nn = (n1 + n2)
        nrm.append(nn.normalized() if nn.length > 1e-6 else n1)
        convex.append(e1.x * e2.y - e1.y * e2.x > 1e-6)
    return pts, nrm, convex


def circum_r(a, b, c):
    ab, bc, ca = (b - a).length, (c - b).length, (a - c).length
    cr = abs((b - a).x * (c - a).y - (b - a).y * (c - a).x)
    return 1e3 if cr < 1e-9 else ab * bc * ca / (2 * cr)


# ------------------------------------------------------------------ lower body
def lower_body(name, P, hw, color, mat="metal", r_top=0.13, r_front=0.22, r_back=0.2, r_bot=0.03, r_arch=0.035,
               arches=(), zb=0.24, belt=0.9, tumble=0.04, crown=0.03, cowl_y=-0.8, bulge_f=0.05, bulge_b=0.03,
               bed=None, well=WELL, rounding_steps=(90, 62, 32, 0), smooth_iters=3):
    """P: outline [Vector2(y, z)] (from fillet_outline). Lofted across X from -hw to +hw.
    bed: None or dict(y0, y1, floor, wall, floor_color, floor_mat, inner_color) -> recessed pickup bed.
    Returns the object and a dict of per-vertex info."""
    P, N, convex = outline_normals(P)
    n = len(P)
    tags = []
    for i, p in enumerate(P):
        tag = "side"
        for ya, zc, R in arches:
            if abs((p - V2(ya, zc)).length - R) < 0.02 and p.y >= zb - 0.005:
                tag = "arch"
        if tag != "arch" and p.y < zb + 0.004:
            tag = "bottom"
        if bed and bed["y0"] + 0.004 < p.x < bed["y1"] - 0.004 and p.y > belt - 0.06 and N[i].y > 0.5:
            tag = "bed"
        tags.append(tag)
    # per-vertex rounding radius from the outline normal, clamped by local curvature on convex points
    rv = []
    for i in range(n):
        ny, nzz = N[i].x, N[i].y
        if tags[i] == "arch":
            r = r_arch
        else:
            r = r_top * max(nzz, 0) ** 2 + r_bot * max(-nzz, 0) ** 2 + (r_front if ny < 0 else r_back) * ny * ny
        rv.append(r)
    for _ in range(smooth_iters):
        rv = [rv[i] if tags[i] == "arch" else (rv[i - 1] + 2 * rv[i] + rv[(i + 1) % n]) / 4 for i in range(n)]
    for i in range(n):
        if convex[i]:
            rc = circum_r(P[i - 1], P[i], P[(i + 1) % n])
            rv[i] = min(rv[i], 0.92 * rc)
    if bed:
        for i in range(n):
            if tags[i] == "bed" or (abs(P[i].x - bed["y0"]) < 0.03 or abs(P[i].x - bed["y1"]) < 0.03) and P[i].y > belt - 0.06:
                rv[i] = min(rv[i], bed["wall"] - 0.02)

    # rings, left half from the cap inward: (x per vertex, offset per vertex, lowered?)
    half = []
    prev_x = [-hw - 1.0] * n
    for phi in rounding_steps:
        ph = math.radians(phi)
        xs, offs = [], []
        for i in range(n):
            xs.append(-(hw - rv[i] + rv[i] * math.sin(ph)))
            offs.append(rv[i] * (1 - math.cos(ph)))
        half.append((xs, offs, False, "round" if phi > 0 else "edge"))
        prev_x = xs
    if bed:
        x_wall = -(hw - bed["wall"])
        xs = [max(x_wall, px + 0.003) for px in prev_x]
        half.append((xs, [0.0] * n, False, "wall"))
        xs2 = [x + 0.004 for x in xs]
        half.append((xs2, [0.0] * n, True, "low"))
    rings_spec = half + [([0.0] * n, [0.0] * n, bool(bed), "mid")]
    rings_spec += [([-x for x in xs], offs, low, kind) for xs, offs, low, kind in reversed(half)]

    def tumble_k(z):
        return 1.0 - tumble * max(0.0, min(1.0, (belt - z) / max(belt - zb, 0.1)))

    bm = bmesh.new()
    proj, _ = K._uv_layers(bm)
    ymin = min(q.x for q in P)
    ymax = max(q.x for q in P)
    rings = []
    for xs, offs, low, kind in rings_spec:
        ring = []
        for i in range(n):
            p = P[i] - N[i] * offs[i]
            y, z = p.x, p.y
            if low and tags[i] == "bed":
                z = bed["floor"]
            x = xs[i] * tumble_k(z)
            # bonnet crown (cap vertices sit at |x| = hw and are not moved)
            ax = min(1.0, abs(x) / hw)
            if crown and y < cowl_y + 0.1 and z > belt - 0.45:
                z += crown * (1 - ax * ax) * smooth01((z - (belt - 0.45)) / 0.2)
            # plan bulge of nose and tail
            if bulge_f:
                y -= bulge_f * (1 - ax * ax) * smooth01((ymin + 0.35 - y) / 0.35)
            if bulge_b:
                y += bulge_b * (1 - ax * ax) * smooth01((y - (ymax - 0.35)) / 0.35)
            ring.append(bm.verts.new((x, y, z)))
        rings.append((ring, kind, low))
    per = [0.0]
    for i in range(1, n + 1):
        per.append(per[-1] + (P[i % n] - P[i - 1]).length)
    groups = {}
    for k in range(len(rings) - 1):
        ra, ka, la = rings[k]
        rb, kb, lb = rings[k + 1]
        inner = ka in ("edge", "wall", "low", "mid") and kb in ("edge", "wall", "low", "mid")
        for j in range(n):
            j1 = (j + 1) % n
            f = bm.faces.new((ra[j], ra[j1], rb[j1], rb[j]))
            for loop, (jj, kk) in zip(f.loops, [(j, k), (j + 1, k), (j + 1, k + 1), (j, k + 1)]):
                loop[proj].uv = (per[jj], loop.vert.co.x)
            ta, tb = tags[j], tags[j1]
            col, m = color, mat
            if inner and ta in ("arch", "bottom") and tb in ("arch", "bottom"):
                col, m = well, "flat"
            if bed and ta == "bed" and tb == "bed":
                if la and lb:
                    col, m = bed["floor_color"], bed["floor_mat"]
                elif la != lb:
                    col, m = bed.get("inner_color", color), mat
            groups.setdefault((col, m), []).append(f)
            f.smooth = True
    caps = [bm.faces.new(list(reversed(rings[0][0]))), bm.faces.new(rings[-1][0])]
    for f in caps:
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv_box(bm, caps)
    K._paint_bm(bm, color, mat)
    for (c, m), fs in groups.items():
        K._paint_bm(bm, c, m, fs)
    K._paint_bm(bm, color, mat, caps)
    # pickup bed floor faces should be flat-shaded (planks), and the bed walls crisp
    if bed:
        for f in bm.faces:
            f.normal_update()
            if abs(f.normal.z) > 0.98 and f.calc_center_median().z < bed["floor"] + 0.01:
                f.smooth = False
    ob = mkobj(bm, name)
    scale_uv(ob, 0.4)
    info = {"P": P, "N": N, "tags": tags, "rv": rv, "hw": hw, "tumble": tumble_k}
    return ob, info


# ------------------------------------------------------------------ cabin / greenhouse
class Cabin:
    """Rounded-rect rings lofted up Z. Window bands (sill..header) are recessed by `inset` where a
    vertex is glass-tagged; everything else above the sill is the pillar/roof colour.

    keys(z) -> hx, yf, yb, rc: linear (with optional easing on yf) between base and roof edge.
    side_glass / front_glass / back_glass: intervals in [0, 1] along each flat segment."""

    def __init__(self, z_base, z_sill, z_head, z_edge, z_top, base, edge, n_arc=4, side_glass=((0, 1),),
                 front_glass=((0, 1),), back_glass=((0, 1),), inset=0.025, reveal=0.035, bulge_f=0.05,
                 bulge_b=0.02, ease_f=1.0, body="house_mint", roof="cream", frame=CHROME, roof_mat="metal",
                 body_mat="metal", roof_steps=(30, 60, 90), pillar=None, pillar_mat=None):
        self.__dict__.update(locals())
        del self.__dict__["self"]
        if self.pillar is None:
            self.pillar = self.body
        if self.pillar_mat is None:
            self.pillar_mat = self.body_mat

    def keys(self, z):
        t = (z - self.z_base) / (self.z_edge - self.z_base)
        t = max(0.0, min(1.0, t))
        b, e = self.base, self.edge
        tf = t ** self.ease_f
        return (b[0] + (e[0] - b[0]) * t, b[1] + (e[1] - b[1]) * tf, b[2] + (e[2] - b[2]) * t,
                b[3] + (e[3] - b[3]) * t)

    def _params(self, intervals, length):
        e = min(self.reveal / max(length, 0.1), 0.2)
        ts = {0.0: False, 1.0: False}
        for a, b in intervals:
            ts[a] = ts.get(a, False)
            ts[b] = ts.get(b, False)
            ts[a + e] = True
            ts[b - e] = True
            # extra glass points inside long windows so curvature can be shown
            if b - a > 0.5:
                ts[(a + b) / 2] = True
        out = sorted(ts.items())
        return out

    def layout(self):
        """Fixed per-vertex layout: list of (segment, param, glass)."""
        hx, yf, yb, rc = self.keys(self.z_sill)
        side_len = (yb - rc) - (yf + rc)
        fb_len = 2 * (hx - rc)
        lay = []
        side = self._params(self.side_glass, side_len)
        front = self._params(self.front_glass, fb_len)
        back = self._params(self.back_glass, fb_len)
        for t, g in side:  # right side, front -> back
            lay.append(("R", t, g))
        for k in range(1, self.n_arc):
            lay.append(("BR", k / self.n_arc, False))
        for t, g in back:  # back, right -> left
            lay.append(("B", t, g))
        for k in range(1, self.n_arc):
            lay.append(("BL", k / self.n_arc, False))
        for t, g in reversed(side):  # left side, back -> front
            lay.append(("L", t, g))
        for k in range(1, self.n_arc):
            lay.append(("FL", k / self.n_arc, False))
        for t, g in front:  # front, left -> right
            lay.append(("F", t, g))
        for k in range(1, self.n_arc):
            lay.append(("FR", k / self.n_arc, False))
        return lay

    def point(self, seg, t, z, inset=0.0, off=0.0):
        """Point on the ring at height z. inset pushes along -normal, off shrinks the whole rect."""
        hx, yf, yb, rc = self.keys(z)
        hx -= off
        yf += off
        yb -= off
        rc = max(rc - off * 0.7, 0.03)
        if seg == "R":
            p, n = Vector((hx, (yf + rc) + ((yb - rc) - (yf + rc)) * t, z)), Vector((1, 0, 0))
        elif seg == "L":
            p, n = Vector((-hx, (yf + rc) + ((yb - rc) - (yf + rc)) * t, z)), Vector((-1, 0, 0))
        elif seg == "B":
            x = (hx - rc) - 2 * (hx - rc) * t
            ax = x / max(hx - rc, 1e-3)
            p, n = Vector((x, yb + self.bulge_b * (1 - ax * ax), z)), Vector((0, 1, 0))
        elif seg == "F":
            x = -(hx - rc) + 2 * (hx - rc) * t
            ax = x / max(hx - rc, 1e-3)
            p, n = Vector((x, yf - self.bulge_f * (1 - ax * ax), z)), Vector((0, -1, 0))
        else:
            c = {"BR": (hx - rc, yb - rc, 0.0), "BL": (-(hx - rc), yb - rc, 90.0),
                 "FL": (-(hx - rc), yf + rc, 180.0), "FR": (hx - rc, yf + rc, 270.0)}[seg]
            a = math.radians(c[2] + 90.0 * t)
            n = Vector((math.cos(a), math.sin(a), 0))
            p = Vector((c[0], c[1], z)) + n * rc
        return p - n * inset, n

    def build(self, name):
        lay = self.layout()
        m = len(lay)
        eps = 0.006
        levels = [("base", self.z_base, 0.0, False), ("sill", self.z_sill, 0.0, False),
                  ("sill_in", self.z_sill + eps, 0.0, True), ("head_in", self.z_head - eps, 0.0, True),
                  ("head", self.z_head, 0.0, False), ("edge", self.z_edge, 0.0, False)]
        rr = self.z_top - self.z_edge
        for phi in self.roof_steps:
            ph = math.radians(phi)
            levels.append((f"roof{phi}", self.z_edge + rr * math.sin(ph), rr * (1 - math.cos(ph)) * 1.15, False))
        bm = bmesh.new()
        proj, _ = K._uv_layers(bm)
        rings = []
        for lname, z, off, rec in levels:
            ring = []
            for seg, t, g in lay:
                p, _ = self.point(seg, t, z, inset=self.inset if (rec and g) else 0.0, off=off)
                ring.append(bm.verts.new(p))
            rings.append(ring)
        groups = {}
        for k in range(len(levels) - 1):
            la, lb = levels[k][0], levels[k + 1][0]
            for j in range(m):
                j1 = (j + 1) % m
                f = bm.faces.new((rings[k][j], rings[k][j1], rings[k + 1][j1], rings[k + 1][j]))
                ga, gb = lay[j][2], lay[j1][2]
                if la == "base":
                    cm = (self.body, self.body_mat)
                elif la in ("sill", "head_in"):
                    cm = (self.frame, "metal") if (ga or gb) else (self.pillar, self.pillar_mat)
                elif la == "sill_in":
                    if ga and gb:
                        cm = (GLASS, "flat")
                    elif ga or gb:
                        cm = (self.frame, "metal")
                    else:
                        cm = (self.pillar, self.pillar_mat)
                elif la == "head":
                    cm = (self.pillar, self.pillar_mat)
                else:
                    cm = (self.roof, self.roof_mat)
                groups.setdefault(cm, []).append(f)
                f.smooth = not (cm[0] == GLASS)
        top = bm.faces.new(rings[-1])
        top.smooth = False
        groups.setdefault((self.roof, self.roof_mat), []).append(top)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        uv_box(bm, bm.faces)
        for (c, mm), fs in groups.items():
            K._paint_bm(bm, c, mm, fs)
        return scale_uv(mkobj(bm, name), 0.4)

    def streaks(self, name, seg, specs, color=STREAK):
        """Diagonal highlight strips on a window: specs [(t_low, t_high, width_t, zlo_frac, zhi_frac)]."""
        parts = []
        zs, zh = self.z_sill + 0.03, self.z_head - 0.03
        for i, (t0, t1, w, f0, f1) in enumerate(specs):
            za = zs + (zh - zs) * f0
            zb = zs + (zh - zs) * f1
            pts = []
            for t, z in ((t0, za), (t0 + w, za), (t1 + w, zb), (t1, zb)):
                p, nrm = self.point(seg, t, z, inset=self.inset - 0.004)
                pts.append(p)
            parts.append(quad(f"{name}{i}", pts, nrm, color))
        return parts


# ------------------------------------------------------------------ wheels
def wheel(name, x, y, r=0.33, w=0.26, rim="cream", cap=CHROME, button="metal_red", white="lolly_white", segs=14):
    """Chunky tyre (axis along X, outer face toward +-x) + whitewall/rim/hubcap disc. The inner
    sidewall is never seen, so the profile starts at the inner shoulder."""
    sx = 1 if x > 0 else -1
    parts = []
    prof = [(r - 0.03, -w / 2), (r, -w / 2 + 0.05), (r, w / 2 - 0.075), (r - 0.012, w / 2 - 0.03),
            (r - 0.05, w / 2), (0.2, w / 2)]
    tyre = lathe(f"{name}_t", prof, "charcoal", "flat", segments=segs, cap_bottom=False, cap_top=True,
                 cap_colors=("charcoal", "charcoal"), phase=math.pi / segs)
    transform(tyre, loc=(x, y, r), rot=(0, 90 * sx, 0))
    parts.append(tyre)
    hub = lathe(f"{name}_h", [(r - 0.075, 0.0), (r - 0.095, 0.01), (0.15, 0.022), (0.095, 0.05), (0.035, 0.062),
                              (0.0, 0.066)],
                [white, rim, cap, cap, button], ["flat", "metal", "metal", "metal", "metal"],
                segments=segs, cap_bottom=False, phase=math.pi / segs)
    transform(hub, loc=(x + sx * (w / 2 - 0.006), y, r), rot=(0, 90 * sx, 0))
    parts.append(hub)
    return parts


# ------------------------------------------------------------------ lamps, grille, plates
def lamp(name, loc, direction, r, lens="lolly_white", ring=CHROME, pod=None, pod_len=0.0, segs=12, dome=0.03,
         lens_mat="flat"):
    """Round lamp facing `direction`: optional body-coloured pod, chrome bezel, domed lens."""
    prof, cols, mats = [], [], []
    if pod:
        prof += [(r * 1.02, -pod_len), (r * 1.08, -0.005)]
        cols += [pod]
        mats += [PAINT_MAT]
    else:
        prof += [(r * 1.12, -0.02)]
    prof += [(r * 1.12, 0.012), (r * 0.98, 0.026), (r * 0.55, 0.026 + dome * 0.75), (0.0, 0.026 + dome)]
    cols += [ring, ring, lens, lens]
    mats += ["metal", "metal", lens_mat, lens_mat]
    ob = lathe(name, prof, cols, mats, segments=segs, cap_bottom=False)
    return orient(ob, loc, direction)


def plate(name, loc, facing, text=None, w=0.36, h=0.12, color="candy_corn_white", ink="witch_purple"):
    """Number plate facing -Y (facing=-1) or +Y (facing=+1). text 'BOO' draws chunky letters."""
    parts = [box(f"{name}_p", (w, 0.025, h), color, "flat"),
             box(f"{name}_r", (w + 0.02, 0.015, h + 0.02), "iron", "metal", loc=(0, 0.006, 0))]
    lt = 0.012  # letters raised in front of the plate face
    fy = -0.0125 - 0.004
    if text == "BOO":
        hgt = 0.075
        bx = -0.095
        parts.append(box(f"{name}_b0", (0.016, 0.01, hgt), ink, "flat", loc=(bx, fy, 0)))
        for k, zc in enumerate((hgt / 4, -hgt / 4)):
            # torus arc = upper half in XY; Rx(90) stands it up in XZ, Ry(90) turns it into the right half
            arcp = K.torus(f"{name}_b{k + 1}", hgt / 4, 0.008, color=ink, major_seg=5, minor_seg=3, arc=180.0)
            transform(arcp, loc=(bx, fy, zc), rot=(90, 90, 0), scale=(1.0, 1.25, 1.0))
            parts.append(arcp)
        for k, xc in enumerate((0.0, 0.085)):
            o = K.torus(f"{name}_o{k}", 0.028, 0.0085, color=ink, major_seg=7, minor_seg=3)
            transform(o, loc=(xc, fy, 0), rot=(90, 0, 0), scale=(0.8, 1.33, 1.0))
            parts.append(o)
    elif text == "dash":
        for k, xc in enumerate((-0.1, -0.035, 0.035, 0.1)):
            parts.append(box(f"{name}_d{k}", (0.04, 0.008, 0.018 if k in (1, 2) else 0.05), ink, "flat",
                             loc=(xc, fy, 0)))
    ob = K.merge(parts, name)
    transform(ob, loc=loc, rot=(0, 0, 0 if facing < 0 else 180))
    return ob


def jack(name, loc, r, face_dir=(0, -1, 0), color="pumpkin", glow="glow_jack_face", ribs=8, sides=12, rings=5,
         stem_lean=(0.02, 0.01), carved=True):
    """Pumpkin (ribbed) with an optional carved glowing face pointing along face_dir (horizontal)."""
    x, y, z = loc
    parts = [ribbed(f"{name}_b", r, r * 1.3, color, ribs=ribs, depth=0.06, rings=rings, sides=sides, loc=(x, y, z))]
    parts.append(rod(f"{name}_st", (x, y, z + r * 1.2), (x + stem_lean[0], y + stem_lean[1], z + r * 1.55),
                     max(0.012, r * 0.13), "stem_green", mat="wood", sides=6))
    if carved:
        face = []
        for sx in (-1, 1):
            eye = K.polygon_prism(f"{name}_e{sx}", [(-0.2 * r, -0.14 * r), (0.2 * r, -0.14 * r), (0.0, 0.2 * r)],
                                  0.1 * r, color=glow)
            transform(eye, loc=(sx * 0.36 * r, 0, 0.2 * r), rot=(90, 0, 0))
            face.append(eye)
        mouth = stroke(f"{name}_m", [(-0.46 * r, 0.0, 0), (-0.2 * r, -0.18 * r, 0), (0.2 * r, -0.18 * r, 0),
                                     (0.46 * r, 0.0, 0)], 0.2 * r, glow, thick=0.1 * r, taper=(0.5, 0.5), sides=4, z=0)
        transform(mouth, loc=(0, 0, -0.2 * r), rot=(90, 0, 0))
        face.append(mouth)
        fo = K.merge(face, f"{name}_face")
        d = Vector(face_dir).normalized()
        yaw = math.degrees(math.atan2(d.x, -d.y))
        # face sits on the pumpkin front at mid height
        c = Vector((x, y, z + r * 0.62)) + d * (r * 0.97)
        transform(fo, loc=tuple(c), rot=(0, 0, yaw))
        parts.append(fo)
    return parts


def hay_bale(name, loc, size, rot_z=0.0, twine="rope"):
    x, y, z = loc
    sx, sy, sz = size
    parts = [box(f"{name}_b", size, "hay", "straw", loc=(x, y, z + sz / 2), rot=(0, 0, rot_z), bevel=0.045, segments=1)]
    for k, off in enumerate((-sx * 0.25, sx * 0.25)):
        band = box(f"{name}_t{k}", (0.03, sy + 0.012, sz + 0.012), "straw_dark", "flat",
                   loc=(x + off * math.cos(math.radians(rot_z)), y + off * math.sin(math.radians(rot_z)), z + sz / 2),
                   rot=(0, 0, rot_z))
        parts.append(band)
    return parts


def finish_car(parts, asset_id, ao_radius=0.6, ao_lift=None):
    """Merge, ground, clean, bake AO, export, sheet. ao_lift(co) -> 0..1 lifts the AO toward white for
    vertices in deep pockets that would otherwise bake near-black (pickup bed)."""
    from yard_common import clean
    car = K.merge(parts, asset_id)
    ground(car)
    clean(car)
    K.bake_ao([car], samples=32, radius=ao_radius, strength=0.9, ground=True)
    if ao_lift:
        attr = car.data.color_attributes.get("AO")
        for v in car.data.vertices:
            k = ao_lift(v.co)
            if k > 0:
                a = attr.data[v.index].color[0]
                a = a + (1.0 - a) * k
                attr.data[v.index].color = (a, a, a, 1.0)
    K.export([car], f"props/{asset_id}")
    tris = K.tri_count([car])
    sh = K.review_sheet([car], asset_id)
    print(f"ASSET {asset_id} tris={tris} gltf=props/{asset_id} sheet={sh}")
    lo = [min(v.co[i] for v in car.data.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in car.data.vertices) for i in range(3)]
    print(f"BOUNDS {asset_id} x {lo[0]:.3f}..{hi[0]:.3f} y {lo[1]:.3f}..{hi[1]:.3f} z {lo[2]:.3f}..{hi[2]:.3f}")
    return tris
