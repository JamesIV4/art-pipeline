# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/master.py (imported 2026-10-25)
# Changed: header only
"""AVENGER v2b master: the complete craft (hull, sides, nose, canopy, fins, cockpit, nacelles, pylons,
landing gear, ramp, hold interior) in craft coordinates, built from convex solids.

Every record has a builder that returns its world-space solids at its canonical tile; records repeated in
the map are translation-invariant by construction, so the assembled craft (canonical models placed at all
MAP positions) is exactly what the game shows. master_render.py renders it whole; blender_build.py cuts and
exports. Craft frame: X = 2*map_x (east), Y = -2*map_y (north), Z = level*sqrt6.
"""
import math

from avgeo import (H, Solid, Face, box, prism, extrude, lathe, clip_poly2, clip_solid, clip_box, ccw, unit, dot, sub, add,
                   mul, cross, plane_frame, bounds_tb, poly_normal)
import meshdata as MD
import craft as C

Z0, Z1, Z2 = 0.0, H, 2 * H
WT = H - 0.005                 # wall top (5 mm under the level line)
BELLY = -0.30                  # hull belly / deck slab underside (level-local)
TW = 0.75                      # hull wall thickness (P034/P046: 6 px cut faces)
U_IN = 0.03                    # interior face set 3 cm into the wall tile (room for interior relief)
SQ2 = math.sqrt(2.0)

# hull wall cross-section (u outward from the tile-edge line, z level-local), CCW
WALL_PROF = [(U_IN, BELLY), (0.36, BELLY), (TW, 0.12), (TW, WT - 0.48), (0.22, WT), (U_IN, WT)]
WALL_MATS = ["hulldark", "greeble", "greeble", "greeble", "hull", "interior"]

# nose / canopy
NOSE_Y = -37.75
NOSE_TOP = 16 * H / 24         # 1.633 (LOFT layers 0-7)
BAND_Z = (0.24, 0.68)
SLOPE_K = (WT - NOSE_TOP) / 2.0  # windscreen slope dz/dY over y18


def canopy_z(y):
    return NOSE_TOP + (y + 37.0) * SLOPE_K


# ------------------------------------------------------------------ small helpers
def keep(s):
    for f in s.faces:
        f.tag = "keep"
    return s


def mats(s, m):
    for f in s.faces:
        f.mat = m
    return s


def frustum(c, A, B, N, a0, a1, b0, b1, depth, bevel, mat, side_mat=None, base=False):
    """Bevelled raised plate: base rectangle (a0..a1, b0..b1) in plane (c; A, B), top rectangle inset by
    `bevel` at height `depth` along N. Convex. Base face omitted unless base=True."""
    P = lambda a, b, h: add(c, add(mul(A, a), add(mul(B, b), mul(N, h))))
    bs = [P(a0, b0, 0), P(a1, b0, 0), P(a1, b1, 0), P(a0, b1, 0)]
    tp = [P(a0 + bevel, b0 + bevel, depth), P(a1 - bevel, b0 + bevel, depth), P(a1 - bevel, b1 - bevel, depth),
          P(a0 + bevel, b1 - bevel, depth)]
    faces = [Face(tp, mat, tag="top")]
    if base:
        faces.append(Face(list(reversed(bs)), side_mat or mat, tag="base"))
    for i in range(4):
        j = (i + 1) % 4
        faces.append(Face([bs[i], bs[j], tp[j], tp[i]], side_mat or mat, tag="side"))
    cen = mul(add(_cen(bs), _cen(tp)), 0.5)
    cen = sub(cen, mul(N, depth * 0.5 + 0.001))
    for f in faces:
        if dot(poly_normal(f.pts), sub(_cen(f.pts), cen)) < 0:
            f.pts.reverse()
    return Solid(faces, "plate")


def _cen(pts):
    c = (0.0, 0.0, 0.0)
    for p in pts:
        c = add(c, p)
    return mul(c, 1.0 / len(pts))


def obox(c, A, B, N, a0, a1, b0, b1, n0, n1, mat, name="obox"):
    """Oriented box in the frame (c; A, B, N)."""
    return extrude([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], c, A, B, N, n0, n1, mat, name=name)


class WallFrame:
    """Wall frame: inner tile-edge line through a (2D) with along-direction d, outward normal o; level base z."""

    def __init__(self, a, d, o, zb=Z1):
        self.a, self.d, self.o, self.zb = (a[0], a[1], zb), (d[0], d[1], 0.0), (o[0], o[1], 0.0), zb

    def P(self, u, z, s):
        return add(self.a, add(mul(self.o, u), add(mul(self.d, s), (0.0, 0.0, z))))


def wall_body(F, s0=-3.0, s1=3.0, prof=None, mats_=None):
    return extrude(prof or WALL_PROF, F.a, F.o, (0, 0, 1), F.d, s0, s1, "hull", side_mats=mats_ or WALL_MATS, name="hull wall")


def ext_plate(F, s0, s1, z0, z1, mat="greeble", depth=0.04, bevel=0.025):
    return frustum(F.P(TW, 0, 0), F.d, (0, 0, 1), F.o, s0, s1, z0, z1, depth, bevel, mat, side_mat="hull")


def int_plate(F, s0, s1, z0, z1, mat, depth=0.025, bevel=0.012):
    neg = mul(F.o, -1.0)
    return frustum(F.P(U_IN, 0, 0), F.d, (0, 0, 1), neg, s0, s1, z0, z1, depth, bevel, mat, side_mat="taupe")


def vent(F, s0, s1, z0, z1, n=5):
    """Exterior vent: dark recessed-looking frame with horizontal slats."""
    out = [frustum(F.P(TW, 0, 0), F.d, (0, 0, 1), F.o, s0, s1, z0, z1, 0.03, 0.02, "dark", side_mat="hull")]
    h = (z1 - z0 - 0.08) / n
    for k in range(n):
        zz = z0 + 0.04 + k * h
        out.append(obox(F.P(TW, 0, 0), F.d, (0, 0, 1), F.o, s0 + 0.05, s1 - 0.05, zz + h * 0.25, zz + h * 0.62, 0.02, 0.05,
                        "hull", name="vent slat"))
    return out


def ext_detail(F, layout, smid=0.0, half=0.96):
    """Exterior: the sprite shows only the big maze (texture, mapped round the profile) and the light band under the
    shoulder; no extra plates (user 2026-10-03: match the sprite's detail density)."""
    return [obox(F.P(TW, 0, 0), F.d, (0, 0, 1), F.o, -3, 3, WT - 0.52, WT - 0.47, -0.01, 0.035, "hull", name="shoulder rail")]


PROFILE_CHAIN = [(0.36, BELLY), (TW, 0.12), (TW, WT - 0.48), (0.22, WT)]


def _chain_param(u, z):
    """Arc length along the outer profile chain of the nearest point to (u, z)."""
    best, acc, res = 1e9, 0.0, 0.0
    for (u0, z0), (u1, z1) in zip(PROFILE_CHAIN[:-1], PROFILE_CHAIN[1:]):
        du, dz = u1 - u0, z1 - z0
        L2 = du * du + dz * dz
        t = max(0.0, min(1.0, ((u - u0) * du + (z - z0) * dz) / L2))
        pu, pz = u0 + du * t, z0 + dz * t
        dd = (pu - u) ** 2 + (pz - z) ** 2
        if dd < best:
            best, res = dd, acc + t * math.sqrt(L2)
        acc += math.sqrt(L2)
    return res


