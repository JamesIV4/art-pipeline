"""Example build script, yard_common style (blob, lathe, cull_hidden, finish).
Origin: S:/Repos/trick-or-treat/art/team/yard_street/batch02/build_bush_pot.py (copied 2026-10-25). Changed: the kit import points at
<pipeline>/kits/lowpoly. Run from the trick-or-treat root (palette/materials/catalog live there):
  cd S:/Repos/trick-or-treat
  blender --background --factory-startup --python <this file> [-- ids...]
It exports into the game's models folder, so only run it against a game you mean to change.

bush_round and flower_pot (v2)."""
import pathlib
import sys

import os
sys.path.insert(0, os.path.join(os.environ.get("ART_PIPELINE", r"S:/Repos/art-pipeline"), "kits", "lowpoly"))  # was: this batch folder
from yard_common import *  # noqa: E402,F401,F403
import bmesh  # noqa: E402


def sit_on_ground(ob, z=0.0):
    """Clamp everything below z up onto the plane and delete faces lying flat on it (never seen)."""
    for v in ob.data.vertices:
        if v.co.z < z:
            v.co.z = z
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    dead = [f for f in bm.faces if all(abs(v.co.z - z) < 1e-5 for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def bush_round():
    K.reset()
    spec = [  # radius, loc, scale, segments, rings
        (0.46, (0.0, 0.02, 0.3), (1.05, 1.0, 0.92), 14, 9),
        (0.3, (0.3, -0.2, 0.24), (1.0, 1.0, 0.95), 12, 8),
        (0.3, (-0.33, -0.08, 0.24), (1.0, 1.0, 0.95), 12, 8),
        (0.28, (0.12, 0.3, 0.26), (1.0, 1.0, 0.95), 11, 7),
        (0.25, (-0.08, -0.3, 0.2), (1.0, 1.0, 0.95), 11, 7),
        (0.24, (0.05, 0.02, 0.66), (1.0, 1.0, 0.9), 11, 7),
        (0.27, (-0.25, 0.25, 0.27), (1.0, 1.0, 0.95), 11, 7),
        (0.22, (0.33, 0.12, 0.42), (1.0, 1.0, 0.95), 10, 7),
    ]
    parts = []
    for i, (r, loc, scl, seg, rings) in enumerate(spec):
        b = blob(f"lump{i}", r, "hedge", mat="hedge", loc=loc, scale=scl, segments=seg, rings=rings, lobes=6,
                 lobe_amp=0.16, lobe_pow=4.0, noise_amp=0.05, noise_freq=2.0, seed=7 + i * 3, axis="X", uvmode="box")
        parts.append(b)
    cull_hidden(parts, zmin=0.02)
    for b in parts:
        sit_on_ground(b)
        paint_world(b, "hedge_dark", lambda c, n: n.z < -0.35 or c.z < 0.1)
    bush = K.merge(parts, "bush_round")
    return finish([bush], "props/bush_round", "bush_round", ao_radius=0.5)


def flower_pot():
    K.reset()
    T, C = "terracotta", "clay"
    # tapered pot with a rolled rim; inner wall down to the soil
    prof = [(0.0, 0.0), (0.15, 0.0), (0.162, 0.012), (0.2, 0.24), (0.206, 0.255), (0.24, 0.262), (0.252, 0.285),
            (0.252, 0.325), (0.24, 0.345), (0.222, 0.342), (0.214, 0.31)]
    cols = [C, C, T, C, T, T, T, T, T, "clay"]
    mats = ["stucco"] * 10
    pot = lathe("pot", prof, cols, mats, segments=14, cap_bottom=False, cap_top=False, phase=0.2)
    soil = lathe("soil", [(0.214, 0.31), (0.12, 0.318), (0.0, 0.322)], "choco_dark", "soil", segments=14,
                 cap_bottom=False, cap_top=False, phase=0.2)
    parts = [pot, soil]
    mums = [
        (0.17, (-0.06, -0.06, 0.38), "maple_orange", 2),
        (0.15, (0.12, 0.03, 0.37), "golden_leaf", 5),
        (0.14, (-0.03, 0.13, 0.39), "maple_orange", 8),
    ]
    blobs = []
    for i, (r, loc, col, sd) in enumerate(mums):
        b = blob(f"mum{i}", r, col, mat="hedge", loc=loc, scale=(1.0, 1.0, 0.85), segments=12, rings=7, lobes=14,
                 lobe_amp=0.09, lobe_pow=8.0, noise_amp=0.04, noise_freq=4.0, seed=sd, axis="Z", uvmode="box")
        blobs.append(b)
    cull_hidden(blobs)
    for b in blobs:
        cut_below(b, 0.318, cap_color="hedge_dark", cap_mat="hedge")
        paint_world(b, "rust_leaf" if "orange" in b.name or True else "", lambda c, n: n.z < -0.45)
    parts += blobs
    # leaves fanning over the rim
    for i, (a, tilt) in enumerate([(25, 28), (100, 34), (170, 26), (235, 32), (300, 30), (345, 24)]):
        ar = math.radians(a)
        leaf = blob(f"leaf{i}", 0.075, "hedge", mat="flat", scale=(1.5, 1.0, 0.3), segments=6, rings=4,
                    noise_amp=0.0, axis="X")
        transform(leaf, loc=(math.cos(ar) * 0.2, math.sin(ar) * 0.2, 0.355), rot=(0, -tilt, a))
        paint_world(leaf, "vine_dark", lambda c, n: n.z < 0)
        parts.append(leaf)
    ob = K.merge(parts, "flower_pot")
    return finish([ob], "props/flower_pot", "flower_pot", ao_radius=0.25)


if want("bush_round"):
    bush_round()
if want("flower_pot"):
    flower_pot()
