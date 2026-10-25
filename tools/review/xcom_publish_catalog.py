# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/publish_catalog.py (imported 2026-10-25)
# Changed: renamed (trick-or-treat owns publish_catalog.py); ROOT/PROJECT/catalog via pipeline_paths; <game>/art/tools appended to sys.path for natural_terrain.py
"""Publish modeled identities to Godot and assemble source/model review sheets."""
import argparse
from collections import Counter
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
PROJECT = pipeline_paths.path("godot_project")
_sys.path.append(str(ROOT / "art/tools"))  # game-side natural_terrain.py (MANIFEST, apply_to_catalog)
GAME_TERRAIN = ROOT / "bin/standard/xcom1/TERRAIN"   # what the game loads: OXCE's own copies override the originals
# Game records whose frames match no original record, settled by hand: (set, record) -> why it has no model
GAME_RECORD_EMPTY = {("LIGHTNIN", 41): "OXCE's open state of the UFO door 040; the 3D door slides away when open"}


def game_records(entries):
    """Identities follow the GAME's MCD record numbers, but the art catalog keeps the original files' numbering.
    OXCE remade some craft maps with their own MCDs (the Lightning, 2026-10-23: its console moved from 41 to 42, 41
    became the UFO door's open state, 43-46 are invisible blockers). Each game record whose frames differ from the
    original's takes the identity of the original record with the same sprite frames; a record drawing nothing is
    intentionally empty; anything else is reported (it would show as a sprite billboard)."""
    from catalog_reference import decode_pck, palette
    by_id = {e["id"]: e for e in entries}
    originals_by_id = dict(by_id)   # look-ups by the original numbering, before any game record replaces one
    colors = None
    for mcd in sorted(GAME_TERRAIN.glob("*.MCD")):
        original = ROOT / "reference/TERRAIN" / mcd.name
        if not original.exists():
            continue
        game, orig = mcd.read_bytes(), original.read_bytes()
        frames = lambda data, i: data[i * 62:i * 62 + 8]
        n_game, n_orig = len(game) // 62, len(orig) // 62
        changed = [i for i in range(n_game) if i >= n_orig or frames(game, i) != frames(orig, i)]
        if not changed:
            continue
        family = mcd.stem
        colors = colors or palette(ROOT / "reference")
        sprites = decode_pck(mcd.with_suffix(".PCK"), colors)
        originals = {frames(orig, j): j for j in range(n_orig)}
        for i in changed:
            asset_id = f"terrain/{family}/{i:03d}"
            match = originals.get(frames(game, i))
            source = originals_by_id.get(f"terrain/{family}/{match:03d}") if match is not None else None
            empty = all(sprites[f].getbbox() is None for f in frames(game, i) if f < len(sprites))
            if source and "model" in source:
                entry = dict(source, id=asset_id, record=i,
                             source_label=f"TERRAIN/{family}.MCD (game) record {i} = original record {match}")
            elif empty or (family, i) in GAME_RECORD_EMPTY:
                entry = {"id": asset_id, "category": "terrain", "family": family, "status": "intentional_empty",
                         "source_label": f"TERRAIN/{family}.MCD (game) record {i}: "
                                         + GAME_RECORD_EMPTY.get((family, i), "invisible (empty sprite frames)"),
                         "frame_semantics": "animation phases; not facings", "quality_passed": False, "record": i}
            else:
                print(f"WARNING {asset_id}: the game's record matches no original record; it has no 3D model")
                continue
            if asset_id in by_id:
                entries[entries.index(by_id[asset_id])] = entry
            else:
                last = max(k for k, e in enumerate(entries) if e.get("family") == family)
                entries.insert(last + 1, entry)
            by_id[asset_id] = entry
            print(f"game record {asset_id}: {entry['source_label']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheets", action="store_true")
    parser.add_argument("--game-records", action="store_true",
                        help="only map the game's MCD records onto the published catalog in place (keeps its other entries)")
    args = parser.parse_args()
    if args.game_records:
        output = PROJECT / "assets/catalog.json"
        published = json.loads(output.read_text(encoding="utf-8"))
        game_records(published["assets"])
        output.write_text(json.dumps(published, indent=2)+"\n", encoding="utf-8")
        return
    catalog = json.loads(pipeline_paths.path("catalog").read_text(encoding="utf-8"))
    entries = []
    for asset in catalog["assets"]:
        model = asset.get("model", "")
        entry = {"id": asset["id"], "category": asset["category"],
                 "family": asset.get("set", "ITEMS"), "status": asset["status"]}
        entry["source_label"] = asset.get("source_label", asset["source"])
        entry["frame_semantics"] = asset.get("frame_semantics", asset.get("direction_note", "inventory and ground representations"))
        entry["quality_passed"] = bool(asset.get("quality_review", {}).get("passed", False))
        if model and (ROOT / model).exists():
            entry["model"] = "res://"+(ROOT / model).relative_to(PROJECT).as_posix()
            entry["metrics"] = asset["metrics"]
            if asset.get("variants"):
                entry["variants"] = {key: "res://"+(ROOT / value).relative_to(PROJECT).as_posix()
                                     for key, value in asset["variants"].items()}
                if asset.get("variant_metrics"):
                    entry["variant_metrics"] = asset["variant_metrics"]
                contexts = {key: review["context_west_asset_id"] for key, review in asset.get("variant_reviews", {}).items()
                            if review.get("context_west_asset_id")}
                if contexts:
                    entry["variant_context_west"] = contexts
            if asset["category"] == "terrain":
                entry.update({k: asset[k] for k in ("record", "part", "destroyed_record", "alternate_record", "door", "ufo_door", "light_source")})
        entries.append(entry)
    game_records(entries)
    output = PROJECT / "assets/catalog.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    published = {"schema": 1, "assets": entries}
    from natural_terrain import MANIFEST, apply_to_catalog
    natural_manifest = PROJECT / MANIFEST
    if natural_manifest.exists():
        apply_to_catalog(published, json.loads(natural_manifest.read_text()))
    output.write_text(json.dumps(published, indent=2)+"\n", encoding="utf-8")
    print(f"Published {sum('model' in a for a in entries)} modeled identities of {len(entries)}")
    if not args.sheets:
        return
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
    families = sorted({a.get("set", "ITEMS") for a in catalog["assets"]})
    for family in families:
        available = [a for a in catalog["assets"] if a.get("set", "ITEMS") == family and a.get("review_image") and (ROOT / a["review_image"]).exists()]
        for page_start in range(0, len(available), 16):
            page = available[page_start:page_start+16]
            w, h = 288, 238
            canvas = Image.new("RGB", (w*4, h*4+32), "#17212b")
            draw = ImageDraw.Draw(canvas)
            draw.text((10, 8), f"{family}   ORIGINAL ART / BLENDER REVIEW   page {page_start//16+1}", font=font, fill="#f2ddaa")
            for i, asset in enumerate(page):
                x, y = (i % 4)*w, 32+(i//4)*h
                draw.rectangle((x+2, y+2, x+w-3, y+h-3), fill="#24323d")
                source = Image.open(ROOT / asset["reference_image"]).convert("RGBA")
                source = source.resize((source.width*2, source.height*2), Image.Resampling.NEAREST)
                canvas.paste(source, (x+7, y+48), source)
                model = Image.open(ROOT / asset["review_image"]).convert("RGB")
                model.thumbnail((204, 192), Image.Resampling.LANCZOS)
                canvas.paste(model, (x+78, y+10))
                label = asset["id"].split("/")[-1]
                recipe = asset.get("recipe", "")
                source_label = f"MCD {label} / PCK {asset['frames'][0]:03d}" if asset["category"] == "terrain" else asset["id"].split("/")[-1]
                draw.text((x+9, y+h-38), source_label[:37], font=font, fill="#d1e4e7")
                draw.text((x+9, y+h-21), f"{asset['metrics']['triangles']} triangles / {asset['metrics']['surfaces']} surfaces", font=font, fill="#9db6bf")
            path = ROOT / f"art/review/sheets/{family}_{page_start//16+1:02d}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(path)
    print("Comparison sheets: art/review/sheets/")


if __name__ == "__main__":
    main()
