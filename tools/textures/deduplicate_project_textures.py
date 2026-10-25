# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/deduplicate_project_textures.py (imported 2026-10-25)
# Changed: header only (ROOT/PROJECT come from compress_project_textures)
"""Share byte-identical runtime textures with identical Godot import settings.

Preview by default; --apply backs up files outside the repo before relinking and
removing copies. Shared files live in assets/textures/shared/<content+settings hash>/.
Treat these as immutable: export edits to a new file, then run this again.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import quote

from compress_project_textures import (PROJECT, ROOT, TEXT_EXTENSIONS, atomic_write,
                                      backup_file, default_backup_dir, resolve_reference)

EXTENSIONS = {".webp", ".png", ".jpg", ".jpeg", ".tga", ".bmp"}
ALIASES = "assets/texture_aliases.json"


def import_settings(path):
    sidecar = Path(str(path) + ".import")
    if not sidecar.exists():
        return None  # Import first; never assume defaults match existing settings.
    text = sidecar.read_text(encoding="utf-8-sig")
    header, params = text.split("[params]", 1)
    types = re.findall(r'(?m)^(?:importer|type)=.*$', header)
    return "\n".join(types + sorted(line.strip() for line in params.splitlines() if line.strip()))


def plan(project):
    shared = project / "assets/textures/shared"
    groups = defaultdict(list)
    for path in sorted((project / "assets").rglob("*")):
        if path.suffix.lower() not in EXTENSIONS or not path.is_file():
            continue
        settings = import_settings(path)
        if settings is None:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        key = (digest, settings, path.suffix.lower())
        groups[key].append(path)
    mapping, copies, records = {}, {}, []
    for (digest, settings, extension), paths in groups.items():
        if len(paths) < 2:
            continue
        existing = [p for p in paths if p.is_relative_to(shared)]
        representative = min(paths, key=lambda p: (not p.is_relative_to(project / "assets/textures"), len(p.parts), str(p)))
        identity = hashlib.sha256((digest + settings + extension).encode()).hexdigest()
        target = min(existing) if existing else shared / identity / representative.name
        if not existing:
            copies[target] = representative
        for source in paths:
            if source != target:
                mapping[source] = target
        records.append({"shared": target.relative_to(project).as_posix(), "sha256": digest,
                        "sources": [p.relative_to(project).as_posix() for p in paths],
                        "saved_bytes": (len(paths) - 1) * representative.stat().st_size})
    return mapping, copies, records


def rewrite(text, path, project, mapping, uids):
    def replace(match):
        delimiter, value = match.group(1), match.group(2)
        fields = value.split("|")
        for i, field in enumerate(fields):
            if field in uids:
                fields[i] = uids[field]
                continue
            if Path(field).suffix.lower() not in EXTENSIONS:
                continue
            source = resolve_reference(field, path.parent, project)
            target = mapping.get(source)
            if target is None:
                continue
            if field.startswith("res://"):
                fields[i] = "res://" + target.relative_to(project).as_posix()
            elif field.startswith("xcom-3d-godot/"):
                fields[i] = target.relative_to(ROOT).as_posix()
            elif Path(field).is_absolute():
                fields[i] = target.as_posix()
            else:
                relative = os.path.relpath(target, path.parent).replace("\\", "/")
                fields[i] = quote(relative, safe="/.-_") if path.suffix == ".gltf" else relative
        return delimiter + "|".join(fields) + delimiter
    return re.sub(r'''(["'])([^"'\r\n]*)\1''', replace, text)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Relinking would collapse a JSON key/layer signature: {key}")
        result[key] = value
    return result


def deduplicate(project=PROJECT, backup=None, apply=False):
    project = project.resolve()
    mapping, copies, records = plan(project)
    report = {"groups": records, "removed_files": len(mapping), "created_files": len(copies),
              "saved_bytes": sum(r["saved_bytes"] for r in records), "metadata_updated": []}
    if not mapping:
        return report
    uids = {}
    def uid(p):
        text = Path(str(p) + ".import").read_text(encoding="utf-8-sig")
        match = re.search(r'(?m)^uid="([^"]+)"', text)
        return match.group(1) if match else None
    for source, target in mapping.items():
        old, new = uid(source), uid(copies.get(target, target))
        if old and new:
            uids[old] = new
    updates = {}
    # Preflight every reference before creating files or removing originals.
    for path in sorted(project.rglob("*")):
        if (not path.is_file() or ".godot" in path.parts
                or path.suffix not in TEXT_EXTENSIONS | {".import"}
                or path == project / ALIASES
                or (path.suffix == ".import" and Path(str(path)[:-7]) in mapping)):
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        updated = rewrite(text, path, project, mapping, uids)
        if updated != text:
            if path.suffix in {".gltf", ".json"}:
                # Sealed dependency URIs change alongside images; byte hashes stay valid.
                json.loads(updated, object_pairs_hook=unique_object)
            updates[path] = updated.encode("utf-8")
    report["metadata_updated"] = [p.relative_to(project).as_posix() for p in updates]
    if not apply:
        return report
    backup = Path(backup).resolve() if backup else default_backup_dir().resolve()
    if backup.is_relative_to(ROOT.resolve()) or backup.is_relative_to(project):
        raise ValueError("Backup must be outside the repository/project")
    backup.mkdir(parents=True, exist_ok=False)
    aliases_path = project / ALIASES
    aliases = json.loads(aliases_path.read_text()) if aliases_path.exists() else {}
    for old, target in list(aliases.items()):
        resolved = mapping.get(project / target)
        if resolved:
            aliases[old] = resolved.relative_to(project).as_posix()
    aliases.update({p.relative_to(project).as_posix(): t.relative_to(project).as_posix()
                    for p, t in mapping.items()})
    updates[aliases_path] = (json.dumps(aliases, indent=2, sort_keys=True) + "\n").encode()
    for path in list(mapping) + [Path(str(p) + ".import") for p in mapping] + list(updates):
        if path.exists():
            backup_file(path, project, backup)
            if (backup / path.relative_to(project)).read_bytes() != path.read_bytes():
                raise ValueError(f"Backup verification failed: {path}")
    for target, source in copies.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError(f"Unexpected shared destination: {target}")
        atomic_write(target, source.read_bytes())
        text = Path(str(source) + ".import").read_text(encoding="utf-8-sig")
        old_uri = "res://" + source.relative_to(project).as_posix()
        new_uri = "res://" + target.relative_to(project).as_posix()
        text = text.replace(old_uri, new_uri)
        # Godot's import cache key is the MD5 of its resource URI.
        text = text.replace(hashlib.md5(old_uri.encode()).hexdigest(), hashlib.md5(new_uri.encode()).hexdigest())
        atomic_write(Path(str(target) + ".import"), text.encode())
    for path, data in updates.items():
        atomic_write(path, data)
    report["backup"] = str(backup)
    atomic_write(backup / "deduplication-report.json", (json.dumps(report, indent=2) + "\n").encode())
    for source, target in mapping.items():
        if not source.is_relative_to(project / "assets") or source.read_bytes() != target.read_bytes():
            raise ValueError(f"Shared texture verification failed: {source}")
        source.unlink()
        Path(str(source) + ".import").unlink()
    # Cached scenes still contain the removed texture UIDs. Archive those scenes
    # and the editor dependency index so reimport reads the new source paths.
    cache = project / ".godot"
    stale = {cache / "editor/filesystem_cache10"}
    for path in updates:
        sidecar = Path(str(path) + ".import")
        if path.suffix != ".gltf" or not sidecar.exists():
            continue
        for uri in re.findall(r'"(res://\.godot/imported/[^"]+)"', sidecar.read_text(encoding="utf-8-sig")):
            resource = (project / uri[6:]).resolve()
            if not resource.is_relative_to(cache):
                raise ValueError(f"Import cache path escapes project cache: {resource}")
            stale.update({resource, resource.with_suffix(".md5")})
    for path in stale:
        if path.exists():
            destination = backup / "_generated_cache" / path.relative_to(cache)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    if args.apply:
        from godot_main_lock import main_lock
        with main_lock("texture-deduplication", wait=0):
            report = deduplicate(args.project, args.backup_dir, True)
    else:
        report = deduplicate(args.project)
    print(json.dumps({k: v for k, v in report.items() if k not in {"groups", "metadata_updated"}}, indent=2))
    print(f"{len(report['groups'])} shared groups; {len(report['metadata_updated'])} reference files updated/planned")


if __name__ == "__main__":
    main()
