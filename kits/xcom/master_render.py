# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/master_render.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""Render the complete AVENGER v2b master (every record's canonical model at all its AVENGER.MAP positions),
directly from master.py (no export), from the game camera framed like the 4x sprite composite plus 3/4 and
close-up views.
blender --background --factory-startup --threads 2 --python master_render.py -- --out DIR [--views a,b] [--levels 0,1,2]
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import WORK  # noqa: E402
import master as M  # noqa: E402
import meshdata as MD  # noqa: E402
import blender_build as BB  # noqa: E402
from avgeo import H  # noqa: E402

PX = 2 * math.sqrt(2) / 32


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", default="game,fl,rr,nose,engine,close,interior")
    ap.add_argument("--levels", default="0,1,2")
    ap.add_argument("--tex", default=str(WORK / "textures/out"))
    args = ap.parse_args(argv)
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    levels = {int(v) for v in args.levels.split(",")}
    sc, co, cam = BB.setup_scene()
    mats = BB.mat_defs(Path(args.tex).resolve())
    cache = {}
    for rec, pls in sorted(M.PLACEMENTS.items()):
        for (mx, my, mz), part in pls:
            if mz not in levels:
                continue
            if rec not in cache:
                tile, solids = M.record_faces(rec)
                cache[rec] = (tile, MD.build(solids, tile))
            tile, bufs = cache[rec]
            ob = BB.make_object(f"R{rec:03d}_{mx}_{my}_{mz}", bufs, mats)
            ob.location = Vector((2 * mx, -2 * my, mz * H))
    views = set(args.views.split(","))

    def shot(name, target, w, h, az=-45, el=30, ortho=None, lens=35, dist=60):
        BB.shoot(sc, co, cam, out / f"master_{name}.png", target, w, h, az=az, el=el, ortho=ortho, lens=lens, dist=dist)

    if "game" in views:
        sx, sy, sz = 10, 20, 3
        W, Hh = (sx + sy) * 16 + 64, (sx + sy) * 8 + sz * 24 + 80
        ox, oy = sy * 16 + 16, 24 * sz + 24
        s_ = (W / 2 - ox) / 8.0
        d_ = (Hh / 2 - oy - 32) / 4.0
        X, Y = (s_ + d_) / 2, (s_ - d_) / 2
        shot("game_camera_4x", (X, Y, 0.0), W * 4, Hh * 4, ortho=W * PX, dist=120)
    if "fl" in views:
        shot("front_left", (9.0, -28.0, H + 0.8), 1600, 1100, az=-135, el=24, lens=30, dist=19)
    if "rr" in views:
        shot("rear_right", (9.0, -22.0, H + 0.8), 1600, 1100, az=35, el=24, lens=30, dist=19)
    if "nose" in views:
        shot("nose_canopy", (9.0, -36.2, H + 1.2), 1400, 1000, az=-100, el=22, lens=35, dist=9.5)
    if "engine" in views:
        shot("engine_pylon", (15.0, -23.0, H + 1.2), 1400, 1000, az=-35, el=20, lens=35, dist=11)
    if "close" in views:
        # game-angle close-ups (az -45, el 30, orthographic) of the window, right fin, front gear and a side panel
        shot("close_window", (9.0, -36.0, H + 2.0), 900, 700, ortho=6.0, dist=40)
        shot("close_fin", (12.4, -36.2, H + 0.9), 900, 700, ortho=4.2, dist=40)
        shot("close_gear", (12.0, -30.0, 1.2), 900, 700, ortho=4.2, dist=40)
        shot("close_side", (13.8, -24.0, H + 1.2), 900, 700, ortho=4.6, dist=40)
    if "interior" in views:
        for o in bpy.data.objects:
            if o.name.startswith("R") and o.name.endswith("_2"):
                o.hide_render = True
        shot("level1_cutaway", (9.0, -26.0, H), 1600, 1100, az=-45, el=42, lens=32, dist=21)


if __name__ == "__main__":
    main()
