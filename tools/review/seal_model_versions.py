# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/seal_model_versions.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT; model path = <godot_project>/assets/models/<id>.gltf
"""Bind separate glTF buffers/images to the scene source hash for fresh imports."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT


def seal(path):
    document = json.loads(path.read_text(encoding="utf-8"))
    dependencies = []
    for entry in document.get("buffers", [])+document.get("images", []):
        uri = entry["uri"]
        assert not uri.startswith("data:"), "This contract expects separate external resources"
        content = (path.parent / unquote(uri)).read_bytes()
        dependencies.append({"uri": uri, "sha256": hashlib.sha256(content).hexdigest()})
    extras = document.setdefault("asset", {}).setdefault("extras", {})
    if extras.get("render_dependency_sha256") != dependencies:
        extras["render_dependency_sha256"] = dependencies
        path.write_text(json.dumps(document, indent=2)+"\n", encoding="utf-8")
    return dependencies


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", required=True)
    args = parser.parse_args()
    for asset_id in args.ids.split(","):
        path = pipeline_paths.path("godot_project") / f"assets/models/{asset_id}.gltf"
        print(asset_id, len(seal(path)), "external resource hashes sealed")
