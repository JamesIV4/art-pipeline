"""Example build script, farm_lib style (themed bodies, drape, tendrils).
Origin: S:/Repos/trick-or-treat/art/team/pumpkins_farm/batch02/build_pumpkins.py (copied 2026-10-25). Changed: the kit import points at
<pipeline>/kits/lowpoly. Run from the trick-or-treat root (palette/materials/catalog live there):
  cd S:/Repos/trick-or-treat
  blender --background --factory-startup --python <this file> [-- ids...]
It exports into the game's models folder, so only run it against a game you mean to change.

pumpkin_round, pumpkin_tall, pumpkin_small, gourd_cluster (batch02, textured).

blender --background --factory-startup --python art/team/pumpkins_farm/batch02/build_pumpkins.py [-- ids...]
"""
import math
import pathlib
import sys

import os
sys.path.insert(0, os.path.join(os.environ.get("ART_PIPELINE", r"S:/Repos/art-pipeline"), "kits", "lowpoly"))  # was: this batch folder
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import farm_lib as F  # noqa: E402

K = F.K


def upd():
    bpy.context.view_layer.update()


def pumpkin_round():
    K.reset()
    body = F.pumpkin_body("body", width=0.62, height=0.45, lobes=8, spl=5, rings=13, groove=0.13, plump=0.45,
                          fullness=0.7, flatness=0.75, top_dimple=0.07, dimple_w=0.42, lumps=0.045, seed=3,
                          twist=0.12, lopsided=0.03, lop_dir=1.0, belly=1.2, lobe_h=0.03, rot_z=-90 + 22.5)
    upd()
    top = F.top_point(body)
    parts = [body]
    parts.append(F.stem("stem", top, height=0.17, radius=0.04, curl=0.12, lean_dir=math.radians(200),
                        color="stem_brown", rings=8))
    # curly vine tendril springing from the stem base
    parts.append(F.tendril("curl", (top.x + 0.1, top.y - 0.05, top.z + 0.07), turns=1.7, r0=0.045, r1=0.014,
                           rise=-0.05, n=14, radius=0.008, axis="x", phase=math.pi,
                           lead=(top.x + 0.02, top.y - 0.01, top.z + 0.02)))
    # one leaf resting on the shoulder
    leaf = F.pumpkin_leaf("leaf", size=0.13, color="vine", lobes=5, n=24, cup=0.0, corrugate=0.12,
                          vein_color="vine_dark")
    a = math.radians(-35)
    F.drape(leaf, body, top.x + math.cos(a) * 0.17, top.y + math.sin(a) * 0.17, -35, lift=0.008)
    parts.append(leaf)
    ob = K.merge(parts, "pumpkin_round")
    return F.finish([ob], "props/pumpkin_round", "pumpkin_round")


def pumpkin_tall():
    K.reset()
    body = F.pumpkin_body("body", width=0.5, height=0.6, lobes=8, spl=5, rings=14, groove=0.12, plump=0.45,
                          color="pumpkin_light", fullness=0.78, flatness=0.6, top_dimple=0.06, dimple_w=0.4,
                          lumps=0.04, seed=7, twist=-0.18, lean=(0.03, 0.0), belly=1.08, lobe_h=0.025,
                          rot_z=-90 + 22.5 + 8)
    upd()
    top = F.top_point(body)
    parts = [body]
    parts.append(F.stem("stem", top, height=0.2, radius=0.04, curl=0.08, lean_dir=math.radians(-30),
                        color="stem_green", rings=7))
    parts.append(F.tendril("curl", (top.x - 0.08, top.y + 0.05, top.z + 0.08), turns=1.5, r0=0.04, r1=0.013,
                           rise=0.05, n=12, radius=0.008, axis="x", phase=0.3,
                           lead=(top.x - 0.02, top.y + 0.01, top.z + 0.03)))
    ob = K.merge(parts, "pumpkin_tall")
    return F.finish([ob], "props/pumpkin_tall", "pumpkin_tall")


def pumpkin_small():
    K.reset()
    body = F.pumpkin_body("body", width=0.3, height=0.21, lobes=6, spl=5, rings=11, groove=0.15, plump=0.45,
                          color="pumpkin_dark", fullness=0.7, flatness=0.7, top_dimple=0.04, dimple_w=0.42,
                          bottom_dimple=0.008, lumps=0.05, seed=11, belly=1.2, rot_z=-90 + 30)
    upd()
    top = F.top_point(body)
    parts = [body]
    parts.append(F.stem("stem", top, height=0.12, radius=0.03, curl=0.04, lean_dir=math.radians(150),
                        color="stem_brown", rings=6, tip_ratio=0.9, flare=1.7, uv_scale=4.0))
    ob = K.merge(parts, "pumpkin_small")
    return F.finish([ob], "props/pumpkin_small", "pumpkin_small")


