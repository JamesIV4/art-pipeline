"""Origin: S:/Repos/trick-or-treat/art/team/vines/batch03/vine_kit.py (imported 2026-10-25).
Changed: sys.path inserts now point at kits/lowpoly (all kits live side by side; lowpoly_kit
resolves game paths through tools/pipeline_paths.py). Logic unchanged.

Lane helpers for vines / batch03 (thorn vine knots + thorn root mass), lowpoly_kit v2 textured.

Reuses the monsters/batch03 helper library read-only (mon_kit -> farm_lib + dk_kit + lowpoly_kit):
  M.catmull / M.blob / M.band_lathe / M.put / M.part / M.clip_below / M.nest_finish
  F.sweep (tubes with twist + side colours + lobed profile) / F.blade (leaves) / F._frames

Coordinates: Blender, Z up, front = -Y (glTF/Godot +Z). Origins at the ground centre.
Look: dark-green bark stems (vine_dark with a twisting vine / hedge_dark stripe), bone-white
spines (lolly_white shaft, cream tip) that point outward so they read as white silhouettes.
"""
from __future__ import annotations

import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
# art-pipeline port: was `ROOT = HERE.parents[3]` (game root, only used for sys.path)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # art-pipeline: kits/lowpoly holds every kit

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import mon_kit as M  # noqa: E402

F, D, K = M.F, M.D, M.K
V = Vector
TAU = math.tau
FLAGS = M.FLAGS

STRIPES = ("vine", None, None, "pine_deep", None, None, None)


# ---------------------------------------------------------------- paths
def arclen(pts):
    out = [0.0]
    for i in range(1, len(pts)):
        out.append(out[-1] + (pts[i] - pts[i - 1]).length)
    return out


def smooth(ctrl, per=3):
    return [V(p) for p in M.catmull([V(c) for c in ctrl], per)]


def curl(p0, t, nrm, R0, turns=1.1, n=9, shrink=0.78):
    """Fiddlehead spiral continuing from p0 (heading t), curling toward nrm. Excludes p0."""
    t = V(t).normalized()
    nrm = V(nrm)
    nrm = (nrm - t * nrm.dot(t)).normalized()
    c = V(p0) + nrm * R0
    total = turns * TAU
    out = []
    for k in range(1, n + 1):
        phi = total * k / n
        R = R0 * (1 - shrink * phi / total)
        out.append(c + (-nrm * math.cos(phi) + t * math.sin(phi)) * R)
    return out


def with_curl(ctrl, nrm, R0, turns=1.1, n=9, per=3, shrink=0.78):
    pts = smooth(ctrl, per)
    t = (pts[-1] - pts[-2]).normalized()
    return pts + curl(pts[-1], t, nrm, R0, turns, n, shrink)


def wobble(pts, amp, wave=3.2, phase=0.0, fade_in=0.0):
    """Corkscrew the path around itself (amp metres, wave radians per metre)."""
    fr = F._frames(pts)
    arc = arclen(pts)
    out = []
    for p, (t, side, up), s in zip(pts, fr, arc):
        a = amp * (min(1.0, s / fade_in) if fade_in else 1.0)
        out.append(p + (side * math.cos(s * wave + phase) + up * math.sin(s * wave + phase)) * a)
    return out


def sample(pts, radii, s):
    """Point, radius, segment index at arc length s."""
    arc = arclen(pts)
    i = 0
    while i < len(pts) - 2 and arc[i + 1] < s:
        i += 1
    seg = max(arc[i + 1] - arc[i], 1e-6)
    f = min(max((s - arc[i]) / seg, 0.0), 1.0)
    return pts[i].lerp(pts[i + 1], f), radii[i] + (radii[i + 1] - radii[i]) * f, i


# ---------------------------------------------------------------- stems
def taper(pts, r0, r1, power=1.0, swell=None):
    arc = arclen(pts)
    tot = max(arc[-1], 1e-6)
    out = []
    for s in arc:
        u = s / tot
        r = r0 + (r1 - r0) * u ** power
        if swell:
            r *= swell(u)
        out.append(r)
    return out


def stem(name, pts, r0, r1, sides=7, color="hedge_dark", mat="bark", twist=0.3, stripes=STRIPES,
         profile=None, power=0.8, cap=0.8, radii=None, swell=None):
    """Tapered bark tube. Returns (object, points, radii)."""
    pts = [V(p) for p in pts]
    if radii is None:
        radii = taper(pts, r0, r1, power, swell)
    ob = F.sweep(name, pts, radii, sides=sides, color=color, mat=mat, twist=twist, side_colors=stripes,
                 profile=profile, cap_offset=cap)
    return ob, pts, radii


