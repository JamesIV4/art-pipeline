# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/measure_window.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""Back-project the windscreen glass pixels (P024 at [4,18], P025 at [5,18], level 1) onto candidate planes to
measure the pane outline in map/craft coordinates. Read-only; prints extents and writes a plot."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT, WORK  # noqa: E402  (also puts art-pipeline/tools/review on sys.path)
from catalog_reference import palette, decode_pck  # noqa: E402

fr = decode_pck(ROOT / "reference/TERRAIN/AVENGER.PCK", palette(ROOT / "reference"))


def glass_mask(im):
    a = np.asarray(im.convert("RGBA")).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    return (al > 0) & (b > r + 30) & (b > 150)


def frame_mask(im):
    a = np.asarray(im.convert("RGBA")).astype(int)
    return a[..., 3] > 0


pts_glass, pts_all = [], []
for mx, f in ((4, 24), (5, 25)):
    my, mz = 18, 1
    gm, am = glass_mask(fr[f]), frame_mask(fr[f])
    for (mask, lst) in ((gm, pts_glass), (am, pts_all)):
        ys, xs = np.nonzero(mask)
        for px, py in zip(xs, ys):
            # sprite-local pixel -> screen relative to the map origin: top vertex of tile (mx,my) is sprite (16,24)
            sx = (px + 0.5 - 16) + 16 * (mx - my)
            sy = (py + 0.5 - 24) + 8 * (mx + my) - 24 * mz
            lst.append((sx, sy))


def backproject(pts, zfun):
    out = []
    for sx, sy in pts:
        # x - y = sx/16 ; 8(x+y) - zvox_abs = sy  with zvox_abs = 24*mz + z(y)
        u = sx / 16.0
        y = 18.5
        for _ in range(30):
            v = (sy + 24 + zfun(y)) / 8.0
            y = (v - u) / 2.0
        x = u + y
        out.append((x, y))
    return np.array(out)


planes = {
    "flat_z24": lambda y: 24.0,
    "flat_z20": lambda y: 20.0,
    "slope_24N_12S": lambda y: 24.0 - 12.0 * (y - 18.0),
    "slope_24N_16S": lambda y: 24.0 - 8.0 * (y - 18.0),
}
for name, zf in planes.items():
    g = backproject(pts_glass, zf)
    a = backproject(pts_all, zf)
    X, Y = 2 * g[:, 0], -2 * g[:, 1]
    XA, YA = 2 * a[:, 0], -2 * a[:, 1]
    print(f"{name:16s} glass X {X.min():6.2f}..{X.max():6.2f} (w {X.max()-X.min():.2f})  Y {Y.min():7.2f}..{Y.max():7.2f} (d {Y.max()-Y.min():.2f})"
          f" | all X {XA.min():6.2f}..{XA.max():6.2f} Y {YA.min():7.2f}..{YA.max():7.2f}")
    img = Image.new("RGB", (600, 400), (30, 30, 30))
    d = ImageDraw.Draw(img)
    for (x, y) in zip(XA, YA):
        d.point((int((x - 5) * 60), int((-y - 33) * 60)), fill=(120, 120, 120))
    for (x, y) in zip(X, Y):
        d.point((int((x - 5) * 60), int((-y - 33) * 60)), fill=(120, 180, 255))
    d.text((5, 5), name + "  (plan view, north up, X 5..15, Y -33..-39.7)", fill=(255, 255, 0))
    img.save(WORK / f"sources/window_plan_{name}.png")
