# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/scene_import_policy.py (imported 2026-10-25)
# Changed: ASSETS = <godot_project>/assets via pipeline_paths
"""Scene (glTF) import policy for the MAIN Godot project (renderer LOD study, 2026-10-02).

Terrain scenes (assets/models/terrain/**) import with meshes/generate_lods=false.
Godot's generated LODs crack the seams of multi-tile pieces cut on tile planes (XBASE2
radar dish 000-008, large radar 009-012, U_EXT02 hull edges) and make concave faces
shadow themselves (the LOD'd shadow caster pokes through the full-detail surface).
Cost of no LODs on the heaviest maps (art/review/renderer_lod/REPORT.md): draws and
CPU unchanged, GPU +0.05-0.2 ms at play zoom, +0.4-1.3 ms whole-map zoom (RTX 5060 Ti).
Shadow meshes (meshes/create_shadow_meshes=true) stay on.

STOPPED by the user on 2026-10-02: the policy covers only XBASE1, XBASE2, U_EXT02, U_BITS and
UFO1 (FAMILIES below). Nothing else is touched. There is no project importer default
(it was tried and rolled back), so NEW files in those families import with LODs ON
until this script is run again for them. Only the listed [params] keys are rewritten;
an edited .import makes Godot reimport exactly that file on the next --import.
Idempotent; reports what it changed.

  python art/tools/scene_import_policy.py                    # apply (all terrain + units)
  python art/tools/scene_import_policy.py --family XBASE2    # one terrain family only
  python art/tools/scene_import_policy.py --check            # report only, exit 1 if anything differs

Hold the main-project Godot lock (art/tools/godot_main_lock.py) while applying and
importing: root_gate_batch.py and layered_refresh.py call run() under their lock.
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
SCENE_SUFFIXES = (".gltf.import", ".glb.import")
POLICY = {  # folder under assets/ -> [params] values
    "models/terrain": {"meshes/generate_lods": "false", "meshes/create_shadow_meshes": "true"},
}
# STOPPED 2026-10-02 (user): LODs are off only for these families; do not extend.
# A bare run touches only them; --family may name another folder explicitly.
FAMILIES = ("XBASE1", "XBASE2", "U_EXT02", "U_BITS", "UFO1")


def apply(path: Path, target: dict, check: bool):
    text = path.read_bytes().decode("utf-8-sig")
    if not re.search(r'(?m)^importer="scene"$', text):
        return None
    lines = text.split("\n")
    changed, seen, in_params = {}, set(), False
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


def run(check=False, family=None):
    """Apply (or check) the policy; returns (scene imports, changed, changed paths)."""
    total, changed_paths = 0, []
    target = POLICY["models/terrain"]
    for fam in ([family] if family else FAMILIES):
        base = ASSETS / "models" / "terrain" / fam
        for path in sorted(p for p in base.rglob("*.import") if p.name.endswith(SCENE_SUFFIXES)):
            result = apply(path, target, check)
            if result is None:
                continue
            total += 1
            if result:
                changed_paths.append(path)
    return total, len(changed_paths), changed_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--family", default=None, help="terrain family folder only (e.g. XBASE2)")
    args = parser.parse_args()
    if args.family:
        assert re.fullmatch(r"[A-Z0-9_]+", args.family), args.family
    total, changed, _ = run(args.check, args.family)
    print(f"scene imports {total}; {'would change' if args.check else 'changed'} {changed}")
    if args.check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
