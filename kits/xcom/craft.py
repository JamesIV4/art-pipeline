# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/craft.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""AVENGER v2 master craft, defined in craft coordinates (see avgeo.py) as unions of convex solids.

Each record builder returns the solids that make up its tile; continuous surfaces (roof profile, nose
band, hull greeble) are defined as world-space functions so neighbouring records meet exactly.
Layout (AVENGER.MAP 10 x 20 x 3, see art/team/xbase_opus55/avenger01/research.md):
  hold x3..6 / y9..15 (X 5..13, Y -17..-31), corner tiles chamfered on their diagonals; cockpit x4..5 / y16..18;
  nose y19 (front face Y = -37.75); walls 0.5 m thick with the inner face on the tile edge.
"""
import json
import math
from pathlib import Path

from avgeo import (H, Solid, Face, box, prism, extrude, lathe, clip_poly2, clip_solid, clip_box, ccw, decal, swatch,
                   set_mat, unit, dot, sub, add, mul, cross, plane_frame, bounds_tb)
import meshdata as MD

HERE = Path(__file__).resolve().parent
from xcom_kit_paths import ROOT, WORK  # noqa: E402  (kit folder is on sys.path via the caller)
SLAB = -0.08            # slab / wall bottom below the walking surface of a level
WALL_TOP = H - 0.005    # walls stop 5 mm below the level line
T_WALL = 0.5

# ------------------------------------------------------------------ map / placements
_recs = json.loads((WORK / "sources/records.json").read_text(encoding="utf-8"))
RECS = {r["record"]: r for r in _recs}


def _placements():
    root = ROOT
    data = (root / "reference/MAPS/AVENGER.MAP").read_bytes()
    sy, sx, sz = data[:3]
    nb = len((root / "reference/TERRAIN/BLANKS.MCD").read_bytes()) // 62
    out = {}
    for i in range(sx * sy * sz):
        pos = (i % sx, i // sx % sy, sz - 1 - i // (sx * sy))
        for part, v in enumerate(data[3 + i * 4:7 + i * 4]):
            if v >= nb:
                out.setdefault(v - nb, []).append((pos, ("floor", "west", "north", "object")[part]))
    return out


PLACEMENTS = _placements()


def keep(solid, tags=None):
    for f in solid.faces:
        if tags is None or f.tag in tags:
            f.tag = "keep"
    return solid


def auto_section(faces_solids, tile):
    """Faces lying on the tile boundary planes and facing out of the tile become cut sections ('section')."""
    x0, x1, y0, y1 = MD.tile_box(tile)
    for s in faces_solids:
        for f in s.faces:
            if f.tag == "keep":
                continue
            n = f.normal()
            xs = [p[0] for p in f.pts]; ys = [p[1] for p in f.pts]
            on = ((n[0] > 0.999 and min(xs) > x1 - 1e-5) or (n[0] < -0.999 and max(xs) < x0 + 1e-5) or
                  (n[1] > 0.999 and min(ys) > y1 - 1e-5) or (n[1] < -0.999 and max(ys) < y0 + 1e-5))
            if on:
                f.mat, f.uv = "section", "world"
    return faces_solids


def T(mx, my, mz):
    return (mx, my, mz)


# =================================================================== ROOF (level 2)
Z2 = 2 * H
BANDS = [  # (d0, d1, z0, z1): edge chamfer, lip, lower slope, upper slope (4 cm riser at d 0.52), frame
    (0.00, 0.04, -0.04, 0.000),
    (0.04, 0.15, 0.000, 0.000),
    (0.15, 0.52, 0.000, 0.360),
    (0.52, 0.95, 0.400, 0.714),
    (0.95, 9.00, 0.714, 0.714),
]
FRAME_CAP = 0.744       # frame stands 3 cm proud of the plateau field (the field reads recessed, as in the composite)
FIELD_Z = 0.714         # 056 terrainHeight -7 (7 voxels)
FIELD_SLAB = 0.10


def roof_dist(mx, my):
    """Linear distance function (a, b, c): d = a*X + b*Y + c measured inward from the hull outline, for a bevel tile."""
    a = {3: (1, 0, -5), 6: (-1, 0, 13)}.get(mx)       # X - 5 | 13 - X
    c = {9: (0, -1, -17), 15: (0, 1, 31)}.get(my)     # -17 - Y | Y + 31
    if mx in (3, 6) and my in (9, 15):
        return (a[0] + c[0], a[1] + c[1], a[2] + c[2] - 2)
    if mx in (3, 6):
        return a
    return c


def _field_side(mx, my):
    """Tile boundary sides (xn xp yn yp) of a bevel tile that face the recessed plateau field."""
    s = set()
    if mx == 3 and 10 <= my <= 14: s.add("xp")
    if mx == 6 and 10 <= my <= 14: s.add("xn")
    if my == 9 and mx in (4, 5): s.add("yn")
    if my == 15 and mx in (4, 5): s.add("yp")
    return s


def roof_bevel(mx, my):
    a, b, c = roof_dist(mx, my)
    x0, x1, y0, y1 = 2 * mx - 1, 2 * mx + 1, -2 * my - 1, -2 * my + 1
    sq = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    foot = clip_poly2(sq, -a, -b, c)                   # d >= 0
    dist = lambda x, y: a * x + b * y + c
    solids = []
    fside = _field_side(mx, my)
    last = len(BANDS) - 1
    # along-edge coordinate for the transverse straps
    g = math.hypot(a, b)
    e = (-b / g, a / g)
    cx, cy = 2 * mx, -2 * my
    s_of = lambda x, y: (x - cx) * e[0] + (y - cy) * e[1]
    corner = mx in (3, 6) and my in (9, 15)
    strap_at = (-0.72, 0.72) if corner else (-1.0, 0.0, 1.0)
    for bi, (d0, d1, z0, z1) in enumerate(BANDS):
        poly = clip_poly2(clip_poly2(foot, -a, -b, c - d0), a, b, d1 - c)
        if len(poly) < 3 or abs(sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly)))) < 1e-6:
            continue
        if bi == last:
            ztop = Z2 + FIELD_Z
        else:
            ztop = (lambda x, y, d0=d0, d1=d1, z0=z0, z1=z1: Z2 + z0 + (dist(x, y) - d0) * (z1 - z0) / (d1 - d0))
        poly = ccw(poly)
        side_mats = []
        for i in range(len(poly)):
            p, q = poly[i], poly[(i + 1) % len(poly)]
            dp, dq = dist(*p), dist(*q)
            if abs(dp - d0) < 1e-6 and abs(dq - d0) < 1e-6:          # band's outer boundary
                side_mats.append("hull" if (bi == 0 or z0 > BANDS[bi - 1][3] + 1e-6) else None)   # outline / riser
            elif abs(dp - d1) < 1e-6 and abs(dq - d1) < 1e-6:        # band's inner boundary (hidden)
                side_mats.append(None)
            else:
                side_mats.append("hull")
        s = prism(poly, Z2 + SLAB, ztop, "hull", top_mat=("hulldark" if z1 > z0 + 0.05 else "hull"),
                  side_mats=side_mats, name=f"roof band {bi}")
        # outline face (d = 0) is exterior hull even though it lies on a tile plane for edge tiles
        for f in s.faces:
            if f.tag == "side":
                ds = [dist(p[0], p[1]) for p in f.pts]
                if max(abs(v) for v in ds) < 1e-6:
                    f.tag = "keep"
        solids.append(s)
        # transverse straps across the sloped bands (the sprites' alternating light / dark slope panels)
        if z1 > z0 + 0.05:
            for k in strap_at:
                for w in (0.055,):
                    sp = clip_poly2(clip_poly2(poly, e[0], e[1], k + w + cx * e[0] + cy * e[1]),
                                    -e[0], -e[1], -(k - w + cx * e[0] + cy * e[1]))
                    if len(sp) < 3:
                        continue
                    st = prism(sp, Z2 + z0 - 0.02 + 0.0, (lambda x, y, f_=ztop: f_(x, y) + 0.03), "hull", name="slope strap")
                    st.faces = [f for f in st.faces if f.tag != "bottom"]
                    keep(st)
                    solids.append(st)
        if bi == last:
            # 3 cm frame cap; sides on the field boundary are visible steps (hull), others are cuts
            cap = prism(poly, Z2 + FIELD_Z, Z2 + FRAME_CAP, "hull", name="roof frame cap")
            for f in cap.faces:
                if f.tag == "bottom":
                    f.mat = None
            cap.faces = [f for f in cap.faces if f.mat is not None]
            for f in cap.faces:
                n = f.normal()
                side = ("xp" if n[0] > 0.99 else "xn" if n[0] < -0.99 else "yp" if n[1] > 0.99 else "yn" if n[1] < -0.99 else "")
                if side in fside:
                    f.tag = "keep"
            solids.append(cap)
    return solids


def field_ribs(mx, my, ztop):
    """Light raised ribs of the panel grid: centre cross + half ribs on all four tile edges (identical on every tile)."""
    """P008: one X brace corner to corner over the whole 2 m tile (light rib with a shadow side) inside a light
    rim inset ~0.13 m from the tile edges; the xpanel texture carries the same motif at 2 m per tile."""
    x0, x1, y0, y1 = 2 * mx - 1, 2 * mx + 1, -2 * my - 1, -2 * my + 1
    xc, yc = 2 * mx, -2 * my
    s = []
    L, w = 1.5, 0.05
    for k, (dx, dy) in enumerate(((1, 1), (1, -1))):
        U = (dx / math.sqrt(2), dy / math.sqrt(2), 0.0)
        V = (-U[1], U[0], 0.0)
        hgt = 0.050 + 0.005 * k
        br = extrude([(-L, -w), (L, -w), (L, w), (-L, w)], (xc, yc, ztop - 0.01), U, V, (0, 0, 1), 0.0, hgt + 0.01,
                     "hull", name="x brace")
        br.cap_mat = "hull"      # its ends are cut at the tile corners and continue in the neighbour: no lilac specks
        s.append(br)
    ri, rw, rh = 0.13, 0.06, 0.040
    s += [box(x0 + ri, x1 - ri, y0 + ri, y0 + ri + rw, ztop - 0.01, ztop + rh, "hull", name="rim s"),
          box(x0 + ri, x1 - ri, y1 - ri - rw, y1 - ri, ztop - 0.01, ztop + rh, "hull", name="rim n"),
          box(x0 + ri, x0 + ri + rw, y0 + ri + rw, y1 - ri - rw, ztop - 0.01, ztop + rh, "hull", name="rim w"),
          box(x1 - ri - rw, x1 - ri, y0 + ri + rw, y1 - ri - rw, ztop - 0.01, ztop + rh, "hull", name="rim e")]
    # centre boss where the braces cross, and corner bolts
    boss = extrude([(0.09 * math.cos(a), 0.09 * math.sin(a)) for a in [i * math.pi / 4 + math.pi / 8 for i in range(8)]],
                   (xc, yc, ztop), (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.0, 0.05, "steel", name="brace boss")
    s.append(boss)
    for bx, by in ((x0 + ri + rw / 2, y0 + ri + rw / 2), (x1 - ri - rw / 2, y0 + ri + rw / 2),
                   (x0 + ri + rw / 2, y1 - ri - rw / 2), (x1 - ri - rw / 2, y1 - ri - rw / 2)):
        s.append(box(bx - 0.04, bx + 0.04, by - 0.04, by + 0.04, ztop, ztop + 0.055, "steel", name="corner bolt"))
    return s


def roof_field(mx, my):
    x0, x1, y0, y1 = 2 * mx - 1, 2 * mx + 1, -2 * my - 1, -2 * my + 1
    z = Z2 + FIELD_Z
    slab = box(x0, x1, y0, y1, z - FIELD_SLAB, z, "hull", mats={"zp": "xpanel"}, name="plateau field plate")
    return [slab] + field_ribs(mx, my, z)


def cockpit_roof(mx, my):
    x0, x1, y0, y1 = 2 * mx - 1, 2 * mx + 1, -2 * my - 1, -2 * my + 1
    z = Z2
    slab = box(x0, x1, y0, y1, z + SLAB, z, "hull", mats={"zp": "xpanel"}, name="cockpit roof plate")
    for f in slab.faces:      # craft outline faces (over the cockpit walls / the windscreen) stay hull
        n = f.normal()
        if (mx == 4 and n[0] < -0.99) or (mx == 5 and n[0] > 0.99) or (my == 17 and n[1] < -0.99):
            f.tag = "keep"
    return [slab] + field_ribs(mx, my, z)


# =================================================================== NOSE (level 1)
Z1 = H
NOSE_Y = -37.75          # nose front face (block 0.75 m deep, P010 / P009 east face width)
NOSE_TOP = 16 * H / 24   # 16 voxels (LOFT layers 0-7)
BAND_Z = (0.22, 0.66)    # yellow nose band on the front face
NOSE_SPAN = (6.5, 11.5)  # front face X span (posts + block)


def band_uv_faces(solid, z0, z1):
    """Map band faces (all but top/bottom) into the noseband decal: south faces by world X over the nose span,
    other faces by their own extents as a matching slice (keeps the stripe scale)."""
    rect = MD.cell_uv(MD.DECAL["noseband"])
    span = NOSE_SPAN[1] - NOSE_SPAN[0]
    for f in solid.faces:
        n = f.normal()
        if abs(n[2]) > 0.5:
            f.mat = "yellow"
            continue
        f.mat = "trim"
        t0, t1, b0, b1 = bounds_tb(f.pts, n)
        if n[1] < -0.99:
            f.uv = ("rect", rect, (NOSE_SPAN[0], NOSE_SPAN[1], Z1 + z0, Z1 + z1))
        else:
            f.uv = ("rect", rect, (t0, t0 + span, Z1 + z0, Z1 + z1))
    return solid


def nose_post_009():
    """[3,19] NE corner: 0.5 m wide post closing the nose front at the left, outer front edge chamfered,
    yellow band wrapped round it; its east face (X = 7, next to 010) is a cut."""
    x0, x1, y0, y1 = 6.5, 7.0, NOSE_Y, -37.0
    zb, zt = Z1 + SLAB, Z1 + NOSE_TOP
    body = box(x0, x1, y0, y1, zb, zt, "hull", name="nose post 009")
    ch = 0.20
    body = clip_solid(body, unit((-1, -1, 0)), dot(unit((-1, -1, 0)), (x0 + ch, y0, 0)), cap_mat="hull")
    # bevel along the top outer edges (west and front) like the nose block shoulders
    body = clip_solid(body, unit((0, -1, 1.2)), dot(unit((0, -1, 1.2)), (0, y0, zt - 0.14)), cap_mat="hull")
    body = clip_solid(body, unit((-1, 0, 1.2)), dot(unit((-1, 0, 1.2)), (x0, 0, zt - 0.14)), cap_mat="hull")
    # lower front chamfer toward the belly
    body = clip_solid(body, unit((0, -1, -1)), dot(unit((0, -1, -1)), (0, y0, zb + 0.16)), cap_mat="hull")
    for f in body.faces:
        if f.mat == "hull" and f.normal()[0] < -0.99:
            f.mat = "hull"
    band = box(x0 - 0.012, x1, y0 - 0.012, y1 - 0.2, Z1 + BAND_Z[0], Z1 + BAND_Z[1], "trim", name="nose band 009")
    band = clip_solid(band, unit((-1, -1, 0)), dot(unit((-1, -1, 0)), (x0 + ch, y0 - 0.012, 0)) + 0.012 * 0.0, cap_mat="trim")
    band_uv_faces(band, *BAND_Z)
    # small amber running light on the chamfered corner, under the band
    lamp = box(x0 + 0.02, x0 + 0.12, y0 + 0.02, y0 + 0.12, Z1 + 0.80, Z1 + 0.86, "amber", name="corner lamp")
    lamp = clip_solid(lamp, unit((-1, -1, 0)), dot(unit((-1, -1, 0)), (x0 + ch, y0, 0)) + 0.02, cap_mat="amber")
    return [body, band] + ([lamp] if lamp else [])


# =================================================================== registry
# records whose single model also serves outline positions: tile-plane faces stay hull
NO_AUTO_SECTION = {8, 56}   # their sprites show plain plates (no cut faces)


def record_solids(rec):
    """-> (canonical tile, [solids in craft coordinates])"""
    if rec in (0, 1, 2, 3, 4, 5, 6, 7):
        (mx, my, mz), _ = PLACEMENTS[rec][0]
        if rec in (2, 3):
            mx, my, mz = (6 if rec == 2 else 3), 12, 2
        return (mx, my, mz), roof_bevel(mx, my)
    if rec == 56:
        return (4, 12, 2), roof_field(4, 12)
    if rec == 8:
        return (4, 16, 2), cockpit_roof(4, 16)
    if rec == 9:
        return (3, 19, 1), nose_post_009()
    raise KeyError(rec)


def record_faces(rec):
    tile, solids = record_solids(rec)
    solids = [s for s in solids if s is not None]
    if rec not in NO_AUTO_SECTION:
        auto_section(solids, tile)
    return tile, solids
