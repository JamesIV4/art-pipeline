# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/avgeo.py (imported 2026-10-25)
# Changed: header only (pure-Python geometry kernel, no paths)
"""AVENGER v2 geometry kernel (pure Python; also imported inside Blender).

Everything is built in CRAFT coordinates (Blender frame: X = 2*map_x east, Y = -2*map_y north,
Z = level*sqrt6 up) as unions of CONVEX solids. A record's model is its pieces clipped to its tile
box (convex clipping + cap faces), then translated to the tile-local origin. Caps produced by tile
cuts get the 'section' material (the sprites' flat lilac cutaway colour).

Face = polygon (convex, CCW seen from outside) + material + uv mode
  uv mode 'world'       : planar projection in craft coordinates (seamless across tile cuts)
  uv mode ('rect', r, b): planar coords mapped from bounds b=(t0,t1,s0,s1) into atlas rect r=(u0,v0,u1,v1)
  uv mode 'pre'         : per-vertex uvs supplied (cylinders/lathes), interpolated by clipping
Per-vertex normals (smooth pieces) are optional and interpolated by clipping.
"""
import math

EPS = 1e-6
H = math.sqrt(6.0)


def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))


def unit(a):
    l = length(a)
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-12 else (0.0, 0.0, 1.0)


def lerp(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def poly_normal(pts):
    n = (0.0, 0.0, 0.0)
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n = add(n, ((a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])))
    return n


def plane_frame(n):
    """Tangent t (right, seen from outside) and bitangent b (up / up-slope) for a face normal n."""
    n = unit(n)
    if abs(n[0]) < 1e-4 and abs(n[1]) < 1e-4:
        return ((1.0, 0.0, 0.0), (0.0, 1.0 if n[2] > 0 else -1.0, 0.0))
    t = unit(cross((0.0, 0.0, 1.0), n))
    b = cross(n, t)
    return t, b


class Face:
    __slots__ = ("pts", "mat", "uv", "nrm", "uvs", "tag")

    def __init__(self, pts, mat, uv="world", nrm=None, uvs=None, tag=""):
        self.pts, self.mat, self.uv, self.nrm, self.uvs, self.tag = list(pts), mat, uv, nrm, uvs, tag

    def normal(self):
        return unit(poly_normal(self.pts))


class Solid:
    def __init__(self, faces, name=""):
        self.faces, self.name = faces, name

    def translated(self, d):
        fs = [Face([add(p, d) for p in f.pts], f.mat, f.uv, f.nrm, f.uvs, f.tag) for f in self.faces]
        return Solid(fs, self.name)


# ---------------------------------------------------------------- clipping
def clip_solid(solid, n, d, cap_mat="section", cap_tag="cap"):
    """Keep the part with dot(n,p) <= d. Returns None when nothing remains. Solids must be convex."""
    s_all = [dot(n, p) - d for f in solid.faces for p in f.pts]
    if min(s_all) >= -EPS:
        return None
    if max(s_all) <= EPS:
        return solid
    out, on_plane = [], []
    for f in solid.faces:
        k = len(f.pts)
        sv = [dot(n, p) - d for p in f.pts]
        P, N, U = [], [], []
        for i in range(k):
            j = (i + 1) % k
            a, b, sa, sb = f.pts[i], f.pts[j], sv[i], sv[j]
            if sa <= EPS:
                P.append(a); N.append(f.nrm[i] if f.nrm else None); U.append(f.uvs[i] if f.uvs else None)
                if abs(sa) <= EPS:
                    on_plane.append(a)
            if (sa < -EPS and sb > EPS) or (sa > EPS and sb < -EPS):
                t = sa / (sa - sb)
                q = lerp(a, b, t)
                P.append(q); on_plane.append(q)
                N.append(unit(lerp(f.nrm[i], f.nrm[j], t)) if f.nrm else None)
                U.append(lerp(f.uvs[i], f.uvs[j], t) if f.uvs else None)
        if len(P) >= 3:
            out.append(Face(P, f.mat, f.uv, N if f.nrm else None, U if f.uvs else None, f.tag))
    # cap polygon from the on-plane points
    pts = dedupe(on_plane)
    if len(pts) >= 3:
        c = mul(pts[0], 0.0)
        for p in pts:
            c = add(c, p)
        c = mul(c, 1.0 / len(pts))
        t, b = plane_frame(n)
        pts.sort(key=lambda p: math.atan2(dot(sub(p, c), b), dot(sub(p, c), t)))
        if dot(poly_normal(pts), n) < 0:
            pts.reverse()
        out.append(Face(pts, cap_mat, "world", tag=cap_tag))
    if not out:
        return None
    res = Solid(out, solid.name)
    if hasattr(solid, "cap_mat"):
        res.cap_mat = solid.cap_mat
    return res


def dedupe(pts, tol=1e-5):
    res = []
    for p in pts:
        if all(length(sub(p, q)) > tol for q in res):
            res.append(p)
    return res


