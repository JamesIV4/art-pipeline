# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/source_dossier_sheet.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT; catalog = pipeline_paths.path('catalog')
"""Make enlarged, precisely labeled source-only sheets before modeling an asset."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from catalog_reference import save_png

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ids", required=True)
parser.add_argument("--name", required=True)
args = parser.parse_args()
catalog = json.loads(pipeline_paths.path("catalog").read_text(encoding="utf-8"))
by_id = {a["id"]: a for a in catalog["assets"]}
selected = [by_id[key] for key in args.ids.split(",")]
columns, width, height = 4, 296, 410
canvas = Image.new("RGB", (columns*width, ((len(selected)+columns-1)//columns)*height+34), "#17212b")
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 14)
draw.text((12, 9), "VERIFIED SOURCE REFERENCES / "+args.name, font=font, fill="#f2ddaa")
for index, asset in enumerate(selected):
    x, y = index % columns*width, 34+index//columns*height
    image = Image.open(ROOT / asset["reference_image"]).convert("RGBA")
    image = image.resize((image.width*8, image.height*8), Image.Resampling.NEAREST)
    canvas.paste(image, (x+20, y+6), image)
    draw.text((x+10, y+332), asset["id"], font=font, fill="#d1e4e7")
    if asset["category"] == "terrain":
        draw.text((x+10, y+352), f"MCD {asset['record']:03d} -> PCK {asset['frames'][0]:03d}", font=font, fill="#d1e4e7")
        draw.text((x+10, y+372), asset["part"], font=font, fill="#9db6bf")
output = ROOT / f"art/review/source_dossiers/{args.name}.png"
output.parent.mkdir(parents=True, exist_ok=True)
save_png(canvas, output)
print(str(output))
