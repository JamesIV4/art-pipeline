# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/quarantine_failed_validation.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT; catalog = pipeline_paths.path('catalog')
"""Withdraw current approval when a stricter export audit exposes defects."""
import json
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
report = json.loads((ROOT / "art/review/rebuilt_validation.json").read_text(encoding="utf-8"))
failed = {item["id"]: item["error"] for item in report["errors"]}
path = pipeline_paths.path("catalog")
catalog = json.loads(path.read_text(encoding="utf-8"))
for asset in catalog["assets"]:
    if asset["id"] not in failed:
        continue
    asset["prior_quality_review"] = asset.get("quality_review")
    asset["quality_review"] = {"passed": False, "remaining": failed[asset["id"]], "prior_visual_evidence_retained": True}
    asset["status"] = "rebuilt_needs_export_repair"
    asset["rebuild_status"] = "numerical_export_repair_pending"
temporary = path.with_name(path.name+".pending")
temporary.write_text(json.dumps(catalog, indent=2)+"\n", encoding="utf-8")
temporary.replace(path)
print(f"Withdrew approval for {len(failed)} assets pending export repair and fresh reviews.")
