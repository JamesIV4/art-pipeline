# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/assembly.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT)
"""AVENGER v2 assembly (Blender headless, read-only on exported glTFs).

Places every record at its AVENGER.MAP position (X = 2*mx, Y = -2*my, Z = mz*sqrt6), preferring opus-v2
glTFs from --models (trial dir) or the Godot folder, falling back to opus-v1 (labelled), and renders:
  * game camera: ortho az -45 el 30, framed pixel-for-pixel like the 4x sprite composite (inspect_v2.py)
  * three-quarter / roof / nose / engine perspective views.
blender --background --factory-startup --threads 2 --python assembly.py -- --out DIR [--models DIR] [--levels 0,1,2] [--tag t]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT  # noqa: E402
GAME = ROOT / "xcom-3d-godot/x-com--ufo-defense-3d/assets/models/terrain/AVENGER"
H = math.sqrt(6)
PX = 2 * math.sqrt(2) / 32


def cells():
    data = (ROOT / "reference/MAPS/AVENGER.MAP").read_bytes()
    sy, sx, sz = data[:3]
    nb = len((ROOT / "reference/TERRAIN/BLANKS.MCD").read_bytes()) // 62
    out = []
    for i in range(sx * sy * sz):
        pos = (i % sx, i // sx % sy, sz - 1 - i // (sx * sy))
        for part, v in enumerate(data[3 + i * 4:7 + i * 4]):
            if v >= nb:
                out.append((pos, part, v - nb))
    return (sx, sy, sz), out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", default="")
    ap.add_argument("--levels", default="0,1,2")
    ap.add_argument("--tag", default="")
    ap.add_argument("--no-v1", action="store_true")
    ap.add_argument("--views", default="game,three,roof,nose,engine,low")
    args = ap.parse_args(argv)
    levels = {int(v) for v in args.levels.split(",")}
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    trial = Path(args.models).resolve() if args.models else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    (sx, sy, sz), cl = cells()
    protos, used = {}, {}
    for (mx, my, mz), part, rec in cl:
        if mz not in levels:
            continue
        if rec not in protos:
            cands = []
            if trial:
                cands.append((trial / f"{rec:03d}.opus-v2.gltf", "v2-trial"))
            cands.append((GAME / f"{rec:03d}.opus-v2b.gltf", "v2b"))
            cands.append((GAME / f"{rec:03d}.opus-v2.gltf", "v2"))
            if not args.no_v1:
                cands.append((GAME / f"{rec:03d}.opus-v1.gltf", "v1"))
            protos[rec] = None
            for p, kind in cands:
                if p.exists():
                    before = set(bpy.data.objects)
                    bpy.ops.import_scene.gltf(filepath=str(p))
                    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
                    for o in new:
                        o.location = (0, 0, -1000)
                    protos[rec] = (new, kind)
                    break
        if protos[rec] is None:
            used.setdefault("absent", []).append(rec)
            continue
        objs, kind = protos[rec]
        for o in objs:
            c = o.copy(); bpy.context.collection.objects.link(c)
            c.location = Vector((2 * mx, -2 * my, mz * H))
        used.setdefault(kind, set()).add(rec)
    for v in protos.values():
        if v:
            for o in v[0]:
                bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"; sc.render.film_transparent = True
    try:
        sc.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.43, 0.46, 1)
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.2; sun.color = (1.0, 0.94, 0.83); sun.angle = math.radians(3)
    so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    az, el = math.radians(-118), math.radians(51)
    so.rotation_euler = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))).to_track_quat("Z", "Y").to_euler()
    cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    shots = []
    views = set(args.views.split(","))

    def shot(name, target, wpx, hpx, az=-45, el=30, ortho=None, lens=35, dist=60):
        sc.render.resolution_x, sc.render.resolution_y = wpx, hpx
        a, e = math.radians(az), math.radians(el)
        off = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * dist
        co.location = Vector(target) + off
        co.rotation_euler = (-off).to_track_quat("-Z", "Y").to_euler()
        if ortho:
            cam.type = "ORTHO"; cam.ortho_scale = ortho
        else:
            cam.type = "PERSP"; cam.lens = lens
        cam.clip_start, cam.clip_end = 0.1, 500
        p = out / f"AVENGER{args.tag}_{name}.png"
        sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        shots.append(str(p.relative_to(ROOT)))

    if "game" in views:
        # match inspect_v2.composite canvas: W=(sx+sy)*16+64, H=(sx+sy)*8+sz*24+80, ox=sy*16+16, oy=24*sz+24 (1x)
        W, Hh = (sx + sy) * 16 + 64, (sx + sy) * 8 + sz * 24 + 80
        ox, oy = sy * 16 + 16, 24 * sz + 24
        cx, cy = W / 2, Hh / 2
        s_ = (cx - ox) / 8.0      # X + Y
        d_ = (cy - oy - 32) / 4.0  # X - Y
        X, Y = (s_ + d_) / 2, (s_ - d_) / 2
        shot("game_camera_4x", (X, Y, 0.0), W * 4, Hh * 4, ortho=W * PX, dist=120)
    if "three" in views:
        shot("three_quarter_SE", (9.0, -27.0, H + 1.2), 1600, 1100, az=-50, el=32, lens=32, dist=34)
    if "roof" in views:
        shot("roof_SW", (9.0, -26.0, 2 * H + 0.3), 1600, 1100, az=-130, el=28, lens=32, dist=26)
    if "nose" in views:
        shot("nose_S", (9.0, -36.0, H + 1.0), 1400, 1000, az=-75, el=18, lens=32, dist=12)
    if "engine" in views:
        shot("engines_E", (13.0, -24.0, H + 1.0), 1400, 1000, az=-20, el=22, lens=30, dist=16)
    if "low" in views:
        shot("low_NE_rear", (9.0, -18.0, H), 1400, 1000, az=60, el=15, lens=30, dist=22)
    rep = {k: sorted(v) if isinstance(v, set) else v for k, v in used.items()}
    (out / f"AVENGER{args.tag}_assembly.json").write_text(json.dumps({"sources": rep, "renders": shots}, indent=1), encoding="utf-8")
    print("ASSEMBLY", {k: len(v) for k, v in rep.items()}, flush=True)


if __name__ == "__main__":
    main()
