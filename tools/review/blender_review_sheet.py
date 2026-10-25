# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/blender_review_sheet.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT; catalog = pipeline_paths.path('catalog')
"""Review every rebuilt object's four Blender views against its exact source."""
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
lookup = {a["id"]: a for a in json.loads(pipeline_paths.path("catalog").read_text(encoding="utf-8"))["assets"]}
assets = [lookup[key] for key in args.ids.split(",")]
canvas = Image.new("RGB", (1560, len(assets)*302+36), "#17212b")
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
draw.text((10, 9), "SOURCE AND FOUR BLENDER VIEWS / "+args.name, font=font, fill="#f2ddaa")
for row, asset in enumerate(assets):
    y = 36+row*302
    source = Image.open(ROOT / asset["reference_image"]).convert("RGBA")
    source = source.resize((192, 240), Image.Resampling.NEAREST)
    canvas.paste(source, (8, y+4), source)
    draw.text((8, y+250), asset["id"], font=font, fill="#d1e4e7")
    draw.text((8, y+269), f"MCD {asset['record']} -> PCK {asset['frames'][0]}", font=font, fill="#d1e4e7")
    for index, path in enumerate(asset["review_views"]):
        with Image.open(ROOT / path) as opened:
            image = opened.convert("RGB")
        image.thumbnail((286, 286), Image.Resampling.LANCZOS)
        x = 218+index*332
        canvas.paste(image, (x, y))
        draw.text((x+8, y+286), f"view {index+1} / {asset['metrics']['triangles']} triangles", font=font, fill="#d1e4e7")
output = ROOT / f"art/review/verified_sheets/{args.name}.png"
output.parent.mkdir(parents=True, exist_ok=True)
save_png(canvas, output)
print(str(output))
