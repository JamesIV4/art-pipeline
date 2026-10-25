# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/review_contact_sheet.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT
"""Four-angle model reviews beside enlarged original art, with exact identities."""
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
parser.add_argument("--godot-tag", default="")
parser.add_argument("--image-prefix", default="model")
parser.add_argument("--catalog", default="art/asset_catalog.json", help="Use isolated staged diagnostic records when supplied")
args = parser.parse_args()
catalog_path = (ROOT / args.catalog).resolve()
assert catalog_path.is_relative_to(ROOT / "art"), "Review records must stay in the art workspace"
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
lookup = {a["id"]: a for a in catalog.get("staged_assets", catalog.get("assets", []))}
assets = [lookup[key] for key in args.ids.split(",")]
canvas = Image.new("RGB", (1680, 338*len(assets)+38), "#17212b")
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
small = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
draw.text((12, 10), "SOURCE / FOUR GODOT REVIEW ANGLES / "+args.name, font=font, fill="#f2ddaa")
for row, asset in enumerate(assets):
    y = 38+row*338
    reference = Image.open(ROOT / asset["reference_image"]).convert("RGBA")
    reference = reference.resize((reference.width*7, reference.height*7), Image.Resampling.NEAREST)
    canvas.paste(reference, (18, y+4), reference)
    draw.text((12, y+290), asset["id"], font=small, fill="#d1e4e7")
    if "record" in asset:
        draw.text((12, y+308), f"MCD {asset['record']} -> PCK {asset['frames'][0]}", font=small, fill="#d1e4e7")
    else:  # items: no MCD record; show the inventory sprite reference instead
        draw.text((12, y+308), f"BIGOBS {asset.get('big_sprite', '?')}", font=small, fill="#d1e4e7")
    for view in range(4):
        base = ROOT / f"art/review/godot/{asset['id']}"
        if args.godot_tag:
            base = base / args.godot_tag
        image_path = base / f"{args.image_prefix}-view-{view}.png"
        if not image_path.exists():
            raise ValueError("Godot review missing: "+str(image_path))
        with Image.open(image_path) as opened:
            # The fixed capture's left area contains inspector controls.
            # Crop only this derivative review sheet, retaining full captures.
            image = opened.convert("RGB").crop((380, 135, 1080, 795))
        image.thumbnail((344, 306), Image.Resampling.LANCZOS)
        x = 270+view*350
        canvas.paste(image, (x, y+2))
        draw.text((x+8, y+308), f"view {view+1} / {asset['metrics']['triangles']} triangles", font=small, fill="#d1e4e7")
path = ROOT / f"art/review/verified_sheets/{args.name}.png"
path.parent.mkdir(parents=True, exist_ok=True)
save_png(canvas, path)
print(str(path))