def profile_uv(solids, F, su=2.0, sv=2.0):
    """Greeble faces of a hull wall get UVs unrolled round the profile (belly chamfer, side, shoulder) so the maze
    runs continuously over the folds; u follows the wall in craft coordinates (seamless along the hull)."""
    for s in solids:
        if s is None:
            continue
        for f in s.faces:
            if f.mat != "greeble":
                continue
            uvs = []
            for p in f.pts:
                sw = dot(p, F.d)
                uu = dot(sub(p, F.a), F.o)
                zz = p[2] - F.zb
                uvs.append(((sw + 1.0) / su, (_chain_param(uu, zz) + 0.5) / sv))
            f.uv, f.uvs, f.nrm = "pre", uvs, None
    return solids


def interior_base(F, s0=-3, s1=3):
    """Skirting closing the 3 cm interior recess at floor level, a top cap strip and a mid rail."""
    neg = mul(F.o, -1.0)
    return [obox(F.P(U_IN, 0, 0), F.d, (0, 0, 1), neg, s0, s1, -0.01, 0.16, 0.0, U_IN - 0.0005, "taupe", name="skirting"),
            obox(F.P(U_IN, 0, 0), F.d, (0, 0, 1), neg, s0, s1, WT - 0.08, WT, 0.0, U_IN - 0.0005, "hull", name="top cap"),
            obox(F.P(U_IN, 0, 0), F.d, (0, 0, 1), neg, s0, s1, 1.18, 1.25, 0.0005, 0.022, "taupe", name="interior rail")]


def lamps(F, pts, mat, size=0.06, interior=True):
    out = []
    for s, z in pts:
        if interior:
            out.append(int_plate(F, s - size / 2, s + size / 2, z - size / 2, z + size / 2, mat, depth=0.02, bevel=0.005))
        else:
            out.append(frustum(F.P(TW, 0, 0), F.d, (0, 0, 1), F.o, s - size / 2, s + size / 2, z - size / 2, z + size / 2,
                               0.05, 0.008, mat))
    return out


def straight_frame(mx, my, side, level=1):
    """side 'L': wall on the EAST edge of tile mx (left hull, outward -X); 'R': on the WEST edge (outward +X)."""
    zb = level * H
    if side == "L":
        return WallFrame((2 * mx + 1, -2 * my), (0, -1), (-1, 0), zb)
    return WallFrame((2 * mx - 1, -2 * my), (0, 1), (1, 0), zb)


# =================================================================== level 1 hull walls
def straight_wall(mx, my, side, layout, interior=None):
    F = straight_frame(mx, my, side)
    out = [wall_body(F)] + ext_detail(F, layout) + interior_base(F)
    if interior:
        out += interior(F)
    return profile_uv(out, F)


def deco_pink_panel(F):      # P047 (044): pink panel with a grid of blue lights, yellow lamps above
    out = [int_plate(F, -0.55, 0.10, 0.25, 0.95, "pinkpanel")]
    for i in range(3):
        for j in range(2):
            out += lamps(F, [(-0.42 + i * 0.2, 0.45 + j * 0.25)], "bluelight", 0.07)
    out += lamps(F, [(0.25, 1.75), (0.40, 1.75)], "amber")
    return out


def deco_strip(F):           # P048 (045): vertical amber light strip
    return [int_plate(F, -0.08, 0.02, 0.55, 1.05, "amber", depth=0.03, bevel=0.01)] + lamps(F, [(0.45, 1.70)], "amber")


def deco_dots_low(F):        # P049 (046): a row of yellow lamps low on the wall
    return lamps(F, [(-0.75, 0.62), (-0.55, 0.70), (-0.35, 0.78), (-0.15, 0.86)], "amber")


def deco_dots_left(F):       # P046 (043): two yellow lamps
    return lamps(F, [(-0.70, 0.90), (-0.70, 1.10)], "amber")


def deco_plain(F):
    return [int_plate(F, -0.85, 0.85, 1.45, 2.05, "interior", depth=0.02)]


def diag_frame(mx, my):
    """Diagonal corner wall of a hold corner tile (inner face on the tile diagonal), level 1."""
    cx, cy = 2 * mx, -2 * my
    if (mx, my) == (6, 15):   # 012: SE corner, NE-SW diagonal, outward SE
        return WallFrame((cx, cy), (1 / SQ2, 1 / SQ2), (1 / SQ2, -1 / SQ2))
    if (mx, my) == (3, 15):   # 014: SW corner, NW-SE diagonal, outward SW
        return WallFrame((cx, cy), (1 / SQ2, -1 / SQ2), (-1 / SQ2, -1 / SQ2))
    if (mx, my) == (6, 9):    # 016: NE corner, outward NE
        return WallFrame((cx, cy), (1 / SQ2, -1 / SQ2), (1 / SQ2, 1 / SQ2))
    if (mx, my) == (3, 9):    # 048: NW corner, outward NW
        return WallFrame((cx, cy), (1 / SQ2, 1 / SQ2), (-1 / SQ2, 1 / SQ2))
    raise KeyError((mx, my))


def diag_wall(mx, my, keep_y=None, interior=None):
    F = diag_frame(mx, my)
    body = wall_body(F, -4, 4)
    out = [body]
    if keep_y is not None:
        # end against the narrower cockpit wall: the exposed end face is hull, not a cut
        n = (0, -1, 0) if keep_y < -2 * my else (0, 1, 0)
        out = [clip_solid(body, n, dot(n, (0, keep_y, 0)), cap_mat="hull", cap_tag="keep")]
    # exterior plates on the outer face segment inside the tile (centred on the diagonal midpoint)
    out += ext_detail(F, "")
    out += interior_base(F, -2, 2)
    if interior:
        out += interior(F)
    return profile_uv(out, F)


def deco_048(F):             # P051: yellow light bar high left, three yellow dots low right
    return ([int_plate(F, -0.85, -0.25, 1.92, 1.98, "amber", depth=0.03, bevel=0.008)] +
            lamps(F, [(0.30, 0.95), (0.45, 0.95), (0.60, 0.95)], "amber") + deco_plain(F))


def miter_plane(inner, outer, keep_pt):
    """Vertical plane through two 2D points; returns (n, d) keeping the side containing keep_pt."""
    dx, dy = outer[0] - inner[0], outer[1] - inner[1]
    n = unit((dy, -dx, 0.0))
    d = dot(n, (inner[0], inner[1], 0.0))
    if dot(n, (keep_pt[0], keep_pt[1], 0.0)) > d:
        n, d = mul(n, -1.0), -d
    return n, d


def sliver(straight, diag_tile, inner, outer, keep_straight_pt, keep_diag_pt):
    """Hull corner piece outside a hold corner: straight wall up to the miter + the diagonal beyond it."""
    Fs = straight
    Fd = diag_frame(*diag_tile)
    n1, d1 = miter_plane(inner, outer, keep_straight_pt)
    n2, d2 = miter_plane(inner, outer, keep_diag_pt)
    out = []
    for F, (n, d) in ((Fs, (n1, d1)), (Fd, (n2, d2))):
        pieces = [wall_body(F, -4, 4)]
        pieces.append(obox(F.P(TW, 0, 0), F.d, (0, 0, 1), F.o, -4, 4, WT - 0.52, WT - 0.47, -0.01, 0.035, "hull", name="shoulder rail"))
        for p in pieces:
            q = clip_solid(p, n, d, cap_mat="hull", cap_tag="keep")
            if q is not None:
                out += profile_uv([q], F)
    return out


