# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/assembly_sheet.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""Assembly vs sprite composite at the same 4x framing (crop of the craft), side by side + stacked detail.
python assembly_sheet.py <assembly_game_camera_4x.png> <out.png> [title] [composite_level]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import WORK  # noqa: E402
F = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 20)
BG = (30, 36, 44)
CROP = (300, 560, 1360, 1230)


def main():
    a = Image.open(sys.argv[1]).convert("RGBA")
    out = Path(sys.argv[2])
    title = sys.argv[3] if len(sys.argv) > 3 else ""
    lvl = sys.argv[4] if len(sys.argv) > 4 else "2"
    comp = Image.open(WORK / f"sources/composite_upto_z{lvl}_4x.png").convert("RGB")
    b = Image.new("RGBA", a.size, BG + (255,)); b.alpha_composite(a)
    r = b.convert("RGB").crop(CROP)
    c = comp.crop(CROP)
    W = c.width + r.width + 30
    img = Image.new("RGB", (W, c.height + 50), (20, 24, 30))
    d = ImageDraw.Draw(img)
    d.text((10, 10), f"sprite composite (original renderer, 4x)  |  v2 assembly, game camera, same framing   {title}", font=F, fill=(240, 220, 160))
    img.paste(c, (10, 44)); img.paste(r, (c.width + 20, 44))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