def clip_box(solid, x0, x1, y0, y1, z0=None, z1=None, cap_mat="section"):
    planes = [((1, 0, 0), x1), ((-1, 0, 0), -x0), ((0, 1, 0), y1), ((0, -1, 0), -y0)]
    if z1 is not None:
        planes.append(((0, 0, 1), z1))
    if z0 is not None:
        planes.append(((0, 0, -1), -z0))
    cap_mat = getattr(solid, "cap_mat", cap_mat)
    for n, d in planes:
        if solid is None:
            return None
        solid = clip_solid(solid, n, d, cap_mat)
    return solid


def clip_halfplanes(solid, planes, cap_mat="section"):
    for n, d in planes:
        if solid is None:
            return None
        solid = clip_solid(solid, n, d, cap_mat)
    return solid


# ---------------------------------------------------------------- 2D polygon helpers
def poly2_area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def ccw(poly):
    return poly if poly2_area(poly) > 0 else list(reversed(poly))


def clip_poly2(poly, a, b, c):
    """Keep a*x + b*y <= c."""
    out = []
    k = len(poly)
    for i in range(k):
        p, q = poly[i], poly[(i + 1) % k]
        sp, sq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if sp <= EPS:
            out.append(p)
        if (sp < -EPS and sq > EPS) or (sp > EPS and sq < -EPS):
            t = sp / (sp - sq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def inset2(poly, d):
    """Inset a convex CCW polygon by distance d (edges move inward)."""
    poly = ccw(poly)
    k = len(poly)
    lines = []
    for i in range(k):
        p, q = poly[i], poly[(i + 1) % k]
        ex, ey = q[0] - p[0], q[1] - p[1]
        L = math.hypot(ex, ey)
        nx, ny = -ey / L, ex / L          # inward normal for CCW
        lines.append(((p[0] + nx * d, p[1] + ny * d), (ex / L, ey / L)))
    out = []
    for i in range(k):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


# ---------------------------------------------------------------- constructors
def _face(pts, mat, uv="world", tag=""):
    return Face(pts, mat, uv, tag=tag)


def prism(poly, z0, ztop, mat, top_mat=None, bot_mat=None, side_mats=None, top_uv="world", side_uv="world", name=""):
    """Vertical prism over a convex 2D polygon. ztop: number or function (x, y) -> z (planar)."""
    poly = ccw(poly)
    zt = ztop if callable(ztop) else (lambda x, y, v=ztop: v)
    top = [(x, y, zt(x, y)) for x, y in poly]
    bot = [(x, y, z0) for x, y in poly]
    faces = [_face(top, top_mat or mat, top_uv, "top"), _face(list(reversed(bot)), bot_mat or mat, "world", "bottom")]
    k = len(poly)
    for i in range(k):
        j = (i + 1) % k
        m = side_mats[i] if side_mats else mat
        if m is None:
            continue
        faces.append(_face([bot[i], bot[j], top[j], top[i]], m, side_uv, "side"))
    return Solid(faces, name)


def box(x0, x1, y0, y1, z0, z1, mat, mats=None, name="", uvs=None):
    """Axis-aligned box; mats overrides per side: xn xp yn yp zn zp; uvs: per-side uv modes."""
    m = lambda k: (mats or {}).get(k, mat)
    u = lambda k: (uvs or {}).get(k, "world")
    P = lambda x, y, z: (x, y, z)
    f = [
        _face([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], m("zp"), u("zp"), "top"),
        _face([P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0), P(x0, y0, z0)], m("zn"), u("zn"), "bottom"),
        _face([P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)], m("yn"), u("yn"), "yn"),
        _face([P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1)], m("yp"), u("yp"), "yp"),
        _face([P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1)], m("xn"), u("xn"), "xn"),
        _face([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], m("xp"), u("xp"), "xp"),
    ]
    return Solid([x for x in f if x.mat is not None], name)


def extrude(poly, origin, U, V, W, w0, w1, mat, cap0_mat=None, cap1_mat=None, side_mats=None, name="", uv="world",
            cap_uv="world"):
    """Convex 2D polygon in the (U, V) plane at origin, extruded along W from w0 to w1. U, V, W orthonormal, right-handed or not."""
    poly = ccw(poly)
    P = lambda u, v, w: add(origin, add(mul(U, u), add(mul(V, v), mul(W, w))))
    a = [P(u, v, w0) for u, v in poly]
    b = [P(u, v, w1) for u, v in poly]
    faces = []
    k = len(poly)
    for i in range(k):
        j = (i + 1) % k
        m = side_mats[i] if side_mats else mat
        if m is not None:
            faces.append(_face([a[i], a[j], b[j], b[i]], m, uv, "side"))
    faces.append(_face(list(reversed(a)), cap0_mat or mat, cap_uv, "cap0"))
    faces.append(_face(b, cap1_mat or mat, cap_uv, "cap1"))
    # orientation fix: make every face point away from the centroid
    c = mul(add(_centroid(a), _centroid(b)), 0.5)
    for f in faces:
        if dot(poly_normal(f.pts), sub(_centroid(f.pts), c)) < 0:
            f.pts.reverse()
    return Solid(faces, name)


