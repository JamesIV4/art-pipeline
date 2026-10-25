# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/master_sheet.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""Full-craft review sheet: sprite composite vs master (game camera, same framing), then front-left / rear-right
3/4 views, nose+canopy and engine+pylon close-ups, and the level-1 cutaway.
python master_sheet.py <run_dir> <out.png> [title]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import WORK  # noqa: E402
F = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 22)
FS = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 17)
BG = (30, 36, 44)
CROP = (300, 560, 1360, 1230)


def onbg(p, size=None):
    im = Image.open(p).convert("RGBA")
    b = Image.new("RGBA", im.size, BG + (255,)); b.alpha_composite(im)
    b = b.convert("RGB")
    return b.resize(size, Image.Resampling.LANCZOS) if size else b


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    title = sys.argv[3] if len(sys.argv) > 3 else ""
    comp = Image.open(WORK / "sources/composite_upto_z2_4x.png").convert("RGB").crop(CROP)
    game = onbg(run / "master_game_camera_4x.png").crop(CROP)
    W = comp.width * 2 + 30
    tiles = [("front-left 3/4", "master_front_left.png"), ("rear-right 3/4", "master_rear_right.png"),
             ("nose + canopy close-up", "master_nose_canopy.png"), ("engine + pylon close-up", "master_engine_pylon.png"),
             ("level-1 cutaway (roof hidden)", "master_level1_cutaway.png"), ("UFOpaedia UP001 (form reference)", None)]
    tw = (W - 40) // 3
    th = int(tw * 0.70)
    Hh = 50 + comp.height + 40 + 2 * (th + 34) + 20
    img = Image.new("RGB", (W, Hh), (18, 22, 28))
    d = ImageDraw.Draw(img)
    d.text((10, 12), f"AVENGER v2b master  |  left: original sprite composite (4x)  right: master, game camera, same framing  {title}",
           font=F, fill=(240, 220, 160))
    img.paste(comp, (10, 48)); img.paste(game, (comp.width + 20, 48))
    y = 48 + comp.height + 30
    for k, (lab, fn) in enumerate(tiles):
        x = 10 + (k % 3) * (tw + 10)
        yy = y + (k // 3) * (th + 34)
        if fn:
            im = onbg(run / fn)
        else:
            im = Image.open(WORK / "sources/UP001_3x.png").convert("RGB")
        r = min(tw / im.width, th / im.height)
        im = im.resize((int(im.width * r), int(im.height * r)), Image.Resampling.LANCZOS)
        img.paste(im, (x + (tw - im.width) // 2, yy + 26))
        d.text((x, yy + 2), lab, font=FS, fill=(200, 215, 225))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
