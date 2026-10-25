# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/record_visual_review.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT; live catalog = pipeline_paths.path('catalog')
"""Apply an explicit completed manual review, separately from export validation."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote
from validate_rebuilt_models import validate

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--review", required=True)
parser.add_argument("--catalog", default="art/asset_catalog.json", help="An isolated root staging artifact may receive scoped approval without promoting the live bank")
args = parser.parse_args()
review = json.loads((ROOT / args.review).read_text(encoding="utf-8"))
assert review["passed"] is True, "Only completed, affirmative manual reviews can be recorded"
assert review["reviewer"] and review["verified_details"] and review["limitations"]
assert all((ROOT / path).exists() for path in review["evidence"])
path = (ROOT / args.catalog).resolve()
isolated = path != pipeline_paths.path("catalog")
assert not isolated or path.is_relative_to(ROOT / "art/review"), "Isolated approval must stay in root review artifacts"
catalog = json.loads(path.read_text(encoding="utf-8"))
asset_key = "staged_assets" if isolated and "staged_assets" in catalog else "assets"
selected = set(review["asset_ids"])
found = set()
for asset in catalog[asset_key]:
    if asset["id"] not in selected:
        continue
    validation = validate(asset)
    base = ROOT / f"art/review/godot/{asset['id']}"
    if review.get("native_review_tag"):
        base = base / review["native_review_tag"]
    prefix = review.get("native_image_prefix", "model")
    assert prefix not in {"corner", "layout"}, "A context capture is not a standalone base review; record its dedicated variant/layout evidence separately"
    captures = [base / f"{prefix}-view-{index}.png" for index in range(4)]
    assert all(capture.exists() for capture in captures), "Missing native four-view evidence"
    # Matching triangle counts alone cannot establish version identity. Keep
    # the exact source, sidecar, cache and runtime receipts part of approval.
    receipt = json.loads((base / "import-receipt.json").read_text(encoding="utf-8-sig"))
    model = (ROOT / asset["model"]).resolve()
    safety_path = ROOT / "art/review/quality_safety_holds.json"
    if safety_path.exists():
        holds = [hold for hold in json.loads(safety_path.read_text(encoding="utf-8"))["holds"]
                 if hold["asset_id"] == asset["id"] and hold["status"] == "active"]
        if holds:
            current_sha = hashlib.sha256(model.read_bytes()).hexdigest()
            assert all(hold["model_sha256"] != current_sha for hold in holds), "Known unsafe frozen model cannot be reapproved"
            gate_path = (ROOT / review.get("local_shell_export_gate", "")).resolve()
            assert gate_path.is_file() and gate_path.is_relative_to(ROOT / "art"), "Affected asset needs a current exact-export paired-shell proof"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            proof = next(row for row in gate["assets"] if row["id"] == asset["id"])
            assert proof["sha256"] == current_sha and proof["passed"], "Local shell proof does not validate this actual model"
            assert proof["organs"] and all(organ["passed"] and organ["paired_top_bottom_outward_min"] > 0 for organ in proof["organs"])
    assert any(Path(entry["source"]).resolve() == model for entry in receipt), "Scene-source receipt is missing"
    for entry in receipt:
        assert hashlib.md5(Path(entry["source"]).read_bytes()).hexdigest() == entry["source_md5"], "Source changed after capture"
        assert hashlib.sha256(Path(entry["cache"]).read_bytes()).hexdigest() == entry["cache_sha256"], "Imported cache changed after capture"
    document = json.loads(model.read_text(encoding="utf-8"))
    refreshed_opacity = ROOT / "art/review/raw-opacity-revalidation-v3.json"
    if refreshed_opacity.exists():
        refreshed = json.loads(refreshed_opacity.read_text(encoding="utf-8"))
        current_sidecar = ROOT / refreshed["corrected_sidecar"]
        assert refreshed["passed"] and hashlib.sha256(current_sidecar.read_bytes()).hexdigest() == refreshed["corrected_sidecar_sha256"]
        current_proofs = json.loads(current_sidecar.read_text(encoding="utf-8"))["assets"]
        matching = [p for p in current_proofs if p["id"] == asset["id"] and p["sha256"] == hashlib.sha256(model.read_bytes()).hexdigest()]
        if matching:
            assert all(p["passed"] and p["actual_MASK_cutoff_all_contacts_passed"] and p["existing_gt_0_60_all_contacts_passed"] for p in matching)
    for dependency in document["asset"]["extras"]["render_dependency_sha256"]:
        assert hashlib.sha256((model.parent / unquote(dependency["uri"])).read_bytes()).hexdigest() == dependency["sha256"], "Stale sidecar seal"
    runtime = json.loads((base / "runtime-receipt.json").read_text(encoding="utf-8-sig"))
    assert not runtime.get("diagnostic_only"), "A runtime-control diagnostic cannot establish normal native art approval"
    assert hashlib.sha256(Path(runtime["native_library"]).read_bytes()).hexdigest() == runtime["native_sha256"], "Native renderer changed after capture"
    assert hashlib.sha256((ROOT / "native/src/tactical_level_viewer.cpp").read_bytes()).hexdigest() == runtime["viewer_source_sha256"], "Native source changed after capture"
    for index in range(4):
        output = (base / f"{prefix}-view-{index}.stdout.log").read_text(encoding="utf-8")
        assert f"TACTICAL_SOURCE_CHECK id={asset['id']} actual_triangles={asset['metrics']['triangles']} expected_triangles={asset['metrics']['triangles']} matched=true" in output, "Actual loaded geometry not verified"
    asset["status"] = "rebuilt_reviewed"
    asset["rebuild_status"] = "isolated_art_reviewed_live_bank_integration_pending" if isolated else "static_art_reviewed_runtime_behavior_pending" if review.get("static_art_only") else "complete"
    asset["godot_reviews"] = [capture.relative_to(ROOT).as_posix() for capture in captures]
    asset["quality_review"] = {"passed": True, "manual_review": args.review, "reviewer": review["reviewer"],
                               "scope": "isolated_asset_visual_export_review" if isolated else "static_art_only" if review.get("static_art_only") else "asset_visual_export_review",
                               "details": review["verified_details"], "source_limits": review["limitations"],
                               "export_validation": validation, "native_runtime": runtime,
                               "import_receipt": (base / "import-receipt.json").relative_to(ROOT).as_posix()}
    if refreshed_opacity.exists() and matching:
        asset["quality_review"]["refreshed_raw_opacity_proof"] = refreshed_opacity.relative_to(ROOT).as_posix()
    found.add(asset["id"])
assert found == selected, "Review identities are not in the catalog"
if isolated:
    catalog["isolated_model_art_approved_ids"] = sorted(asset["id"] for asset in catalog[asset_key]
        if asset.get("quality_review", {}).get("passed"))
    catalog["live_bank_promotion_performed"] = False
temporary = path.with_name(path.name+".pending")
temporary.write_text(json.dumps(catalog, indent=2)+"\n", encoding="utf-8")
temporary.replace(path)
print(f"Recorded completed manual visual review for {len(found)} explicitly selected assets.")