def _centroid(pts):
    c = (0.0, 0.0, 0.0)
    for p in pts:
        c = add(c, p)
    return mul(c, 1.0 / len(pts))


def lathe(profile, center, axis, n, mat, cap_mats=None, name="", su=1.0, sv=1.0, seg_start=0.0, smooth=True):
    """Convex solid of revolution. profile: [(l, r), ...] along the axis with l increasing, r >= 0 (convex).
    Smooth vertex normals and per-vertex 'pre' uvs (u = arc length / su, v = l / sv)."""
    axis = unit(axis)
    ref = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    e1 = unit(cross(axis, ref))
    e2 = cross(axis, e1)
    angs = [seg_start + 2 * math.pi * i / n for i in range(n + 1)]
    rings = []
    for l, r in profile:
        rings.append([add(center, add(mul(axis, l), add(mul(e1, r * math.cos(a)), mul(e2, r * math.sin(a))))) for a in angs])
    # profile normals (2D) at each profile vertex, averaged from adjacent segments
    pn = []
    for i in range(len(profile)):
        acc = [0.0, 0.0]
        for j in (i - 1, i):
            if 0 <= j < len(profile) - 1:
                (l0, r0), (l1, r1) = profile[j], profile[j + 1]
                dl, dr = l1 - l0, r1 - r0
                L = math.hypot(dl, dr)
                if L > 1e-9:
                    acc[0] += dr / L * -1.0
                    acc[1] += dl / L
        L = math.hypot(*acc) or 1.0
        pn.append((acc[0] / L, acc[1] / L))      # (axial, radial)
    faces = []
    rmax = max(r for _, r in profile)
    for i in range(len(profile) - 1):
        for k in range(n):
            q = [rings[i][k], rings[i][k + 1], rings[i + 1][k + 1], rings[i + 1][k]]
            idx = [(i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)]
            if length(sub(q[0], q[1])) < 1e-9 and length(sub(q[2], q[3])) < 1e-9:
                continue
            keep = [m for m in range(4) if all(length(sub(q[m], q[o])) > 1e-9 for o in range(m))]
            q = [q[m] for m in keep]; idx = [idx[m] for m in keep]
            if len(q) < 3:
                continue
            nr = []
            uv = []
            for (ri, ai) in idx:
                a = angs[ai]
                ax_, rad = pn[ri]
                radial = add(mul(e1, math.cos(a)), mul(e2, math.sin(a)))
                nr.append(unit(add(mul(axis, ax_), mul(radial, rad))) if smooth else None)
                uv.append(((a - seg_start) * rmax / su, profile[ri][0] / sv))
            f = Face(q, mat, "pre", nr if smooth else None, uv, "lathe")
            # orientation: outward
            if dot(poly_normal(f.pts), sub(_centroid(f.pts), add(center, mul(axis, profile[min(i + 1, len(profile) - 1)][0] * 0.5 + profile[i][0] * 0.5)))) < 0:
                f.pts.reverse(); f.uvs.reverse()
                if f.nrm:
                    f.nrm.reverse()
            if not smooth:
                f.nrm = None
            faces.append(f)
    # end caps
    for end, ring in ((0, rings[0]), (len(profile) - 1, rings[-1])):
        if profile[end][1] > 1e-9:
            pts = ring[:-1]
            if end == 0:
                pts = list(reversed(pts))
            cm = (cap_mats or {}).get(end if end == 0 else "end", mat)
            f = Face(pts, cm, "world", tag="lathecap")
            outward = mul(axis, -1.0 if end == 0 else 1.0)
            if dot(poly_normal(f.pts), outward) < 0:
                f.pts.reverse()
            faces.append(f)
    return Solid(faces, name)


def flat_face_uv(face_pts, mat_scale):
    pass


def bounds_tb(pts, n=None):
    n = n or unit(poly_normal(pts))
    t, b = plane_frame(n)
    ts = [dot(p, t) for p in pts]
    bs = [dot(p, b) for p in pts]
    return (min(ts), max(ts), min(bs), max(bs))


def decal(solid, tag, rect, pad=0.0):
    """Map the face(s) of `solid` with the given tag into atlas rect (u0, v0, u1, v1) using their planar bounds."""
    for f in solid.faces:
        if f.tag == tag:
            t0, t1, b0, b1 = bounds_tb(f.pts)
            f.uv = ("rect", rect, (t0 - pad, t1 + pad, b0 - pad, b1 + pad))
    return solid


def swatch(solid, rect, tags=None):
    """Map faces into a solid colour atlas cell (inset), each by its own bounds."""
    u0, v0, u1, v1 = rect
    du, dv = (u1 - u0) * 0.2, (v1 - v0) * 0.2
    inner = (u0 + du, v0 + dv, u1 - du, v1 - dv)
    for f in solid.faces:
        if tags is None or f.tag in tags:
            f.uv = ("swatch", inner)
    return solid


def set_mat(solid, mat, tags=None):
    for f in solid.faces:
        if tags is None or f.tag in tags:
            f.mat = mat
    return solid
