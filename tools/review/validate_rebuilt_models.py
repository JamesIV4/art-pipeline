# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/validate_rebuilt_models.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT
"""Validate rebuilt exports and their references without accepting their art."""
import argparse
import json
import math
from pathlib import Path
import struct
from urllib.parse import unquote

from PIL import Image

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
TYPES = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}


def validate(asset):
    path = ROOT / asset["model"]
    document = json.loads(path.read_text(encoding="utf-8"))
    buffers = [(path.parent / unquote(b["uri"])).read_bytes() for b in document["buffers"]]
    def values(index):
        accessor = document["accessors"][index]
        view = document["bufferViews"][accessor["bufferView"]]
        fmt = "<" + TYPES[accessor["componentType"]]*WIDTHS[accessor["type"]]
        stride = view.get("byteStride", struct.calcsize(fmt))
        start = view.get("byteOffset", 0)+accessor.get("byteOffset", 0)
        return [struct.unpack_from(fmt, buffers[view["buffer"]], start+i*stride) for i in range(accessor["count"])]
    triangles = 0
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            assert primitive.get("mode", 4) == 4, "Non-triangle primitive"
            attributes = primitive["attributes"]
            for name in ("POSITION", "NORMAL", "TEXCOORD_0", "TANGENT"):
                assert name in attributes, f"Missing {name}"
                assert all(math.isfinite(x) for row in values(attributes[name]) for x in row), f"Non-finite {name}"
            positions = values(attributes["POSITION"])
            texcoords = values(attributes["TEXCOORD_0"])
            if "COLOR_0" in attributes:
                accessor = document["accessors"][attributes["COLOR_0"]]
                assert accessor["type"] in ("VEC3", "VEC4") and accessor["count"] == len(positions), "Invalid color accessor"
                colors = values(attributes["COLOR_0"])
                divisor = {5121: 255, 5123: 65535}.get(accessor["componentType"], 1)
                assert divisor == 1 or accessor.get("normalized"), "Integer color data must be normalized"
                assert all(math.isfinite(x) and 0 <= x/divisor <= 1 for row in colors for x in row), "Invalid linear COLOR_0 range"
            indices = [row[0] for row in values(primitive["indices"])]
            assert max(indices) < len(positions), "Index outside vertex buffer"
            assert len(indices) % 3 == 0
            triangles += len(indices)//3
            for start in range(0, len(indices), 3):
                a, b, c = [positions[index] for index in indices[start:start+3]]
                ab, ac = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
                cross = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0])
                assert sum(value*value for value in cross) > 1e-22, "Zero-area geometry triangle"
                u, v, w = [texcoords[index] for index in indices[start:start+3]]
                determinant = (v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0])
                assert abs(determinant) > 1e-13, "Zero-area UV triangle; tangent basis is undefined"
            normals = values(attributes["NORMAL"])
            tangents = values(attributes["TANGENT"])
            for normal in normals:
                assert .98 < sum(x*x for x in normal) < 1.02, "Invalid exported normal"
            for normal, tangent in zip(normals, tangents):
                assert .98 < sum(x*x for x in tangent[:3]) < 1.02, "Zero or non-unit exported tangent"
                assert abs(abs(tangent[3])-1) < .001, "Invalid tangent handedness"
                assert abs(sum(normal[i]*tangent[i] for i in range(3))) < .001, "Tangent is not orthogonal to the normal"
    assert triangles == asset["metrics"]["triangles"], "Catalog/export triangle count differs"
    positions = [p for mesh in document["meshes"] for primitive in mesh["primitives"] for p in values(primitive["attributes"]["POSITION"])]
    low = [min(p[i] for p in positions) for i in range(3)]
    high = [max(p[i] for p in positions) for i in range(3)]
    if asset["id"] == "terrain/CULTIVAT/014":
        assert high[0] < 0 and high[2]-low[2] > (high[0]-low[0])*2, "West-wall orientation mismatch"
    elif asset["id"] == "terrain/CULTIVAT/015":
        assert high[2] < 0 and high[0]-low[0] > (high[2]-low[2])*2, "North-wall orientation mismatch"
    budget = asset.get("performance_budget", {})
    ceiling = 6000 if budget.get("family") == "vegetation" else 4000
    limit = budget.get("max_triangles", 4000)
    assert isinstance(limit, int) and 0 < limit <= ceiling, "Invalid explicit per-asset triangle budget"
    assert triangles <= limit, "Per-asset triangle budget exceeded"
    assert len(document["meshes"]) == 1, "Static model is not consolidated"
    assert len(document["materials"]) <= 3, "Static asset has too many material surfaces"
    for image in document["images"]:
        image_path = (path.parent / unquote(image["uri"])).resolve()
        assert image_path.exists(), "Missing external PBR image"
        with Image.open(image_path) as opened:
            native = asset.get("texture_trials", {}).get("native_image_dimensions", {}).get(image_path.name)
            if native is not None:
                assert list(opened.size) == native, "Image dimensions differ from the recorded native-detail snapshot"
            # Grass has a native 1254-square generated albedo. Validate its
            # honest source detail budget instead of upscaling to claim 2k.
            declared = asset.get("texture_trials", {}).get("image_budgets", {})
            minimum = declared.get(image_path.name)
            if minimum is None:
                minimum = next((size for key, size in declared.items() if key in image_path.stem), None)
            if minimum is None:
                minimum = 512 if "tight_sawn" in image_path.name else 1024 if "grass_natural_blades" in image_path.name and "albedo" in image_path.name else 2048
            assert min(opened.size) >= minimum, "Texture resolution is below its detail budget"
    assert any(n.get("extras", {}).get("asset_id") == asset["id"] for n in document["nodes"]), "Export/source identity mismatch"
    assert (ROOT / asset["blend"]).exists(), "Editable Blender source is missing"
    assert asset.get("reference_review", {}).get("reviewed"), "Source dossier not reviewed"
    assert len(asset.get("review_views", [])) >= 4, "Four-view Blender review is missing"
    for view in asset["review_views"]:
        assert (ROOT / view).exists(), "Review image missing"
    import_path = Path(str(path)+".import")
    assert import_path.exists(), "Godot has not imported the model"
    settings = import_path.read_text(encoding="utf-8")
    for setting in ("array_mesh/deduplicate_surfaces=true", "meshes/generate_lods=true",
                    "meshes/create_shadow_meshes=true", "meshes/force_disable_compression=false"):
        assert setting in settings, "Missing Godot optimization: "+setting
    return {"id": asset["id"], "triangles": triangles, "surfaces": len(document["materials"]),
            "textures": len(document["images"]), "source_and_export_valid": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", default="terrain/CULTIVAT/014,terrain/CULTIVAT/015,terrain/CULTIVAT/020")
    parser.add_argument("--report", default="art/review/rebuilt_validation.json")
    parser.add_argument("--catalog", default="art/asset_catalog.json", help="Use an isolated root staging artifact without modifying the live catalog")
    parser.add_argument("--variant", default="", help="Validate an explicitly staged variant, not its unchanged base")
    args = parser.parse_args()
    catalog_path = (ROOT / args.catalog).resolve()
    assert catalog_path.is_relative_to(ROOT / "art"), "Validation records must stay in the art workspace"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    selected = set(args.ids.split(","))
    records, errors = [], []
    for asset in catalog.get("staged_assets", catalog.get("assets", [])):
        if asset["id"] not in selected:
            continue
        try:
            if args.variant:
                asset = dict(asset)
                asset["model"] = asset["variants"][args.variant]
                asset["metrics"] = asset["variant_metrics"][args.variant]
                variant_review = asset["variant_reviews"][args.variant]
                asset["blend"] = variant_review["blend"]
                asset["review_views"] = [view["path"] if isinstance(view, dict) else view for view in variant_review["review_views"]]
            records.append(validate(asset))
        except Exception as error:
            errors.append({"id": asset["id"], "error": str(error)})
    report = {"passed": not errors and len(records) == len(selected), "assets": records, "errors": errors}
    report_path = (ROOT / args.report).resolve()
    assert report_path.is_relative_to(ROOT / "art/review"), "Validation report must stay in the review evidence directory"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
