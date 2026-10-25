"""Origin: S:/Repos/trick-or-treat/art/team/landmarks/batch03/lm_common.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Shared helpers for the landmarks lane, batch03 (travel gate, shop cart, street-prop fidelity).

Reuses art/team/yard_street/batch02/yard_common.py (sweep, lathe, blob, rod, loft, box, paint_world,
finish ...) and adds:
  * stroke()      flat tapered ribbon (rune glyph strokes, painted swirls)
  * rock()        bevelled box with a noisy, hand-carved wobble (fieldstones, slabs)
  * sector_slab() bevelled annular-sector slab (round flagstones)
  * ribbed()      ribbed lathe-like body (pumpkins, gumdrops) built with sweep along Z
  * export_many() clean + joint AO bake over several assets + separate exports + sheets
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit
from yard_common import *  # noqa: E402,F401,F403
from yard_common import clean, ARGS  # noqa: E402,F401
import bmesh  # noqa: E402
import bpy  # noqa: E402


def ellipse(ax=1.0, ay=1.0):
    def f(i, a):
        return 1.0 / math.sqrt((math.cos(a) / ax) ** 2 + (math.sin(a) / ay) ** 2)
    return f


def stroke(name, pts, width, color, mat="flat", thick=0.012, taper=(0.45, 0.45), sides=6, z=None):
    """Flat ribbon through 2D/3D points lying (roughly) horizontal; tapered ends like a brush stroke."""
    P = [Vector((p[0], p[1], z if z is not None else p[2])) for p in pts]
    n = len(P)
    rad = []
    for i in range(n):
        t = i / max(n - 1, 1)
        k = 1.0
        if taper[0] and t < 0.3:
            k = taper[0] + (1 - taper[0]) * math.sin(t / 0.3 * math.pi / 2)
        if taper[1] and t > 0.7:
            k = min(k, taper[1] + (1 - taper[1]) * math.sin((1 - t) / 0.3 * math.pi / 2))
        rad.append(width / 2 * k)
    return sweep(name, P, rad, color=color, mat=mat, sides=sides, shape=ellipse(thick / width, 1.0),
                 up_hint=(0, 0, 1))


def rock(name, size, color, mat="stone", loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.04, segments=2, wobble=0.025,
         seed=0.0, freq=3.0):
    ob = box(name, size, color, mat, loc=loc, rot=rot, bevel=bevel, segments=segments)
    bake(ob)
    c = Vector(loc)

    def f(v):
        d = v - c
        return v + d.normalized() * wobble * nz(v.x * freq, v.y * freq, v.z * freq, seed) if d.length > 1e-6 else v
    deform(ob, f)
    reproject(ob, "box")
    return ob


def sector_slab(name, r0, r1, a0, a1, z0, z1, color, mat="pavers", bevel=0.015, n=6, top_color=None, segs=1):
    """Annular sector slab (angles in degrees), bevelled edges, flat top."""
    bm = bmesh.new()
    outline = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        outline.append((math.cos(a) * r1, math.sin(a) * r1))
    for k in range(n + 1):
        a = math.radians(a1 + (a0 - a1) * k / n)
        outline.append((math.cos(a) * r0, math.sin(a) * r0))
    bot = [bm.verts.new((x, y, z0)) for x, y in outline]
    top = [bm.verts.new((x, y, z1)) for x, y in outline]
    m = len(outline)
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # bevel only the top rim edges (+ vertical corner edges), the bottom is buried
    edges = [e for e in bm.edges if (all(abs(v.co.z - z1) < 1e-6 for v in e.verts))]
    corners = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6 and
               any(abs(math.hypot(v.co.x, v.co.y) - r) < 1e-5 for v in e.verts for r in (r0, r1)) and
               _is_corner(e, a0, a1)]
    bmesh.ops.bevel(bm, geom=edges + corners, offset=bevel, segments=segs, profile=0.5, affect="EDGES",
                    clamp_overlap=True)
    bm.normal_update()
    uv_box(bm, bm.faces)
    K._paint_bm(bm, color, mat)
    if top_color:
        K._paint_bm(bm, top_color, mat, [f for f in bm.faces if f.normal.z > 0.95])
    for f in bm.faces:
        f.smooth = f.normal.z < 0.95
    return new_obj(bm, name, None)


def _is_corner(e, a0, a1):
    v = e.verts[0].co
    a = math.degrees(math.atan2(v.y, v.x))
    for t in (a0, a1):
        d = (a - t + 180) % 360 - 180
        if abs(d) < 0.01:
            return True
    return False


def ribbed(name, radius, height, color, mat="pumpkin", ribs=8, depth=0.07, rings=7, sides=16, loc=(0, 0, 0),
           squash_top=0.25):
    """Ribbed round body (pumpkin): sweep up Z with a sphere-ish radius profile and cos(ribs*a) lobes."""
    pts, rad = [], []
    for i in range(rings + 1):
        t = i / rings
        th = math.pi * (0.06 + 0.88 * t)
        pts.append((loc[0], loc[1], loc[2] + height * (0.5 - 0.5 * math.cos(th)) / (0.5 - 0.5 * math.cos(math.pi * 0.94))))
        r = radius * math.sin(th) ** 0.8
        rad.append(max(r, radius * 0.12))

    def shape(i, a):
        return 1.0 + depth * (abs(math.cos(ribs * a / 2)) * 2 - 1)

    ob = sweep(name, pts, rad, color=color, mat=mat, sides=sides, shape=shape, up_hint=(1, 0, 0))
    return ob


def export_many(groups, ao_radius=0.8, ao_strength=0.9, sheet=True):
    """groups: [(objects, rel_path, asset_id)]. Cleans, bakes AO over ALL groups together (so a hanging
    part shades the base and vice versa), then exports and sheets each group separately."""
    alls = []
    for objs, _, _ in groups:
        for ob in objs:
            for o in [ob] + list(ob.children_recursive):
                clean(o)
            alls.append(ob)
    K.bake_ao(alls, samples=32, radius=ao_radius, strength=ao_strength, ground=True)
    res = {}
    for objs, rel, aid in groups:
        # hide the other groups from the sheet render
        others = [o for o in alls if o not in objs]
        for o in others:
            o.hide_render = True
            o.hide_set(True)
        out = K.export(objs, rel)
        tris = K.tri_count(objs)
        sh = K.review_sheet(objs, aid) if sheet else None
        for o in others:
            o.hide_render = False
            o.hide_set(False)
        print(f"ASSET {aid} tris={tris} gltf={out} sheet={sh}")
        res[aid] = tris
    return res
