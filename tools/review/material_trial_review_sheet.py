# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/material_trial_review_sheet.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT; catalog = pipeline_paths.path('catalog')
"""Pair one actual model with its own sprite, selected from a trial manifest."""
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
inputs = parser.add_mutually_exclusive_group(required=True)
inputs.add_argument("--folder")
inputs.add_argument("--manifests", nargs="+")
parser.add_argument("--name", required=True)
args = parser.parse_args()
lookup = {asset["id"]: asset for asset in json.loads(pipeline_paths.path("catalog").read_text(encoding="utf-8"))["assets"]}
manifests = [ROOT / path for path in args.manifests] if args.manifests else sorted((ROOT / args.folder).rglob("trial_manifest.json"))
assert manifests, "No exact-identity trial manifests found"
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
rows = []
for path in manifests:
    trial = json.loads(path.read_text(encoding="utf-8"))
    asset = lookup[trial["asset_id"]]
    assert trial["reference_mcd"] == asset["record"]
    phases = trial.get("reference_pck_phases", trial.get("actual_pck_phases"))
    phases = [phase["pck_frame"] if isinstance(phase, dict) else phase for phase in phases]
    assert phases == list(dict.fromkeys(asset["frames"]))
    views = trial.get("views", trial.get("review_views"))
    trial["views"] = [view.get("path") if isinstance(view, dict) else view for view in views]
    assert len(trial["views"]) == 4
    candidate = trial.get("material_candidate", trial.get("materials", {}).get("foliage", "source-specific revision"))
    trial["candidate_label"] = candidate.get("id", "candidate") if isinstance(candidate, dict) else candidate
    rows.append((asset, trial))
canvas = Image.new("RGB", (1560, len(rows)*302+36), "#17212b")
draw = ImageDraw.Draw(canvas)
draw.text((10, 8), "ACTUAL ASSET MATERIAL TRIALS / source selected from each manifest", fill="#f2ddaa", font=font)
for row, (asset, trial) in enumerate(rows):
    y = 36+row*302
    with Image.open(ROOT / asset["reference_image"]) as opened:
        source = opened.convert("RGBA").resize((192, 240), Image.Resampling.NEAREST)
    canvas.paste(source, (8, y), source)
    draw.text((8, y+248), asset["id"], fill="#d1e4e7", font=font)
    draw.text((8, y+266), f"M{asset['record']:03d} -> P{asset['frames'][0]:03d}", fill="#d1e4e7", font=font)
    for index, path in enumerate(trial["views"]):
        with Image.open(ROOT / path) as opened:
            picture = opened.convert("RGB")
            picture.thumbnail((286, 270), Image.Resampling.LANCZOS)
        x = 218+index*332
        canvas.paste(picture, (x, y))
        draw.text((x, y+270), trial["candidate_label"], fill="#d1e4e7", font=font)
        draw.text((x, y+286), f"view {index+1}", fill="#a0b9c4", font=font)
output = ROOT / f"art/review/verified_sheets/{args.name}.png"
save_png(canvas, output)
print(str(output))
