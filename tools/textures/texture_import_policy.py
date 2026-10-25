# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/texture_import_policy.py (imported 2026-10-25)
# Changed: ASSETS = <godot_project>/assets via pipeline_paths
"""Lossless texture import policy for the main Godot project.

Runtime source textures are lossless WebP (compress_project_textures.py).
Godot caches are ignored by Git. Keep 3D mipmaps and normal-map detection,
but do not enable VRAM compression or let Detect 3D override Lossless.
Only policy parameters are changed; UIDs and array slice counts are retained.

  python art/tools/texture_import_policy.py
  python art/tools/texture_import_policy.py --check
"""
import argparse
import re
import sys
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
ASSETS = pipeline_paths.path("godot_project") / "assets"
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tga", ".bmp"}


def wanted(source: Path):
    normal = "_normal" in source.stem.lower()
    return {"compress/mode": "0", "mipmaps/generate": "true", "mipmaps/limit": "-1",
            "detect_3d/compress_to": "0", "compress/normal_map": "1" if normal else "0"}


def apply(path: Path, check: bool):
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    if not re.search(r'(?m)^importer="(?:texture|2d_array_texture)"\r?$', text):
        return None
    source = Path(str(path)[:-len(".import")])
    target = wanted(source)
    if 'importer="2d_array_texture"' in text:
        target.pop("compress/normal_map")
        target.pop("detect_3d/compress_to")
    lines = text.split("\n")
    changed = {}
    in_params = False
    seen = set()
    for i, line in enumerate(lines):
        if line.startswith("["):
            in_params = line.strip() == "[params]"
            continue
        if in_params and "=" in line:
            key, value = line.split("=", 1)
            if key in target:
                seen.add(key)
                if value != target[key]:
                    changed[key] = (value, target[key])
                    lines[i] = f"{key}={target[key]}"
    missing = [k for k in target if k not in seen]
    if missing:
        raise SystemExit(f"{path}: [params] lacks {missing}; import it once before applying the policy")
    if changed and not check:
        path.write_bytes("\n".join(lines).encode("utf-8"))
    return changed


def run(check=False):
    """Apply (or check) the policy on every texture import; returns (textures, normal maps, changed)."""
    total = normal = changed = 0
    for path in sorted(ASSETS.rglob("*.import")):
        if Path(str(path)[:-len(".import")]).suffix.lower() not in EXTENSIONS:
            continue
        result = apply(path, check)
        if result is None:
            continue
        total += 1
        normal += "_normal" in path.name.lower()
        if result:
            changed += 1
    return total, normal, changed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    total, normal, changed = run(args.check)
    print(f"textures {total} (normal maps {normal}); {'would change' if args.check else 'changed'} {changed}")
    if args.check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