def gourd_cluster():
    K.reset()
    parts = []
    # mini white pumpkin, back left
    w = F.pumpkin_body("white", width=0.24, height=0.15, lobes=6, spl=4, rings=8, groove=0.14, plump=0.5,
                       color="gourd_white", fullness=0.6, flatness=0.7, top_dimple=0.03, bottom_dimple=0.006,
                       seed=5, loc=(-0.11, 0.08, 0))
    upd()
    t = F.top_point(w)
    parts.append(w)
    parts.append(F.stem("ws", t, height=0.06, radius=0.016, curl=0.02, lean_dir=1.0, color="stem_green",
                        rings=4, ridges=3, uv_scale=5.0))
    # striped pear gourd, standing at back right: yellow belly, green neck with cream stripes
    zs = [0.0, 0.025, 0.06, 0.1, 0.14, 0.175, 0.21, 0.24, 0.265, 0.285]
    radii = [0.045, 0.078, 0.094, 0.09, 0.072, 0.052, 0.042, 0.038, 0.034, 0.028]
    spine = [(0.12 + 0.12 * max(0.0, z - 0.12) ** 1.2, 0.09 + 0.04 * max(0.0, z - 0.12), z) for z in zs]
    pear = F.sweep("pear", spine, radii, sides=10, color="gourd_green", mat="pumpkin", cap_start=True,
                   cap_end=True, cap_offset=0.3, rib=0.125,
                   side_colors=["candy_corn_white", "candy_corn_white", None, None], side_from=3)
    K.paint(pear, "gourd_yellow", where=lambda c, n: c.z < 0.085)
    parts.append(pear)
    parts.append(F.stem("ps", (0.15, 0.101, 0.28), height=0.05, radius=0.013, curl=0.025, lean_dir=0.4,
                        color="stem_brown", rings=4, ridges=3, uv_scale=5.0, sink=0.01))
    # yellow crookneck lying in front, with a warty bulb and a curved neck
    spine = [(-0.2, -0.1, 0.075), (-0.15, -0.115, 0.08), (-0.08, -0.125, 0.082), (-0.02, -0.125, 0.08),
             (0.03, -0.12, 0.09), (0.06, -0.115, 0.12), (0.065, -0.118, 0.16), (0.05, -0.125, 0.195),
             (0.03, -0.13, 0.21)]
    radii = [0.03, 0.07, 0.085, 0.072, 0.05, 0.036, 0.03, 0.026, 0.02]
    crook = F.sweep("crook", spine, radii, sides=10, color="gourd_yellow", mat="pumpkin", cap_offset=0.4,
                    rib=0.125)
    parts.append(crook)
    for i, (x, y, z) in enumerate(((-0.14, -0.18, 0.1), (-0.08, -0.2, 0.13), (-0.11, -0.12, 0.155))):
        parts.append(K.sphere(f"cw{i}", 0.014, color="candy_corn_yellow", mat="flat", segments=5, rings=3,
                              loc=(x, y + 0.01, z)))
    parts.append(F.stem("cs", (0.03, -0.13, 0.21), height=0.04, radius=0.012, curl=0.02, lean_dir=3.0,
                        color="stem_green", rings=4, ridges=3, uv_scale=5.0, sink=0.008))
    # warty green gourd, front right
    wart = F.pumpkin_body("warty", width=0.17, height=0.15, lobes=5, spl=4, rings=8, groove=0.1, plump=0.6,
                          color="gourd_green", fullness=0.85, flatness=0.9, top_dimple=0.01,
                          bottom_dimple=0.004, seed=8, loc=(0.16, -0.08, 0))
    parts.append(wart)
    for i, (ax, az) in enumerate([(-40, 25), (30, 40), (-100, 50), (80, 20), (170, 35), (-150, 15)]):
        a, e = math.radians(ax - 90), math.radians(az)
        c = (0.16 + math.cos(a) * math.cos(e) * 0.08, -0.08 + math.sin(a) * math.cos(e) * 0.08,
             0.075 + math.sin(e) * 0.07)
        parts.append(K.sphere(f"wart{i}", 0.018, color="olive", mat="flat", segments=5, rings=3, loc=c))
    upd()
    t = F.top_point(wart)
    parts.append(F.stem("gs", t, height=0.05, radius=0.014, curl=0.02, lean_dir=2.0, color="stem_green",
                        rings=4, ridges=3, uv_scale=5.0))
    # a leaf tucked under the cluster
    leaf = F.pumpkin_leaf("leaf", size=0.13, color="vine", lobes=5, n=18, cup=0.15, corrugate=0.08,
                          vein_color="sage_leaf")
    F.place(leaf, loc=(0.02, 0.18, 0.012), rot=(0, 0, 70))
    parts.append(leaf)
    ob = K.merge(parts, "gourd_cluster")
    F.drop_to_ground(ob)
    return F.finish([ob], "props/gourd_cluster", "gourd_cluster")


if __name__ == "__main__":
    F.run({f.__name__: f for f in (pumpkin_round, pumpkin_tall, pumpkin_small, gourd_cluster)})
