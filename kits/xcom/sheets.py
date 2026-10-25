# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/sheets.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""Per-record review sheet: enlarged exact source sprite(s) (8x, all distinct frames, P_Level shift as in game)
beside the sprite-matched game-camera render (same scale) and four Blender angles.
python sheets.py <renders_dir> <out_dir> <rec,rec,...> [label]
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT, WORK  # noqa: E402  (also puts art-pipeline/tools/review on sys.path)
from catalog_reference import palette, decode_pck  # noqa: E402

F = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
FS = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
RECS = {r["record"]: r for r in json.loads((WORK / "sources/records.json").read_text(encoding="utf-8"))}
FR = decode_pck(ROOT / "reference/TERRAIN/AVENGER.PCK", palette(ROOT / "reference"))
BG = (46, 54, 64)


def sprite_panel(rec, S=8):
    r = RECS[rec]
    fs = sorted(set(r["frames"]), key=r["frames"].index)
    W = Image.new("RGB", (len(fs) * 32 * S + (len(fs) - 1) * 8, 40 * S), BG)
    for k, f in enumerate(fs):
        b = Image.new("RGBA", (32, 40), BG + (255,))
        b.alpha_composite(FR[f], (0, -r["p_level"]) if r["p_level"] else (0, 0))
        W.paste(b.convert("RGB").resize((32 * S, 40 * S), Image.Resampling.NEAREST), (k * (32 * S + 8), 0))
    d = ImageDraw.Draw(W)
    for k in range(len(fs)):
        ox = k * (32 * S + 8)
        for (x0, y0, x1, y1) in ((16, 24, 32, 32), (32, 32, 16, 40), (16, 40, 0, 32), (0, 32, 16, 24)):
            d.line((ox + x0 * S, y0 * S, ox + x1 * S, y1 * S), fill=(120, 100, 50))
    return W, fs


def on_bg(p, size=None):
    im = Image.open(p).convert("RGBA")
    if size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    b = Image.new("RGBA", im.size, BG + (255,))
    b.alpha_composite(im)
    return b.convert("RGB")


def sheet(rdir, out, rec, label="", notes=""):
    sp, fs = sprite_panel(rec)
    gc = on_bg(rdir / f"{rec:03d}/game_camera_8x.png")
    d_ = ImageDraw.Draw(gc)
    for (x0, y0, x1, y1) in ((16, 24, 32, 32), (32, 32, 16, 40), (16, 40, 0, 32), (0, 32, 16, 24)):
        d_.line((x0 * 8, y0 * 8, x1 * 8, y1 * 8), fill=(120, 100, 50))
    views = [on_bg(rdir / f"{rec:03d}/view_{k}.png", (320, 320)) for k in range(1, 5)]
    W = max(sp.width + gc.width + 40, 4 * 330) + 20
    Hh = 40 + 320 + 30 + 320 + 40
    img = Image.new("RGB", (W, Hh), (24, 28, 34))
    d = ImageDraw.Draw(img)
    r = RECS[rec]
    d.text((10, 8), f"AVENGER {rec:03d}  {label}  | MCD rec {rec} -> PCK frames {fs}  type {r['tile_type']}  P_Level {r['p_level']}  T_Level {r['t_level']}", font=F, fill=(240, 220, 160))
    img.paste(sp, (10, 36)); d.text((10, 36 + 322), "source sprite 8x (P_Level shift applied)", font=FS, fill=(200, 210, 220))
    img.paste(gc, (sp.width + 30, 36)); d.text((sp.width + 30, 36 + 322), "v2 render, game camera, same scale", font=FS, fill=(200, 210, 220))
    for k, v in enumerate(views):
        img.paste(v, (10 + k * 330, 36 + 350))
    d.text((10, Hh - 22), "views: SE (game az) / SW / NW / NE   " + notes, font=FS, fill=(200, 210, 220))
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"AVENGER_{rec:03d}_sheet.png"
    img.save(p)
    return p


if __name__ == "__main__":
    rdir, out = Path(sys.argv[1]), Path(sys.argv[2])
    label = sys.argv[4] if len(sys.argv) > 4 else ""
    for r in sys.argv[3].split(","):
        print(sheet(rdir, out, int(r), label))