# =================================================================== level 1 nose, cockpit sides, canopy
def taper_planes(side, grow=0.0):
    """Planes that taper the nose: the outer side face narrows from u=TW at Y=-35 to u=0.35 at Y=-37 and on to the
    front; the top follows the windscreen slope. side 'L' (outer -X) or 'R' (outer +X). grow offsets outward."""
    if side == "L":
        a, b = (7.0 - TW, -35.0), (7.0 - 0.35, -37.0)
        n2 = unit((-(b[1] - a[1]), (b[0] - a[0]), 0.0))   # outward (-X-ish)
        if n2[0] > 0:
            n2 = mul(n2, -1.0)
    else:
        a, b = (11.0 + TW, -35.0), (11.0 + 0.35, -37.0)
        n2 = unit(((b[1] - a[1]), -(b[0] - a[0]), 0.0))
        if n2[0] < 0:
            n2 = mul(n2, -1.0)
    side_plane = (n2, dot(n2, (a[0], a[1], 0.0)) + grow)
    # top: z <= canopy_z(Y) (plane through (Y=-37, z=NOSE_TOP) rising north)
    nt = unit((0.0, -SLOPE_K, 1.0))
    top_plane = (nt, dot(nt, (0.0, -37.0, Z1 + NOSE_TOP)) + grow)
    return side_plane, top_plane


def cockpit_side(mx, my, side, layout, fin=False, interior=None, port=False, badge=False):
    """Cockpit hull wall (x3 east edge 'L' / x6 west edge 'R'); at y18 it tapers in plan and its top follows the
    windscreen slope down to the nose (P042/P011)."""
    F = straight_frame(mx, my, side)
    parts = [wall_body(F)] + ext_detail(F, layout) + interior_base(F)
    if interior:
        parts += interior(F)
    if port:   # P011: round light-grey port high on the north end
        c = F.P(TW, 1.80, 0.55 if side == "R" else -0.55)
        parts.append(lathe([(0.0, 0.26), (0.05, 0.26), (0.07, 0.20)], c, F.o, 16, "greymid", name="port"))
        parts.append(lathe([(0.0, 0.17), (0.09, 0.17), (0.10, 0.12)], c, F.o, 16, "steel", name="port hub"))
    if badge:
        parts += badge_disc(F)
    parts = profile_uv(parts, F)
    out = []
    if my == 18:
        sp, tp = taper_planes(side)
        for p in parts:
            q = clip_solid(p, *sp, cap_mat="greeble", cap_tag="keep")
            if q is not None:
                q = clip_solid(q, *tp, cap_mat="hull", cap_tag="keep")
            if q is not None:
                out.append(q)
    else:
        out = parts
    if fin:
        out += nose_fin(side)
    return out


def badge_disc(F, s=0.0, z=1.45):
    """P033: the X-COM roundel (yellow disc, red outlined emblem) as a raised disc on the cockpit side."""
    c = F.P(TW, z, s)
    d = lathe([(0.0, 0.50), (0.035, 0.50), (0.05, 0.47)], c, F.o, 28, "yellow", cap_mats={"end": "trim"}, name="badge")
    rect = MD.cell_uv(MD.DECAL["badge"])
    for f in d.faces:
        if f.tag == "lathecap" and dot(f.normal(), F.o) > 0.9:
            # map the disc face onto the badge decal (planar along the wall: t = along, b = up)
            t0 = dot(c, F.d) - 0.5 if False else None
            f.mat = "trim"
            tt, bb = plane_frame(f.normal())
            ct, cb = dot(c, tt), dot(c, bb)
            f.uv = ("rect", rect, (ct - 0.5, ct + 0.5, cb - 0.5, cb + 0.5))
    return [d]


def nose_fin(side):
    """Nose fins (P011 right, P045 left, composite): longitudinal vertical plates along the outer edge of the y18
    tiles, about 1.15 m outside the cockpit side, z 0.5 .. ~1.35 m (taller at the front), white louvred outer face,
    grey inner face, yellow cap along the top and down the front edge, two horizontal struts to the hull."""
    sgn = -1 if side == "L" else 1
    xo = 7.0 - 1.95 if side == "L" else 11.0 + 1.95          # outer face of the fin (inside the tile)
    xi = xo - sgn * 0.12
    xa, xb = min(xo, xi), max(xo, xi)
    yf, yb = -36.96, -35.20                                  # front (south) / back (north)
    zl = Z1 + 0.50
    ztf, ztb = Z1 + 1.36, Z1 + 1.18                          # top: higher at the front
    out = []
    g = box(xa, xb, yf, yb, zl, ztf + 0.1, "hull", name="fin plate")
    nt = unit((0.0, -(ztf - ztb) / (yb - yf) * -1.0, 1.0))
    # top plane through (yf, ztf) and (yb, ztb)
    k = (ztb - ztf) / (yb - yf)
    nt = unit((0.0, -k, 1.0))
    g = clip_solid(g, nt, dot(nt, (0.0, yf, ztf)), cap_mat="yellow", cap_tag="keep")
    rect = MD.cell_uv(MD.DECAL["grille"])
    for f in g.faces:
        n = f.normal()
        if n[0] * sgn > 0.99:                                 # outer face: white louvres
            f.mat = "trim"
            t, b = plane_frame(n)
            ts = sorted((dot((0, yf, 0), t), dot((0, yb, 0), t)))
            f.uv = ("rect", rect, (ts[0], ts[1], zl, ztf))
        elif n[1] < -0.99:                                    # front edge: yellow
            f.mat = "yellow"
    out.append(g)
    # yellow cap strip along the top, following the slope
    cap = box(xa - 0.02, xb + 0.02, yf - 0.02, yb, zl, ztf + 0.2, "yellow", name="fin cap")
    cap = clip_solid(cap, nt, dot(nt, (0.0, yf, ztf + 0.05)), cap_mat="yellow", cap_tag="keep")
    cap = clip_solid(cap, mul(nt, -1.0), -dot(nt, (0.0, yf, ztf - 0.02)), cap_mat="yellow", cap_tag="keep")
    if cap is not None:
        out.append(cap)
    # strake deck: grey sloping surface from the tapered hull side out to the fin top (P011 / P045 grey area)
    xw = 7.0 - 0.30 if side == "L" else 11.0 + 0.30
    prof = [(0.0, 0.92), (abs(xi - xw), 0.62), (abs(xi - xw), 1.18), (0.0, 1.30)]
    U = (sgn * 1.0, 0.0, 0.0)
    deck = extrude([(u, z) for u, z in prof], (xw, 0.0, Z1), U, (0, 0, 1), (0, 1, 0), -36.90, -35.30, "hull",
                   side_mats=["hulldark", "hull", "hull", "hull"], name="fin strake")
    out.append(deck)
    return out


