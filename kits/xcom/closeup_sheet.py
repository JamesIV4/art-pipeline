# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/closeup_sheet.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""Close-ups beside the enlarged sprite crops (same game angle): window (P024+P025 in the composite), right nose fin
(P011), front landing gear (P052), side panel (P034-P036 hull side in the composite).
python closeup_sheet.py <run_dir> <out.png>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT, WORK  # noqa: E402  (also puts art-pipeline/tools/review on sys.path)
from catalog_reference import palette, decode_pck  # noqa: E402

F = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 18)
BG = (30, 36, 44)
fr = decode_pck(ROOT / "reference/TERRAIN/AVENGER.PCK", palette(ROOT / "reference"))
comp = Image.open(WORK / "sources/composite_upto_z2_4x.png").convert("RGB")
comp1 = Image.open(WORK / "sources/composite_upto_z1_4x.png").convert("RGB")


def sprite(i, S=10):
    b = Image.new("RGBA", (32, 40), BG + (255,)); b.alpha_composite(fr[i])
    return b.convert("RGB").resize((32 * S, 40 * S), Image.Resampling.NEAREST)


def onbg(p):
    im = Image.open(p).convert("RGBA")
    b = Image.new("RGBA", im.size, BG + (255,)); b.alpha_composite(im)
    return b.convert("RGB")


def fit(im, w, h):
    r = min(w / im.width, h / im.height)
    return im.resize((int(im.width * r), int(im.height * r)), Image.Resampling.NEAREST if r > 1.5 else Image.Resampling.LANCZOS)


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    # composite crops (4x canvas coordinates)
    win = comp.crop((300 + 90, 560 + 420, 300 + 300, 560 + 560))
    side = comp.crop((300 + 470, 560 + 400, 300 + 720, 560 + 560))
    rows = [("window: composite (P024+P025)", win, "close_window.png"),
            ("right nose fin: P011 (10x)", sprite(11), "close_fin.png"),
            ("front gear: P052 (10x)", sprite(52), "close_gear.png"),
            ("hull side: composite (P034-P036)", side, "close_side.png")]
    W, ROWH = 1500, 520
    img = Image.new("RGB", (W, 40 + len(rows) * ROWH), (18, 22, 28))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "AVENGER v2b close-ups: enlarged source (left) vs master render at the game angle (right)", font=F, fill=(240, 220, 160))
    for k, (lab, src, fn) in enumerate(rows):
        y = 40 + k * ROWH
        a = fit(src, 700, ROWH - 40)
        b = fit(onbg(run / f"master_{fn}"), 720, ROWH - 40)
        img.paste(a, (10, y + 30)); img.paste(b, (760, y + 30))
        d.text((10, y + 6), lab, font=F, fill=(200, 215, 225))
        d.text((760, y + 6), "master " + fn[:-4], font=F, fill=(200, 215, 225))
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