def rope(j, sides=9, lobes=3):
    """Lobed cross-section multiplier: twisted with the sweep it reads as a rope of strands."""
    k = j % (sides // lobes)
    return (1.0, 0.9, 0.74)[k] if sides // lobes == 3 else (1.0 if k == 0 else 0.8)


# ---------------------------------------------------------------- spines
class Spines:
    """All spines of an asset in one bmesh: 5-sided soft cones, lolly_white shaft, cream tip,
    open base (always buried in a stem). 30 tris each (25 for small ones)."""

    SIDES = 6
    SMALL = 0.3   # spines shorter than this get 5 sides (25 tris)

    def __init__(self, shaft="trim_white", tip="cream", mat="flat"):
        self.bm = bmesh.new()
        self.shaft, self.tip, self.mat = shaft, tip, mat
        self.shaft_faces, self.tip_faces = [], []
        self.count = 0

    def add(self, base, d, length, r=None, hook=None, hook_amt=0.12):
        d = V(d).normalized()
        r = r if r is not None else length * 0.3
        h = length
        hk = V(hook) if hook is not None else V((0, 0, 1))
        hk = hk - d * hk.dot(d)
        if hk.length < 1e-4:
            hk = d.orthogonal()
        hk.normalize()
        x = hk.cross(d).normalized()
        prof = [(r, -0.3 * r), (r * 0.7, 0.38 * h), (r * 0.3, 0.74 * h), (0.0, h)]
        n = self.SIDES if length >= self.SMALL else 5
        rings = []
        for rr, z in prof:
            bend = hook_amt * h * max(z / h, 0.0) ** 2
            c = V(base) + d * z + hk * bend
            if rr < 1e-6:
                rings.append([self.bm.verts.new(c)])
            else:
                rings.append([self.bm.verts.new(c + (x * math.cos(TAU * j / n + 0.3) +
                                                      hk * math.sin(TAU * j / n + 0.3)) * rr)
                              for j in range(n)])
        for i in range(len(rings) - 1):
            A, B = rings[i], rings[i + 1]
            for j in range(n):
                j2 = (j + 1) % n
                if len(B) == 1:
                    f = self.bm.faces.new((A[j], A[j2], B[0]))
                else:
                    f = self.bm.faces.new((A[j], A[j2], B[j2], B[j]))
                f.normal_update()
                cen = f.calc_center_median()
                ax = V(base) + d * (cen - V(base)).dot(d)
                if f.normal.dot(cen - ax) < 0:
                    f.normal_flip()
                (self.tip_faces if i == 2 else self.shaft_faces).append(f)
        self.count += 1

    def build(self, name="spines"):
        bm = self.bm
        bm.normal_update()
        K._project_bm(bm, "box")
        K._paint_bm(bm, self.shaft, self.mat, self.shaft_faces)
        K._paint_bm(bm, self.tip, self.mat, self.tip_faces)
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        return K._link(bpy.data.objects.new(name, me))


def spines_on(S, pts, radii, rng, every=(0.24, 0.36), start=0.25, end=0.97, size=(2.3, 3.3), min_len=0.13,
              max_len=0.9, out_fn=None, up_bias=0.25, skip=None, embed=0.3, golden=2.39996, hook_amt=0.12):
    """Scatter spines along a stem. out_fn(p) -> Vector bias (outward direction). skip(p, d, L) -> bool."""
    fr = F._frames(pts)
    arc = arclen(pts)
    total = arc[-1]
    s = start + rng.uniform(0, every[1] * 0.5)
    k = rng.uniform(0, TAU)
    while s < total * end:
        p, r, i = sample(pts, radii, s)
        t, side, up = fr[i]
        k += golden + rng.uniform(-0.35, 0.35)
        d = side * math.cos(k) + up * math.sin(k)
        if out_fn:
            d = d + out_fn(p)
        d = d + V((0, 0, up_bias))
        d = d - t * d.dot(t) * 0.85
        if d.length < 1e-4:
            s += rng.uniform(*every)
            continue
        d.normalize()
        if d.z < -0.25 and p.z < 0.7:
            d.z = abs(d.z) * 0.5
            d.normalize()
        L = min(max_len, max(min_len, r * rng.uniform(*size)))
        if skip and skip(p, d, L):
            s += rng.uniform(*every)
            continue
        perp = (d - t * d.dot(t))
        perp = perp.normalized() if perp.length > 1e-4 else d
        S.add(p + perp * r * embed, d, L, hook=t, hook_amt=hook_amt)
        s += rng.uniform(*every)


# ---------------------------------------------------------------- leaves, buds
def leaf(name, p, d, nrm, size=0.3, color="vine", under="hedge_dark"):
    d = V(d).normalized()
    nrm = V(nrm)
    nrm = (nrm - d * nrm.dot(d)).normalized()
    p = V(p)
    pts = [p, p + d * 0.14 * size + nrm * 0.03 * size, p + d * 0.55 * size, p + d * size - nrm * 0.18 * size]
    widths = [0.05 * size, 0.5 * size, 0.42 * size, 0.0]
    return F.blade(name, pts, widths, thick=0.035 * size, color=color, mat="leaves", up=nrm, under_color=under)


def bud(name, p, d, r=0.11, sepal="vine"):
    """Small glowing purple bud cupped by three little sepals, sitting on p and pointing along d."""
    d = V(d).normalized()

    def seed(c):
        if c.z > 0:
            k = 1 - 0.45 * c.z ** 1.5
            c = V((c.x * k, c.y * k, c.z))
        return c
    objs = [M.blob(name, (0, 0, 0), (r, r, r * 1.3), segs=8, rings=6, color="glow_purple", warp=seed)]
    D.put(objs[0], V(p) + d * r * 0.9, d)
    side = d.orthogonal().normalized()
    for k in range(3):
        a = TAU * k / 3
        q = Matrix.Rotation(a, 3, d) @ side
        c = M.cone(f"{name}_s{k}", r * 1.35, r * 0.42, segs=5, color=sepal, lo=True)
        D.put(c, V(p) + d * r * 0.25 + q * r * 0.35, (d * 0.9 + q * 0.75).normalized())
        objs.append(c)
    return objs


# ---------------------------------------------------------------- roots
def ground_root(name, ang, L, r0, rng, z0=0.26, rise=0.1, sides=6, bend=None):
    """Root knotting from the base out and down into the ground (clipped at z = 0 later)."""
    dv = V((math.cos(ang), math.sin(ang), 0))
    sd = V((-math.sin(ang), math.cos(ang), 0))
    b = rng.uniform(-0.3, 0.3) if bend is None else bend
    ctrl = [dv * 0.12 + V((0, 0, z0)), dv * L * 0.35 + sd * b * L * 0.15 + V((0, 0, rise + 0.06)),
            dv * L * 0.7 + sd * b * L * 0.35 + V((0, 0, rise * 0.55)), dv * L + sd * b * L * 0.5 + V((0, 0, -0.22))]
    pts = smooth(ctrl, 2)
    return stem(name, pts, r0, r0 * 0.5, sides=sides, power=1.0, cap=0.3, twist=0.25)


def radial(k=0.6):
    def fn(p):
        h = V((p.x, p.y, 0))
        return h.normalized() * k if h.length > 1e-4 else V((0, 0, 0))
    return fn


# ---------------------------------------------------------------- finish
def finish_knot(objs, asset_id, ao_radius=0.55, ao_strength=0.85):
    return M.nest_finish(objs, asset_id, ao_radius=ao_radius, ao_strength=ao_strength)


def finish_parts(asset_id, roots_objs, heart_objs, heart_game, ao_radius=0.7, ao_strength=0.85):
    """Empty root '<asset_id>' with children 'roots' (origin = root, clipped at the ground) and
    'heart' (origin = heart_game, game coordinates). The heart's AO is baked on its own so the
    cage doesn't dim the glow core."""
    root = K.empty(asset_id, (0, 0, 0))
    roots = K.merge(roots_objs, "roots")
    M.clip_below(roots)
    heart = M.part(heart_objs, "heart", heart_game)
    D.attach(roots, root)
    D.attach(heart, root)
    for o in (roots, heart):
        F.cleanup(o)
    deg = F.degenerate_count([root])
    bpy.context.view_layer.update()
    lo = V((1e9, 1e9, 1e9))
    hi = V((-1e9, -1e9, -1e9))
    for o in (roots, heart):
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = V((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = V((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
    K.bake_ao([root], samples=32, radius=ao_radius, strength=ao_strength, ground=True)
    K.bake_ao([heart], samples=24, radius=0.4, strength=0.5, ground=False)
    import time
    root["build"] = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time() % 1:.4f}"
    out = K.export([root], f"monsters/{asset_id}")
    sh = K.review_sheet([root], asset_id) if "--nosheet" not in FLAGS else None
    tris = K.tri_count([root])
    size = hi - lo
    report = "; ".join(f"{o.name}:{D.tris(o)}@{M.b2g(o.matrix_world.translation)}" for o in (roots, heart))
    print(f"RESULT {asset_id} tris={tris} degenerate={deg} size(x,y_up,z)=({size.x:.2f},{size.z:.2f},{size.y:.2f}) "
          f"minz={lo.z:.3f} maxz={hi.z:.3f} parts=[{report}] gltf={out} sheet={sh}")
    return tris