def nose_block_planes(grow=0.0, x_left=None, x_right=None):
    """Front planes of the nose: front face Y=-37.75 with a large upper chamfer to the nose top and a lower chamfer
    to the belly; the corner posts add 45-degree vertical chamfers and the side tapers."""
    planes = []
    yf = NOSE_Y - grow
    planes.append(((0.0, -1.0, 0.0), -yf))                                           # Y >= front
    nu = unit((0.0, -1.0, 0.95))
    planes.append((nu, dot(nu, (0.0, yf, Z1 + 0.98)) + grow))                         # sloping upper nose plane
    nl = unit((0.0, -1.0, -1.0))
    planes.append((nl, dot(nl, (0.0, yf, Z1 + 0.14)) + grow))                       # lower chamfer
    planes.append(((0.0, 0.0, 1.0), Z1 + NOSE_TOP + grow))                           # top
    return planes


def corner_planes(side, grow=0.0):
    sp, tp = taper_planes(side, grow)
    if side == "L":
        nc = unit((-1.0, -1.0, 0.0))
        corner = (nc, dot(nc, (6.95, NOSE_Y, 0.0)) + grow)
    else:
        nc = unit((1.0, -1.0, 0.0))
        corner = (nc, dot(nc, (11.05, NOSE_Y, 0.0)) + grow)
    return [sp, corner]


def clip_all(s, planes, cap_mat="hull", cap_tag="keep"):
    for n, d in planes:
        if s is None:
            return None
        s = clip_solid(s, n, d, cap_mat=cap_mat, cap_tag=cap_tag)
    return s


def band_uv(s, z0, z1):
    rect = MD.cell_uv(MD.DECAL["noseband"])
    for f in s.faces:
        n = f.normal()
        if abs(n[2]) > 0.6:
            f.mat = "yellow"
            continue
        f.mat = "trim"
        t, b = plane_frame(n)
        cx = _cen(f.pts)
        # 2 m per decal repeat, seamless across tiles (decal tiles horizontally); split at wraps is avoided by
        # anchoring to the 2 m cell containing the face centre (faces never cross a 2 m line: tiles are 2 m)
        tc = dot(cx, t)
        t0 = math.floor((tc - 1.0) / 2.0) * 2.0 + 1.0
        f.uv = ("rect", rect, (t0, t0 + 2.0, Z1 + z0, Z1 + z1))
    return s


def nose_piece(x0, x1, side=None):
    """Nose block / corner post between x0 and x1 (Y -37 .. front), with the band slab wrapped round it."""
    zb = Z1 + BELLY
    body = box(x0, x1, NOSE_Y - 0.05, -37.0, zb, Z1 + NOSE_TOP + 0.05, "hull", mats={"yp": "interior"}, name="nose block")
    for f in body.faces:   # 010: cockpit front wall above the console; posts: joint with the tapered cockpit side
        if f.tag == "yp":
            f.tag = "keep"
            if side is not None:
                f.mat = "hull"
    planes = nose_block_planes()
    if side:
        planes = planes + corner_planes(side)
    body = clip_all(body, planes)
    band = box(x0 - (0.02 if side == "L" else 0), x1 + (0.02 if side == "R" else 0), NOSE_Y - 0.03, -37.25,
               Z1 + BAND_Z[0], Z1 + BAND_Z[1], "trim", name="nose band")
    bp = [((0.0, -1.0, 0.0), -(NOSE_Y - 0.012))]
    if side:
        bp += corner_planes(side, 0.012)
    band = clip_all(band, bp, cap_mat="trim")
    out = [body]
    if band is not None:
        out.append(band_uv(band, *BAND_Z))
    # raised rib above the band and a dark intake slot under it, along the front
    rib = box(x0, x1, NOSE_Y - 0.03, -37.4, Z1 + BAND_Z[1] + 0.06, Z1 + BAND_Z[1] + 0.11, "hull", name="nose rib")
    rib = clip_all(rib, ([] if not side else corner_planes(side, 0.02)))
    if rib is not None:
        out.append(rib)
    slot = box(x0, x1, NOSE_Y - 0.008, -37.4, Z1 + 0.13, Z1 + BAND_Z[0] - 0.03, "dark", name="nose slot")
    slot = clip_all(slot, ([] if not side else corner_planes(side, 0.008)))
    if slot is not None:
        out.append(slot)
    return out


def nose_010(mx):
    x0, x1 = 2 * mx - 1, 2 * mx + 1
    return nose_piece(x0, x1)


def nose_post(side):
    if side == "L":   # 009 [3,19]
        out = nose_piece(7.0 - TW, 7.0, "L")
        out.append(box(6.55, 6.75, NOSE_Y + 0.20, NOSE_Y + 0.40, Z1 + 1.02, Z1 + 1.10, "amber", name="corner lamp"))
        return out
    out = nose_piece(11.0, 11.0 + TW, "R")   # 017 [6,19]
    out.append(box(11.25, 11.45, NOSE_Y + 0.20, NOSE_Y + 0.40, Z1 + 1.02, Z1 + 1.10, "amber", name="corner lamp"))
    # P017: inset panel on the post
    F = WallFrame((11.0, -38.0), (0, 1), (1, 0))
    return out


def canopy(mx):
    """Windscreen 024 [4,18] / 025 [5,18] (P024/P025 back-projected on the sloped nose top): ONE rounded-rectangle
    light-blue pane, long axis across the craft (X 7.52..10.48), set into the grey sloped nose top (Y -36.80..-35.20
    in plan) with a thin dark bevelled rim and a grey border all round; glass decal with speckle/reflection."""
    x0, x1 = 2 * mx - 1, 2 * mx + 1
    S = unit((0.0, 2.0, WT - NOSE_TOP))
    Lc = math.hypot(2.0, WT - NOSE_TOP)
    N = unit(cross((1.0, 0.0, 0.0), S))
    if N[2] < 0:
        N = mul(N, -1.0)
    o = (0.0, -37.0, Z1 + NOSE_TOP)
    top = obox(o, (1, 0, 0), S, N, x0, x1, 0.0, Lc, -0.12, 0.0, "hull", name="nose top")
    for f in top.faces:      # its X ends meet the cockpit sides' 3 cm interior recess: finished hull, not a cut
        if f.mat == "hull" and abs(f.normal()[0]) > 0.99 and ((mx == 4 and f.normal()[0] < 0) or (mx == 5 and f.normal()[0] > 0)):
            f.tag = "keep"
    out = [top]
    # pill outline in canopy coordinates (a = X, b = along the slope)
    kb = Lc / 2.0
    a0, a1 = 7.52, 10.48
    b0, b1 = (36.80 - 37.0 + 0.0) * 0 + (37.0 - 36.80) * kb, (37.0 - 35.20) * kb
    r = 0.46

    def rrect(off):
        pts = []
        for (cxr, cyr, ang0) in ((a1 - r, b0 + r, -90), (a1 - r, b1 - r, 0), (a0 + r, b1 - r, 90), (a0 + r, b0 + r, 180)):
            for k in range(7):
                ang = math.radians(ang0 + 90 * k / 6)
                pts.append((cxr + (r + off) * math.cos(ang), cyr + (r + off) * math.sin(ang)))
        return pts

    rim0 = extrude(rrect(0.17), o, (1, 0, 0), S, N, -0.02, 0.003, "white", name="window light bevel")
    rim1 = extrude(rrect(0.085), o, (1, 0, 0), S, N, -0.02, 0.006, "black", name="window rim outer")
    rim2 = extrude(rrect(0.05), o, (1, 0, 0), S, N, -0.02, 0.013, "dark", name="window rim bevel")
    glass = extrude(rrect(0.0), o, (1, 0, 0), S, N, -0.02, 0.020, "glass", name="window glass")
    rect = MD.cell_uv(MD.DECAL["glass"])
    for f in glass.faces:
        if dot(f.normal(), N) > 0.99:
            f.mat = "trim"
            t, b = plane_frame(f.normal())
            ts = sorted((dot(add(o, (a0, 0, 0)), t), dot(add(o, (a1, 0, 0)), t)))
            bs = sorted((dot(add(o, mul(S, b0)), b), dot(add(o, mul(S, b1)), b)))
            f.uv = ("rect", rect, (ts[0], ts[1], bs[0], bs[1]))
        else:
            f.mat = "black"
    out += [rim0, rim1, rim2, glass]
    # amber frame markers (P024: on the left border; P025: at the front border)
    if mx == 4:
        out.append(frustum(add(o, mul(S, 0.95)), (1, 0, 0), S, N, 7.14, 7.26, -0.06, 0.06, 0.03, 0.01, "amber"))
    else:
        out.append(frustum(add(o, mul(S, 0.12)), (1, 0, 0), S, N, 9.95, 10.07, -0.05, 0.05, 0.03, 0.01, "amber"))
        out.append(frustum(add(o, mul(S, 0.12)), (1, 0, 0), S, N, 10.15, 10.27, -0.05, 0.05, 0.03, 0.01, "amber"))
    return out


