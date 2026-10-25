# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/root_gate_batch.py (imported 2026-10-25)
# Changed: ROOT/PROJECT/GODOT via pipeline_paths; CAPTURE from $XCOM_CAPTURE_REVIEW_PS1 (default <game>/art/tools/CaptureGodotReview.ps1); SHEET and sibling tools resolved inside art-pipeline/tools; contact sheets run with cwd = game root
"""Root gate for an Opus worker batch: stage, import, capture four native angles, sheet.

Usage (PowerShell, from the repo root):
  python art/tools/root_gate_batch.py --batch urban23_opus --models ids_models.json
where ids_models.json is a list of {"id": "terrain/URBAN/050",
"model": "xcom-3d-godot/.../050.urban23-opus-v1.gltf"} objects (repo-relative).

Writes only new files: an isolated diagnostic catalog under the Godot project's
assets/review_diagnostics/<batch>/, art/review/<batch>-staging.json, captures under
art/review/godot/<id>/<batch>/ and art/review/verified_sheets/<batch>-<n>.png.
The main catalogs are never touched. Nothing here approves art.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import os as _os
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
PROJECT = pipeline_paths.path("godot_project")
GODOT = Path(pipeline_paths.setting("godot_exe"))  # was C:\GameDev\Godot_v4.7-stable_win64\Godot_v4.7-stable_win64.exe
# engine-side capture script (owned by the engine port, not in tools/review)
CAPTURE = Path(_os.environ.get("XCOM_CAPTURE_REVIEW_PS1") or ROOT / "art" / "tools" / "CaptureGodotReview.ps1")
SHEET = Path(__file__).resolve().parent / "review_contact_sheet.py"


def gltf_triangles(path):
    """Index count / 3 for every triangle primitive, matching the native check."""
    document = json.loads(path.read_text(encoding="utf-8"))
    total = 0
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            accessor = primitive.get("indices")
            count = document["accessors"][accessor]["count"] if accessor is not None else \
                document["accessors"][primitive["attributes"]["POSITION"]]["count"]
            total += count // 3
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--models", required=True)
    parser.add_argument("--skip-import", action="store_true")
    parser.add_argument("--only", default="", help="comma-separated ids to (re)capture")
    args = parser.parse_args()
    assert args.batch.replace("_", "").replace("-", "").isalnum()

    entries = json.loads(Path(args.models).read_text(encoding="utf-8-sig"))
    if isinstance(entries, dict):  # some workers wrap the list as {"root_gate": [...]}
        entries = entries["root_gate"]
    catalog = {a["id"]: a for a in json.loads((ROOT / "art/asset_catalog.json").read_text(encoding="utf-8"))["assets"]}
    staged, runtime = [], []
    for entry in entries:
        model = (ROOT / entry["model"]).resolve()
        assert model.is_relative_to(PROJECT / "assets"), model
        assert model.exists(), model
        source = dict(catalog[entry["id"]])
        source.pop("metrics", None)
        metrics = {"triangles": gltf_triangles(model)}
        res = "res://" + model.relative_to(PROJECT).as_posix()
        staged.append({**source, "model": res, "metrics": metrics})
        runtime.append({"id": entry["id"], "category": source["category"], "family": source.get("set"),
                        "source_label": source.get("source_label", ""),
                        "frame_semantics": source.get("frame_semantics", ""),
                        "model": res, "metrics": metrics,
                        "status": "isolated_preview_unapproved", "quality_passed": False})

    diag = PROJECT / "assets" / "review_diagnostics" / args.batch
    diag.mkdir(parents=True, exist_ok=True)
    (diag / "catalog.json").write_text(json.dumps({"schema": 1, "diagnostic_only": True, "assets": runtime}, indent=1), encoding="utf-8")
    staging = ROOT / "art" / "review" / f"{args.batch}-staging.json"
    staging.write_text(json.dumps({"schema": 1, "staged_assets": staged, "diagnostic_catalog": f"assets/review_diagnostics/{args.batch}/catalog.json",
                                   "main_catalogs_unchanged": True, "art_approved": False}, indent=1), encoding="utf-8")

    if not args.skip_import:
        log = ROOT / "art" / "review" / f"{args.batch}-import.log"
        with open(log, "w", encoding="utf-8") as handle:
            result = subprocess.run([str(GODOT), "--headless", "--path", str(PROJECT), "--import"],
                                    stdout=handle, stderr=subprocess.STDOUT, timeout=1800)
        print("import exit", result.returncode, log)
        # Texture import policy (VRAM + mipmaps, normal-map flag): concurrent scene-driven
        # texture reimports can reset a texture's options, so re-apply and import again.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "textures"))
        from texture_import_policy import run as texture_policy
        _, _, fixed = texture_policy()
        if fixed:
            with open(log, "a", encoding="utf-8") as handle:
                subprocess.run([str(GODOT), "--headless", "--path", str(PROJECT), "--import"],
                               stdout=handle, stderr=subprocess.STDOUT, timeout=1800)
            print("texture import policy re-applied to", fixed, "textures; imported again")

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "textures"))
    from root_independent_checks import check
    checks = [check(e["id"], e["model"]) for e in entries]
    (ROOT / "art" / "review" / f"{args.batch}-root-checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
    for c in checks:
        if not c["passed"]:
            print("CHECK-FAIL", c["id"], "; ".join(c["fails"]))
    print("independent checks:", sum(c["passed"] for c in checks), "/", len(checks), "pass")

    only = set(filter(None, args.only.split(",")))
    failures = []
    for entry in staged:
        if only and entry["id"] not in only:
            continue
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(CAPTURE),
                   "-Asset", entry["id"], "-ReviewTag", args.batch,
                   "-Catalog", f"assets/review_diagnostics/{args.batch}/catalog.json"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        ok = result.returncode == 0
        print(("OK  " if ok else "FAIL"), entry["id"], entry["metrics"]["triangles"])
        if not ok:
            failures.append(entry["id"])
            print(result.stdout[-1500:], result.stderr[-1500:])

    captured = [e["id"] for e in staged if e["id"] not in failures and (not only or e["id"] in only)]
    for n in range(0, len(captured), 5):
        chunk = captured[n:n + 5]
        # Partial re-captures get their own sheet name so the full batch sheet survives.
        name = f"{args.batch}-{'recap-' if only else ''}{n // 5 + 1}"
        subprocess.run([sys.executable, str(SHEET), "--ids", ",".join(chunk), "--name", name,
                        "--godot-tag", args.batch, "--catalog", staging.relative_to(ROOT).as_posix()],
                       check=True, cwd=str(ROOT))
    print("failures:", failures)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "textures"))  # compress_project_textures
    from godot_main_lock import main_lock
    from compress_project_textures import finalize_saved_assets
    # The finalizer takes the main lock itself (wait=0), so run it before root-gate holds it,
    # retrying while another process (e.g. a queued gate) holds the lock.
    import time
    for _ in range(240):
        try:
            finalize_saved_assets()
            break
        except TimeoutError:
            time.sleep(15)
    else:
        raise TimeoutError("Godot main-project lock stayed busy for an hour")
    # Serialize with any other process running Godot on the main project.
    with main_lock("root-gate"):
        main()
