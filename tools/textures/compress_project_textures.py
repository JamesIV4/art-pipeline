# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/compress_project_textures.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT, PROJECT = pipeline_paths.path('godot_project'); tools/review on sys.path for godot_main_lock
"""Finalize runtime textures as lossless WebP and repair their Godot/glTF references.

Requires Pillow: python -m pip install -r art/tools/texture-requirements.txt
Preview: python art/tools/compress_project_textures.py
Apply:   python art/tools/compress_project_textures.py --apply --allow-8bit --backup-dir <outside-repo>

PNG originals and changed metadata are backed up outside the repository. Encoding is
lossless for 8-bit input, including RGB under transparent pixels. 16-bit RGB/RGBA
input requires --allow-8bit and is decoded by Godot to preserve its runtime pixels.
Generated .godot caches are never source assets and are already ignored by Git.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid
from urllib.parse import unquote

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "review"))  # godot_main_lock.py
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
PROJECT = pipeline_paths.path("godot_project")
TEXT_EXTENSIONS = {".gltf", ".json", ".gd", ".tscn", ".tres", ".godot", ".gdshader"}


def sources(project):
    return sorted(p for p in project.rglob("*") if p.is_file()
                  and p.suffix.lower() == ".png" and ".godot" not in p.parts)


def png_depth(path):
    with path.open("rb") as handle:
        header = handle.read(26)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a PNG: {path}")
    return header[24], header[25]


def encode(path, allow_8bit=False, normalized=None):
    from PIL import Image
    depth, color = png_depth(path)
    if depth > 8 and not allow_8bit:
        raise ValueError(f"16-bit PNG requires --allow-8bit: {path}")
    if depth > 8 and color not in (2, 6):
        raise ValueError(f"Unsupported 16-bit grayscale conversion: {path}")
    if depth > 8 and normalized is None:
        raise ValueError(f"16-bit input must first be decoded by Godot: {path}")
    with Image.open(normalized or path) as image:
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError(f"Animated PNG is not a static texture: {path}")
        # Godot performs its own 16-to-8-bit/gamma conversion before this step.
        rgba = image.convert("RGBA")
        if max(rgba.size) > 16383:
            raise ValueError(f"Exceeds WebP's 16383-pixel dimension limit: {path}")
        output = io.BytesIO()
        rgba.save(output, format="WEBP", lossless=True, exact=True, method=4)
        data = output.getvalue()
        with Image.open(io.BytesIO(data)) as decoded:
            if decoded.size != rgba.size or decoded.convert("RGBA").tobytes() != rgba.tobytes():
                raise ValueError(f"Pixel verification failed: {path}")
    return data, depth


def atomic_write(path, data):
    temporary = path.with_name(path.name + ".texture-tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def backup_file(path, project, backup):
    destination = backup / path.relative_to(project)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(path, destination)


def resolve_reference(value, parent, project):
    if value.startswith("res://"):
        return (project / unquote(value[6:])).resolve()
    if value.startswith(("data:", "http:", "https:")):
        return None
    decoded = unquote(value)
    try:
        if decoded.startswith("xcom-3d-godot/"):
            return (ROOT / decoded).resolve()
        return (parent / decoded).resolve()
    except OSError:
        # e.g. escaped "\\..\\x.png" strings in legacy extras resolve as UNC paths
        return None


def rewrite_references(text, path, project, mapping):
    # Only exact quoted paths resolving to a converted source are changed.
    def replace(match):
        value = match.group(1)
        # Layered-material signatures contain several URI fields separated by |.
        fields = value.split("|")
        for i, field in enumerate(fields):
            if field.lower().endswith(".png") and resolve_reference(field, path.parent, project) in mapping:
                fields[i] = field[:-4] + ".webp"
        return '"' + "|".join(fields) + '"'
    return re.sub(r'"([^"\n]*\.[pP][nN][gG][^"\n]*)"', replace, text)


def fix_gltf(document, path):
    webp_images = {i for i, image in enumerate(document.get("images", []))
                   if image.get("uri", "").lower().endswith(".webp")}
    for i in webp_images:
        document["images"][i]["mimeType"] = "image/webp"
    for texture in document.get("textures", []):
        index = texture.get("source")
        if index in webp_images:
            texture.setdefault("extensions", {})["EXT_texture_webp"] = {"source": index}
            del texture["source"]
    if webp_images:
        for key in ("extensionsUsed", "extensionsRequired"):
            if "EXT_texture_webp" not in document.setdefault(key, []):
                document[key].append("EXT_texture_webp")
    extras = document.get("asset", {}).get("extras", {})
    if "render_dependency_sha256" in extras:
        extras["render_dependency_sha256"] = [
            {"uri": entry["uri"], "sha256": hashlib.sha256(
                (path.parent / unquote(entry["uri"])).read_bytes()).hexdigest()}
            for entry in document.get("buffers", []) + document.get("images", [])
            if "uri" in entry and not entry["uri"].startswith("data:")]


def find_godot():
    override = os.environ.get("GODOT")
    if override:
        return override
    for name in ("godot", "godot4"):
        found = shutil.which(name)
        if found:
            return found
    for path in Path("C:/GameDev").glob("Godot*/*console.exe"):
        return str(path)
    raise ValueError("Godot is required for 16-bit conversion; set the GODOT environment variable")


def normalize_16bit(pngs, project, backup):
    jobs = []
    outputs = {}
    for source in pngs:
        if png_depth(source)[0] <= 8:
            continue
        target = backup / "_runtime8" / source.relative_to(project)
        target.parent.mkdir(parents=True, exist_ok=True)
        jobs.append([source.as_posix(), target.as_posix()])
        outputs[source] = target
    if jobs:
        script = backup / "normalize_16bit.gd"
        script.write_text('extends SceneTree\nfunc _initialize():\n'
                          '    var jobs = ' + json.dumps(jobs) + '\n'
                          '    for pair in jobs:\n'
                          '        var image = Image.load_from_file(pair[0])\n'
                          '        if image == null or image.save_png(pair[1]) != OK:\n'
                          '            push_error("16-bit normalization failed: " + pair[0])\n'
                          '            quit(1)\n            return\n'
                          '    print("Normalized ", jobs.size(), " 16-bit textures")\n'
                          '    quit(0)\n', encoding="utf-8")
        subprocess.run([find_godot(), "--headless", "--path", str(backup),
                        "--script", str(script)], check=True, timeout=600)
    return outputs


def default_backup_dir():
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".cache")))
    return base / "Xcom3D/texture-backups" / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])


def finalize_saved_assets():
    """Python asset/review pipelines call this before importing newly saved assets."""
    from godot_main_lock import main_lock
    with main_lock("texture-save-finalizer", wait=0):
        result = migrate(PROJECT, default_backup_dir(), allow_8bit=True, replace_existing=True) if sources(PROJECT) else None
        from deduplicate_project_textures import deduplicate
        deduplicate(PROJECT, apply=True)
        return result


def migrate(project=PROJECT, backup=None, allow_8bit=False, workers=4, replace_existing=False):
    project = project.resolve()
    backup = Path(backup).resolve() if backup else None
    if backup is None or backup.is_relative_to(ROOT.resolve()) or backup.is_relative_to(project):
        raise ValueError("A backup directory outside the repository is required")
    backup.mkdir(parents=True, exist_ok=True)
    pngs = sources(project)
    if not pngs:
        return {"textures": [], "source_bytes": 0, "webp_bytes": 0, "metadata_updated": []}
    mapping = {p.resolve(): p.with_suffix(".webp").resolve() for p in pngs}
    # Preflight the whole batch before creating outputs or changing references.
    for source in pngs:
        if png_depth(source)[0] > 8 and not allow_8bit:
            raise ValueError(f"16-bit PNG requires --allow-8bit: {source}")
    normalized = normalize_16bit(pngs, project, backup)
    receipts = []
    # Identical PNGs are common in versioned material sets; encode each once.
    groups = {}
    for source in pngs:
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        groups.setdefault(digest, []).append(source)
    def convert(group):
        data, depth = encode(group[0], allow_8bit, normalized.get(group[0]))
        result = []
        for source in group:
            target = source.with_suffix(".webp")
            if target.exists() and target.read_bytes() != data:
                if not replace_existing:
                    raise ValueError(f"Conflicting WebP already exists: {target}")
                backup_file(target, project, backup)
                atomic_write(target, data)
            elif not target.exists():
                atomic_write(target, data)
            result.append({"source": source.relative_to(project).as_posix(),
                           "target": target.relative_to(project).as_posix(),
                           "source_bytes": source.stat().st_size, "webp_bytes": len(data),
                           "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                           "webp_sha256": hashlib.sha256(data).hexdigest(),
                           "source_bit_depth": depth, "verified_8bit_rgba": True})
        return result
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(convert, groups.values()):
            receipts.extend(result)
            if len(receipts) % 50 < len(result):
                print(f"Encoded and verified {len(receipts)}/{len(pngs)} textures", flush=True)
    edited = []
    for path in sorted(project.rglob("*")):
        if not path.is_file() or ".godot" in path.parts or path.suffix not in TEXT_EXTENSIONS:
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        updated = rewrite_references(text, path, project, mapping)
        if path.suffix == ".gltf":
            document = json.loads(updated)
            affected = updated != text or any(
                resolve_reference(image.get("uri", ""), path.parent, project) in mapping.values()
                for image in document.get("images", []) if "uri" in image)
            if affected:
                fix_gltf(document, path)
                updated = json.dumps(document, indent=2) + "\n"
        if updated != text:
            backup_file(path, project, backup)
            atomic_write(path, updated.encode("utf-8"))
            edited.append(path.relative_to(project).as_posix())
    # Retain UIDs, array slice counts, and unrelated import settings.
    for source in pngs:
        sidecar = Path(str(source) + ".import")
        if sidecar.exists():
            target = Path(str(source.with_suffix(".webp")) + ".import")
            if target.exists():
                if not replace_existing:
                    raise ValueError(f"Conflicting import sidecar: {target}")
                # Keep the already published WebP UID/settings for asset updates.
                continue
            backup_file(sidecar, project, backup)
            text = sidecar.read_text(encoding="utf-8-sig")
            text = text.replace(source.name, source.with_suffix(".webp").name)
            text = re.sub(r"(?m)^compress/mode=.*$", "compress/mode=0", text)
            text = re.sub(r"(?m)^detect_3d/compress_to=.*$", "detect_3d/compress_to=0", text)
            atomic_write(target, text.encode("utf-8"))
    report = {"schema": 1, "project": str(project), "backup": str(backup),
              "textures": receipts, "metadata_updated": edited,
              "source_bytes": sum(r["source_bytes"] for r in receipts),
              "webp_bytes": sum(r["webp_bytes"] for r in receipts)}
    atomic_write(backup / "conversion-report.json", (json.dumps(report, indent=2) + "\n").encode())
    # Archive originals only after all encoding and reference updates succeed.
    for source in pngs:
        backup_file(source, project, backup)
        if (backup / source.relative_to(project)).read_bytes() != source.read_bytes():
            raise ValueError(f"Backup verification failed: {source}")
        source.unlink()
        Path(str(source) + ".import").unlink(missing_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-8bit", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--replace-existing", action="store_true",
                        help="Finalize deliberately re-exported textures; back up existing WebP before replacing")
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if not args.apply:
        pngs = sources(args.project)
        print(f"{len(pngs)} PNGs, {sum(p.stat().st_size for p in pngs):,} bytes; "
              f"{sum(png_depth(p)[0] > 8 for p in pngs)} require 16-to-8-bit conversion")
        return
    if not args.backup_dir:
        parser.error("--apply requires --backup-dir outside the repository")
    from godot_main_lock import main_lock
    with main_lock("texture-webp-migration", wait=0):
        report = migrate(args.project, args.backup_dir, args.allow_8bit, args.workers, args.replace_existing)
    print(f"Converted {len(report['textures'])} PNGs: {report['source_bytes']:,} -> {report['webp_bytes']:,} bytes")
    print(f"Backup and verification report: {args.backup_dir}")


if __name__ == "__main__":
    main()