def seat(mx, my):
    """041 pilot seat (P044): lavender bucket seat inside a low brown wrap-round frame (back on the north, arms east and
    west), on a purple pedestal and a steel base, facing the nose (south)."""
    cx, cy = 2 * mx, -2 * my
    z = Z1
    out = [lathe([(0.0, 0.30), (0.06, 0.30), (0.08, 0.12)], (cx, cy, z), (0, 0, 1), 12, "steel", name="seat base"),
           lathe([(0.0, 0.10), (0.40, 0.10)], (cx, cy, z + 0.06), (0, 0, 1), 10, "purpledark", name="pedestal")]
    out.append(lathe([(0.0, 0.44), (0.10, 0.44)], (cx, cy, z + 0.44), (0, 0, 1), 16, "taupe", name="seat pan frame"))
    out.append(lathe([(0.0, 0.38), (0.08, 0.36)], (cx, cy, z + 0.54), (0, 0, 1), 16, "seat", name="cushion"))
    # wrap-round frame: back (north) and two arms, low like the sprite
    out.append(box(cx - 0.46, cx + 0.46, cy + 0.30, cy + 0.44, z + 0.50, z + 1.05, "taupe", name="back frame"))
    out.append(box(cx - 0.38, cx + 0.38, cy + 0.26, cy + 0.30, z + 0.60, z + 1.00, "seat", name="back cushion"))
    for sx in (-1, 1):
        out.append(box(cx + sx * 0.44 - 0.07, cx + sx * 0.44 + 0.07, cy - 0.30, cy + 0.44, z + 0.50, z + 0.82, "taupe", name="arm"))
    return out


def console(mx, blue=False):
    """039 / 040 cockpit floor with a console block (P042 / P043): a beige block ~1.45 m square and 1.15 m tall in the
    south-west of each cockpit tile, channelled south face, a dark knee recess on its east face, and the instrument
    top sloping down toward the seats with the console decal and a row of amber (040: blue) and red lamps."""
    x0, x1, y0, y1 = 2 * mx - 1, 2 * mx + 1, -37.0, -35.0
    out = deck_slab(mx, 18)
    bx0, bx1, by0, by1 = x0 + 0.05, x0 + 1.45, -37.0, -35.65
    zs, zn = 1.15, 0.86
    blk = box(bx0, bx1, by0, by1, Z1, Z1 + zs + 0.05, "beige", mats={"yn": "interior"}, name="console")
    k = (zn - zs) / (by1 - by0)
    nt = unit((0.0, -k, 1.0))
    blk = clip_solid(blk, nt, dot(nt, (0.0, by0, Z1 + zs)), cap_mat="trim", cap_tag="keep")
    rect = MD.cell_uv(MD.DECAL["console_beige"])
    for f in blk.faces:
        if f.mat == "trim":
            t, b = plane_frame(f.normal())
            ts = sorted((dot((bx0, 0, 0), t), dot((bx1, 0, 0), t)))
            bs = sorted((dot((0, by0, Z1 + zs), b), dot((0, by1, Z1 + zn), b)))
            f.uv = ("rect", rect, (ts[0], ts[1], bs[0], bs[1]))
        elif f.normal()[1] > 0.99:
            f.mat = "interior"
    out.append(blk)
    # knee recess on the east face (P042 arch)
    out.append(box(bx1, bx1 + 0.012, by0 + 0.30, by1 - 0.25, Z1 + 0.02, Z1 + 0.62, "black", name="knee recess"))
    out.append(box(bx1, bx1 + 0.03, by0 + 0.22, by0 + 0.30, Z1 + 0.0, Z1 + 0.70, "taupe", name="recess frame"))
    out.append(box(bx1, bx1 + 0.03, by1 - 0.25, by1 - 0.17, Z1 + 0.0, Z1 + 0.70, "taupe", name="recess frame"))
    col = "bluelight" if blue else "amber"
    for i in range(4):
        out.append(box(bx0 + 0.25 + i * 0.22, bx0 + 0.37 + i * 0.22, by0 + 0.05, by0 + 0.17, Z1 + zs, Z1 + zs + 0.035, col, name="lamp"))
    out.append(box(bx1 - 0.30, bx1 - 0.18, by0 + 0.05, by0 + 0.17, Z1 + zs, Z1 + zs + 0.035, "redglow" if not blue else "bluelight", name="lamp"))
    return out


def deck_slab(mx, my, clip_diag=None):
    x0, x1, y0, y1 = 2 * mx - 1, 2 * mx + 1, -2 * my - 1, -2 * my + 1
    s = box(x0, x1, y0, y1, Z1 + BELLY, Z1, "hulldark", mats={"zp": "deck"}, name="deck")
    if clip_diag:
        n, d = clip_diag
        s = clip_solid(s, n, d, cap_mat="section")
    return [s]


def corner_floor(mx, my):
    F = diag_frame(mx, my)
    n = F.o                        # keep the inner side: dot(o, p - a) <= 0
    return deck_slab(mx, my, (n, dot(n, F.a)))


# =================================================================== engines (level 1)
NAC_Z, NAC_R = 0.85, 0.72
NAC_Y0 = -19.0                 # profile length origin (north edge of y10), l grows southward


