"""Origin: S:/Repos/trick-or-treat/art/tools/publish_catalog.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. Published fields are the publish_fields setting.

Publishes gate-passing assets to the game's catalog (published_catalog, default game/assets/catalog.json).

    python <pipeline>/tools/publish_catalog.py      (from the game root, or set ART_GAME_ROOT)

Only assets whose export exists and passes every cheap gate are published; the generator falls
back to placeholders for the rest. Prints a summary and exits 1 if anything failed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates  # noqa: E402
import pipeline_paths as P  # noqa: E402

OUT = P.path("published_catalog")
FIELDS = tuple(P.setting("publish_fields"))


def main():
    published, failed, missing = [], [], []
    for asset in gates.CATALOG:
        result = gates.check(asset)
        if result["fails"] == ["missing export"]:
            missing.append(asset["id"])
            continue
        if not result["pass"]:
            failed.append((asset["id"], result["fails"]))
            continue
        published.append({k: asset[k] for k in FIELDS if k in asset})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"assets": published}, indent=1))
    print(f"published {len(published)} assets -> {OUT}")
    for aid, fails in failed:
        print(f"  FAIL {aid}: {'; '.join(fails)}")
    if missing:
        print(f"  not exported yet: {', '.join(missing)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
