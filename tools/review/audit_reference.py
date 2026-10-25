# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/audit_reference.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT; catalog = pipeline_paths.path('catalog')
"""Audit reference identities/assembly against the root renderer and source bytes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from PIL import Image
import yaml

from catalog_reference import decode_pck, palette
from renderer_reference import standing_recipe, assemble, FACINGS

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT


def renderer_body_orders(routine):
    source = (ROOT / "src/Battlescape/UnitSprite.cpp").read_text(encoding="utf-8")
    start = source.index(f"void UnitSprite::drawRoutine{routine}()")
    end = source.find("void UnitSprite::", start+10)
    function = source[start:end if end >= 0 else len(source)]
    switch = function[function.rfind("switch (unitDir)"):]
    pieces = re.split(r"case\s+(\d+)\s*:", switch)
    names = {"leftArm": "left_arm", "rightArm": "right_arm", "legs": "legs", "torso": "torso"}
    result = {}
    for index in range(1, len(pieces), 2):
        body = pieces[index+1]
        # Standing reference has no held item, so any two-handed branch is false.
        if "else" in body:
            body = body[body.rfind("else"):]
        result[int(pieces[index])] = tuple(names[name] for name in re.findall(r"blitBody\((\w+)\)", body))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reject-initial-drafts", action="store_true")
    args = parser.parse_args()
    catalog_path = pipeline_paths.path("catalog")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    errors, warnings, checked = [], [], Counter()
    colors = palette(ROOT / "reference")
    # Decode verifies every real TAB offset, not only the table's inferred count.
    for directory in ("TERRAIN", "UNITS", "UFOGRAPH"):
        for path in sorted((ROOT / "reference" / directory).glob("*.TAB")):
            pck = path.with_suffix(".PCK")
            width, height = (128, 64) if path.stem == "X1" else (32, 48) if path.stem == "BIGOBS" else (32, 40)
            try:
                frames = decode_pck(pck, colors, width, height)
                checked["pck_sets"] += 1
                checked["pck_frames"] += len(frames)
            except Exception as error:
                errors.append(str(error))
    for routine in (0, 1, 6, 7, 10):
        expected = renderer_body_orders(0 if routine == 10 else routine)
        for direction in range(8):
            actual = tuple(layer["part"] for layer in standing_recipe(routine, direction)["layers"])
            if actual != expected.get(direction):
                errors.append(f"Routine {routine}, facing {direction}: {actual} != root renderer {expected.get(direction)}")
            checked["unit_layer_orders"] += 1
    raw_mcd = {}
    item_rules = {x["type"]: x for x in yaml.safe_load((ROOT / "bin/standard/xcom1/items.rul").read_text(encoding="utf-8"))["items"]}
    for asset in catalog["assets"]:
        if asset["category"] == "unit":
            raw_frames = decode_pck(ROOT / asset["source"], colors)
            for view_index, view in enumerate(asset.get("reference_views", [])):
                expected_recipe = standing_recipe(asset["drawing_routine"], view_index)
                if view["layers"] != expected_recipe["layers"]:
                    errors.append(f"Catalog assembly is stale/incorrect: {asset['id']} view {view_index}")
                expected_pixels = assemble(raw_frames, expected_recipe).tobytes()
                actual_pixels = Image.open(ROOT / view["path"]).convert("RGBA").tobytes()
                if expected_pixels != actual_pixels:
                    errors.append(f"Assembled reference pixels differ: {asset['id']} view {view_index}")
                checked["assembled_unit_views"] += 1
        if asset["category"] == "terrain":
            raw = raw_mcd.setdefault(asset["set"], (ROOT / asset["source"]).read_bytes())
            data = raw[asset["record"]*62:(asset["record"]+1)*62]
            if list(data[:8]) != asset["frames"]:
                errors.append(f"Frame mapping mismatch: {asset['id']}")
            if data[53] >= 4:
                warnings.append({"id": asset["id"], "issue": f"Original MCD Tile_Type={data[53]} is outside the normal tile-part enum; do not invent a semantic type"})
            checked["mcd_records"] += 1
        elif asset["category"] == "item":
            rule = item_rules[asset["name"]]
            for catalog_key, rule_key in (("big_sprite", "bigSprite"), ("floor_sprite", "floorSprite"), ("hand_sprite", "handSprite")):
                if asset.get(catalog_key) != rule.get(rule_key):
                    errors.append(f"Item mapping mismatch: {asset['id']} {catalog_key}")
            checked["item_identities"] += 1
        for view in asset.get("reference_views", asset.get("reference_frames", [])):
            if view.get("pixel_sha256"):
                pixels = Image.open(ROOT / view["path"]).convert("RGBA").tobytes()
                if hashlib.sha256(pixels).hexdigest() != view["pixel_sha256"]:
                    errors.append(f"Reference image/hash mismatch: {asset['id']} {view['path']}")
                checked["reference_images"] += 1
        if args.reject_initial_drafts and asset.get("model") and asset["status"] in ("modeled_needs_review", "rejected_initial_draft"):
            asset["status"] = "rejected_initial_draft"
            asset["rebuild_status"] = "pending"
            asset.setdefault("legacy_review_image", asset.get("review_image"))
    report = {"passed": not errors, "checks": dict(checked), "errors": errors, "warnings": warnings,
              "direction_labels": list(FACINGS), "projection": "screen x=16(x-y), y=8(x+y)-24z; fixed tactical camera",
              "model_quality": "No initial draft is accepted by a structural reference audit"}
    path = ROOT / "art/review/reference_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    if args.reject_initial_drafts:
        catalog_path.write_text(json.dumps(catalog, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