def nacelle(mx):
    """Engine nacelle along Y on tile column mx (P031 / P030 / P021 / P020): grey machinery casing, raised bands at
    every metre seam, a tapered rear with a dark exhaust, and the purple dome at the front (south) with a dark
    intake at its tip. Cut faces of the casing are the sprites' red-glowing core."""
    cx = 2 * mx
    c = (cx, NAC_Y0, Z1 + NAC_Z)
    ax = (0.0, -1.0, 0.0)
    body = lathe([(0.20, 0.40), (0.42, 0.62), (0.62, NAC_R), (5.62, NAC_R)], c, ax, 20, "hull",
                 cap_mats={0: "dark", "end": "redglow"}, name="nacelle", su=1.0, sv=1.0, seg_start=-math.pi / 2)
    body.cap_mat = "redglow"
    L0, Rd = 6.10, NAC_R + 0.01
    dome_prof = [(5.60, Rd)] + [(L0 + 0.78 * math.sin(a), max(Rd * math.cos(a), 0.11))
                                for a in [i * (math.pi / 2) / 7 for i in range(0, 7)]]
    dome = lathe(dome_prof, c, ax, 20, "purple", cap_mats={0: "purpledark", "end": "purpledark"}, name="dome",
                 seg_start=-math.pi / 2)
    dome.cap_mat = "purpledark"
    out = [body, dome]
    # raised bands every 2 m (seams split them) and between
    for l in (1.0, 2.0, 3.0, 4.0, 5.0):
        b = lathe([(l - 0.07, NAC_R + 0.035), (l + 0.07, NAC_R + 0.035)], c, ax, 20, "hull", name="band",
                  seg_start=-math.pi / 2)
        b.cap_mat = "hull"
        out.append(b)
    # dark exhaust cone at the rear
    ex = lathe([(0.06, 0.30), (0.24, 0.42)], c, ax, 16, "black", cap_mats={0: "redglow"}, name="exhaust",
               seg_start=-math.pi / 2)
    out.append(ex)
    # blue running lights along the top of the rear segment (P031: rows of blue dots, two frames blink)
    for l in (0.75, 1.05, 1.35, 1.65):
        for ang in (-0.55, 0.0, 0.55):
            px = cx + math.sin(ang) * (NAC_R + 0.01)
            pz = Z1 + NAC_Z + math.cos(ang) * (NAC_R + 0.01)
            out.append(box(px - 0.035, px + 0.035, NAC_Y0 - l - 0.035, NAC_Y0 - l + 0.035, pz - 0.03, pz + 0.035,
                           "bluelight", name="blue light"))
    return out


HOUSING_Y = (-22.85, -21.15)
HOUSING_Z = (1.22, WT)


def housing(mx, side):
    """Nacelle housing on y11 (P030 right / P022 left): boxy casing over the nacelle with vertical louvre grilles on
    its front (south) face, the red hazard mark, and on the right the blue '18' plate on top. Top flush with the
    hull top (WT), continuing the pylon."""
    cx = 2 * mx
    sgn = 1 if side == "R" else -1
    x0, x1 = (cx - 1.0, cx + 0.88) if side == "R" else (cx - 0.88, cx + 1.0)
    s = box(x0, x1, HOUSING_Y[0], HOUSING_Y[1], Z1 + HOUSING_Z[0], Z1 + HOUSING_Z[1], "hull", name="housing")
    # chamfer the outer top edge and the bottom edges
    n = unit((sgn * 1.0, 0.0, 1.0))
    s = clip_solid(s, n, dot(n, (cx + sgn * 0.88, 0, Z1 + HOUSING_Z[1] - 0.30)), cap_mat="hull", cap_tag="keep")
    n = unit((sgn * 1.0, 0.0, -1.0))
    s = clip_solid(s, n, dot(n, (cx + sgn * 0.88, 0, Z1 + HOUSING_Z[0] + 0.25)), cap_mat="hulldark", cap_tag="keep")
    for f in s.faces:   # the face against the pylon stays hull (the pylon is slightly smaller)
        if f.normal()[0] * sgn < -0.99:
            f.tag = "keep"
    out = [s]
    # louvre grilles (decal panels) on the south face
    rect = MD.cell_uv(MD.DECAL["grille"])
    gx = (x0 + 0.12, x0 + 1.02) if side == "R" else (x1 - 1.02, x1 - 0.12)
    gpl = frustum((0.0, HOUSING_Y[0], 0.0), (1, 0, 0), (0, 0, 1), (0, -1, 0), gx[0], gx[1], Z1 + 1.40, Z1 + 2.15, 0.035, 0.015,
                  "white", side_mat="hull")
    for f in gpl.faces:
        if f.tag == "top":
            f.mat = "trim"
            t, b = plane_frame(f.normal())
            ts = sorted((dot((gx[0], 0, 0), t), dot((gx[1], 0, 0), t)))
            f.uv = ("rect", rect, (ts[0], ts[1], Z1 + 1.40, Z1 + 2.15))
    out.append(gpl)
    # red hazard mark
    mrect = MD.cell_uv(MD.DECAL["mark_red"])
    mx0 = (gx[1] + 0.10) if side == "R" else (gx[0] - 0.60)
    mk = frustum((0.0, HOUSING_Y[0], 0.0), (1, 0, 0), (0, 0, 1), (0, -1, 0), mx0, mx0 + 0.50, Z1 + 1.55, Z1 + 2.05, 0.012, 0.004,
                 "hullgrey")
    for f in mk.faces:
        if f.tag == "top":
            f.mat = "trim"
            t, b = plane_frame(f.normal())
            ts = sorted((dot((mx0, 0, 0), t), dot((mx0 + 0.5, 0, 0), t)))
            f.uv = ("rect", mrect, (ts[0], ts[1], Z1 + 1.55, Z1 + 2.05))
    out.append(mk)
    if side == "R":   # blue '18' plate on top
        r18 = MD.cell_uv(MD.DECAL["mark_18"])
        p = frustum((0.0, 0.0, Z1 + HOUSING_Z[1]), (1, 0, 0), (0, 1, 0), (0, 0, 1), cx - 0.15, cx + 0.55, HOUSING_Y[0] + 0.35,
                    HOUSING_Y[0] + 1.05, 0.02, 0.01, "lavlight")
        for f in p.faces:
            if f.tag == "top":
                f.mat = "trim"
                f.uv = ("rect", r18, (cx - 0.15, cx + 0.55, HOUSING_Y[0] + 0.35, HOUSING_Y[0] + 1.05))
        out.append(p)
    # top panel seams / raised plates
    out.append(frustum((0.0, 0.0, Z1 + HOUSING_Z[1]), (1, 0, 0), (0, 1, 0), (0, 0, 1), cx - 0.95 if side == "R" else cx - 0.25,
                       cx - 0.25 if side == "R" else cx + 0.45, HOUSING_Y[0] + 0.15, HOUSING_Y[1] - 0.15, 0.03, 0.02, "hull"))
    # web joining the housing to the nacelle below
    out.append(box(cx - 0.45, cx + 0.45, HOUSING_Y[0] + 0.10, HOUSING_Y[1] - 0.10, Z1 + NAC_Z, Z1 + HOUSING_Z[0] + 0.05, "hulldark",
                   name="web"))
    return out


def pylon(side, mx):
    """Thick arm from the hull side to the nacelle housing at y11 (027 / 047), its top level with the hull top."""
    if side == "R":
        x0, x1 = 13.0 + 0.40, 2 * mx + 1.0
    else:
        x0, x1 = 2 * mx - 1.0, 5.0 - 0.40
    s = box(x0, x1, HOUSING_Y[0] + 0.05, HOUSING_Y[1] - 0.05, Z1 + HOUSING_Z[0] + 0.15, Z1 + HOUSING_Z[1], "hull", name="pylon")
    # bottom chamfers (fore and aft) so the arm reads as a faired beam
    for sy in (-1, 1):
        n = unit((0.0, sy * 1.0, -1.0))
        yy = HOUSING_Y[1] - 0.05 if sy > 0 else HOUSING_Y[0] + 0.05
        s = clip_solid(s, n, dot(n, (0, yy, Z1 + HOUSING_Z[0] + 0.15 + 0.30)), cap_mat="hull", cap_tag="keep")
    out = [s]
    rect = MD.cell_uv(MD.DECAL["grille"])
    gx = (x0 + 0.20, x1 - 0.05) if side == "R" else (x0 + 0.05, x1 - 0.20)
    g = frustum((0.0, HOUSING_Y[0] + 0.05, 0.0), (1, 0, 0), (0, 0, 1), (0, -1, 0), gx[0], gx[1], Z1 + 1.78, Z1 + 2.28, 0.03, 0.012,
                "white", side_mat="hull")
    for f in g.faces:
        if f.tag == "top":
            f.mat = "trim"
            t, b = plane_frame(f.normal())
            ts = sorted((dot((gx[0], 0, 0), t), dot((gx[1], 0, 0), t)))
            f.uv = ("rect", rect, (ts[0], ts[1], Z1 + 1.78, Z1 + 2.28))
    out.append(g)
    return out


# =================================================================== level 0: gear, ramp
BELLY_Z0 = H + BELLY           # belly height above the ground


def gear(mx, my, raked):
    """Landing gear (P052 raked / P053 straight): lavender housing under the belly (purple rim, three light louvre
    slots), a lavender strut with a dog-leg knee (raked) or a straight neck, a dark-grey bolted 1.5 m foot pad with a
    raised centre block."""
    cx, cy = 2 * mx, -2 * my
    out = []
    hy = cy + (0.50 if raked else 0.0)
    hw = 0.36 if raked else 0.50
    hz0 = BELLY_Z0 - (1.00 if raked else 1.05)
    out.append(box(cx - hw, cx + hw, hy - hw, hy + hw, hz0, BELLY_Z0, "lavender", name="gear housing"))
    out.append(box(cx - hw - 0.03, cx + hw + 0.03, hy - hw - 0.03, hy + hw + 0.03, BELLY_Z0 - 0.07, BELLY_Z0, "purple", name="rim"))
    for k in range(3):
        xx = cx - hw * 0.55 + k * hw * 0.55
        out.append(box(xx - 0.04, xx + 0.04, hy - hw - 0.02, hy - hw + 0.01, hz0 + 0.18, BELLY_Z0 - 0.20, "lavlight", name="louvre"))
        if not raked:
            yy = hy - hw * 0.55 + k * hw * 0.55
            out.append(box(cx + hw - 0.01, cx + hw + 0.02, yy - 0.04, yy + 0.04, hz0 + 0.18, BELLY_Z0 - 0.20, "lavlight", name="louvre"))
    fz = 0.36
    t = 0.15
    if raked:
        # dog-leg: from under the housing angled forward-down to the knee, then straight down to the foot
        knee = (cx, cy - 0.10, 0.95)
        top = (cx, hy, hz0 + 0.06)
        A = unit(sub(knee, top))
        L = math.dist(knee, top)
        N = unit(cross((1, 0, 0), A))
        out.append(obox(top, (1, 0, 0), A, N, -t, t, -0.05, L + 0.10, -t, t, "lavender", name="upper strut"))
        out.append(box(cx - t, cx + t, cy - 0.10 - t, cy - 0.10 + t, fz - 0.02, knee[2] + 0.12, "lavender", name="lower strut"))
        out.append(lathe([(0.0, 0.17), (0.34, 0.17)], (cx - 0.17, cy - 0.10, knee[2]), (1, 0, 0), 12, "purple", name="knee joint"))
        out.append(lathe([(0.0, 0.06), (L * 0.85, 0.06)], add(top, (0.0, 0.0, -0.02)), A, 8, "steel", name="piston"))
        fy = cy - 0.10
    else:
        out.append(box(cx - t - 0.02, cx + t + 0.02, cy - t - 0.02, cy + t + 0.02, fz - 0.02, hz0 + 0.02, "lavender", name="strut"))
        out.append(lathe([(0.0, 0.065), (hz0 - fz - 0.2, 0.065)], (cx + 0.26, cy, fz + 0.1), (0, 0, 1), 10, "steel", name="piston"))
        fy = cy
    # foot pad
    out.append(box(cx - 0.75, cx + 0.75, fy - 0.75, fy + 0.75, 0.0, 0.10, "dark", name="pad"))
    out.append(box(cx - 0.62, cx + 0.62, fy - 0.62, fy + 0.62, 0.10, 0.14, "greymid", name="pad plate"))
    out.append(box(cx - 0.26, cx + 0.26, fy - 0.26, fy + 0.26, 0.14, fz, "greymid", name="foot block"))
    bolts = {(bx, by) for bx in (-0.52, -0.17, 0.17, 0.52) for by in (-0.52, 0.52)}
    bolts |= {(by, bx) for (bx, by) in list(bolts)}
    for bx, by in sorted(bolts):
        out.append(box(cx + bx - 0.045, cx + bx + 0.045, fy + by - 0.045, fy + by + 0.045, 0.14, 0.18, "steel", name="bolt"))
    return out


def ramp_z(y):
    return (-11.0 - y) / 6.0 * H


def ramp(mx, my):
    """Boarding ramp 055/054/053 (P061, p_level 0/8/16): one continuous plate from the ground at Y=-11 up to the deck
    at Y=-17, brown deck plating with transverse grip bars and edge rails on each 2 m tile."""
    x0, x1, y0, y1 = 2 * mx - 1, 2 * mx + 1, -2 * my - 1, -2 * my + 1
    S = unit((0.0, -6.0, H))
    N = unit(cross((1, 0, 0), S))
    if N[2] < 0:
        N = mul(N, -1.0)
    o = (0.0, -11.0, 0.0)
    L = math.hypot(6.0, H)
    s0 = (-11.0 - y1) / 6.0 * L
    s1 = (-11.0 - y0) / 6.0 * L
    out = [obox(o, (1, 0, 0), S, N, x0, x1, s0, s1, -0.10, 0.0, "ramp", name="ramp plate")]
    for sx in (x0, x1 - 0.07):
        out.append(obox(o, (1, 0, 0), S, N, sx, sx + 0.07, s0, s1, -0.18, 0.06, "hulldark", name="edge rail"))
    k = math.floor(s0 / 0.5) * 0.5 + 0.25
    while k < s1:
        if k - 0.03 > s0 and k + 0.03 < s1:
            out.append(obox(o, (1, 0, 0), S, N, x0 + 0.10, x1 - 0.10, k - 0.03, k + 0.03, 0.0, 0.022, "steel", name="grip bar"))
        k += 0.5
    for q in out:           # the slab ends are perpendicular to the slope: tile-plane trims are finished edges
        q.cap_mat = "hulldark"
    return out


# =================================================================== hatch doors (unused records)
def hatch(mx, state, mirror=False):
    """051/052 rear hatch leaves (P054-P060, UFO-door type) on the north edge of the hold rear tiles; 057/058 the open
    states (leaf slid aside)."""
    x0, x1 = 2 * mx - 1, 2 * mx + 1
    yN = -2 * 9 + 1      # north edge of y9
    if state == "closed":
        lx0, lx1 = x0, x1
    else:
        lx0, lx1 = (x0, x0 + 0.40) if not mirror else (x1 - 0.40, x1)
    out = [box(lx0, lx1, yN - 0.16, yN, Z1, Z1 + WT - 0.05, "purple", name="hatch leaf")]
    if lx1 - lx0 > 0.5:
        out.append(frustum((0.0, yN - 0.16, 0.0), (1, 0, 0), (0, 0, 1), (0, -1, 0), lx0 + 0.08, lx1 - 0.08, Z1 + 0.18,
                           Z1 + WT - 0.25, 0.03, 0.02, "lavlight", side_mat="purple"))
    out.append(box(x0, x1, yN - 0.70, yN, Z1, Z1 + 0.04, "lavlight", name="sill"))
    return out


# =================================================================== registry
UNUSED_TILE = {23: (8, 11, 1), 26: (7, 12, 1), 40: (5, 18, 1), 51: (4, 9, 1), 52: (5, 9, 1), 57: (4, 9, 1), 58: (5, 9, 1)}


def canonical(rec):
    if rec in UNUSED_TILE:
        return UNUSED_TILE[rec]
    over = {2: (6, 12, 2), 3: (3, 12, 2), 56: (4, 12, 2), 8: (4, 16, 2), 34: (4, 12, 1), 31: (7, 10, 1), 43: (2, 13, 1),
            44: (2, 10, 1), 13: (6, 8, 1), 20: (8, 13, 1), 21: (8, 12, 1), 29: (8, 10, 1), 10: (4, 19, 1), 41: (4, 17, 1),
            39: (4, 18, 1), 49: (3, 15, 0), 50: (3, 10, 0), 53: (4, 8, 0), 54: (4, 7, 0), 55: (4, 6, 0)}
    if rec in over:
        return over[rec]
    (mx, my, mz), _ = C.PLACEMENTS[rec][0]
    return (mx, my, mz)


def build(rec):
    mx, my, mz = canonical(rec)
    if rec <= 7:
        return C.roof_bevel(mx, my)
    if rec == 56:
        return C.roof_field(mx, my)
    if rec == 8:
        return C.cockpit_roof(mx, my)
    if rec == 9:
        return nose_post("L")
    if rec == 17:
        return nose_post("R")
    if rec == 10:
        return nose_010(mx)
    if rec == 11:
        return cockpit_side(mx, my, "R", "PPVP", fin=True, port=True)
    if rec == 42:
        return cockpit_side(mx, my, "L", "PPPP", fin=True, interior=lambda F: (
            [int_plate(F, -0.80, 0.10, 0.35, 1.05, "pinkpanel")] + lamps(F, [(-0.65 + 0.18 * i, 0.75) for i in range(4)], "bluelight", 0.07) +
            lamps(F, [(0.45, 1.55)], "redglow", 0.12) + lamps(F, [(0.80, 0.4 + 0.2 * k) for k in range(5)], "amber", 0.06)))
    if rec == 30:
        return cockpit_side(mx, my, "R", "P-P-", badge=True)
    if rec in (31, 32, 33, 26):
        lay = {31: "PPSP", 32: "VPPS", 33: "PVSP", 26: "SPPV"}[rec]
        return straight_wall(mx, my, "R", lay, deco_plain)
    if rec in (43, 44, 45, 46):
        deco = {43: deco_dots_left, 44: deco_pink_panel, 45: deco_strip, 46: deco_dots_low}[rec]
        lay = {43: "PPPP", 44: "PSPP", 45: "VPPP", 46: "PPVP"}[rec]
        return straight_wall(mx, my, "L", lay, deco)
    if rec == 47:
        return straight_wall(mx, my, "L", "PP--", lambda F: lamps(F, [(0.6, 0.45)], "amber")) + pylon("L", mx)
    if rec == 27:
        return straight_wall(mx, my, "R", "PP--", deco_plain) + pylon("R", mx)
    if rec == 12:
        return diag_wall(mx, my, keep_y=-31.0, interior=deco_plain)
    if rec == 14:
        return diag_wall(mx, my, keep_y=-31.0, interior=deco_plain)
    if rec == 16:
        return diag_wall(mx, my, interior=deco_plain)
    if rec == 48:
        return diag_wall(mx, my, interior=deco_048)
    if rec == 15:
        return sliver(straight_frame(2, 15, "L"), (3, 15), (5.0, -29.0), (5.0 - TW, -29.0 - (TW * SQ2 - TW)),
                      (4.6, -28.0), (5.5, -30.5))
    if rec == 19:
        return sliver(straight_frame(7, 15, "R"), (6, 15), (13.0, -29.0), (13.0 + TW, -29.0 - (TW * SQ2 - TW)),
                      (13.4, -28.0), (12.5, -30.5))
    if rec == 13:
        F = diag_frame(6, 9)
        pieces = [wall_body(F, -4, 4),
                  obox(F.P(TW, 0, 0), F.d, (0, 0, 1), F.o, -4, 4, WT - 0.52, WT - 0.47, -0.01, 0.035, "hull", name="shoulder rail")]
        out = []
        for p in pieces:
            q = clip_solid(p, (-1, 0, 0), -11.0, cap_mat="hull", cap_tag="keep")   # hatch-side end of the hull (X >= 11)
            if q is not None:
                q = clip_solid(q, (0, -1, 0), 17.0, cap_mat="hull", cap_tag="keep")  # Y >= -17: face toward 016 (hull)
            if q is not None:
                out.append(q)
        return profile_uv(out, F)
    if rec == 18:
        F = diag_frame(3, 9)
        out = []
        for p in [wall_body(F, -4, 4),
                  obox(F.P(TW, 0, 0), F.d, (0, 0, 1), F.o, -4, 4, WT - 0.52, WT - 0.47, -0.01, 0.035, "hull", name="shoulder rail")]:
            q = clip_solid(p, (1, 0, 0), 7.0, cap_mat="hull", cap_tag="keep")
            if q is not None:
                out.append(q)
        return profile_uv(out, F)
    if rec == 34:
        return deck_slab(mx, my)
    if rec in (35, 36, 37, 38):
        tile = {35: (3, 15), 36: (6, 9), 37: (6, 15), 38: (3, 9)}[rec]
        return corner_floor(*tile)
    if rec in (39, 40):
        return console(mx, blue=(rec == 40))
    if rec == 41:
        return seat(mx, my)
    if rec in (24, 25):
        return canopy(mx)
    if rec in (20, 21, 29):
        return nacelle(mx)
    if rec == 28:
        return nacelle(mx) + housing(mx, "R")
    if rec == 22:
        return nacelle(mx) + housing(mx, "L")
    if rec == 23:
        # unused housing block variant (P023): the housing and pylon block without the nacelle
        return housing(mx, "R")[:1]
    if rec == 49:
        return gear(mx, my, raked=True)
    if rec == 50:
        return gear(mx, my, raked=False)
    if rec in (53, 54, 55):
        return ramp(mx, my)
    if rec == 51:
        return hatch(mx, "closed")
    if rec == 52:
        return hatch(mx, "closed", mirror=True)
    if rec == 57:
        return hatch(mx, "open")
    if rec == 58:
        return hatch(mx, "open", mirror=True)
    raise KeyError(rec)


NO_AUTO_SECTION = {8, 56, 53, 54, 55}


def record_faces(rec):
    tile = canonical(rec)
    solids = [s for s in build(rec) if s is not None]
    if rec not in NO_AUTO_SECTION:
        C.auto_section(solids, tile)
    return tile, solids


RECS = C.RECS
PLACEMENTS = C.PLACEMENTS

