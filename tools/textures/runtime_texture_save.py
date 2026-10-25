# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/runtime_texture_save.py (imported 2026-10-25)
# Changed: header only (PROJECT comes from compress_project_textures, which also puts tools/review on sys.path)
"""Finalize Blender exports with the host Python's verified lossless WebP pipeline."""
import os
from pathlib import Path
import shutil
import subprocess

from compress_project_textures import PROJECT, default_backup_dir, sources


def finalize_blender_export():
    if sources(PROJECT):
        python = os.environ.get("XCOM_TEXTURE_PYTHON") or shutil.which("python") or shutil.which("python3")
        if not python:
            raise RuntimeError("Set XCOM_TEXTURE_PYTHON to Python with art/tools/texture-requirements.txt installed")
        subprocess.run([python, str(Path(__file__).with_name("compress_project_textures.py")),
                        "--apply", "--allow-8bit", "--replace-existing",
                        "--backup-dir", str(default_backup_dir())], check=True)
    from deduplicate_project_textures import deduplicate
    from godot_main_lock import main_lock
    with main_lock("texture-export-sharing", wait=0):
        deduplicate(PROJECT, apply=True)
    relink_runtime_images()


def relink_runtime_images():
    """Repair older Blender sources that still name converted runtime PNGs."""
    import bpy
    import json
    from deduplicate_project_textures import ALIASES
    aliases_path = PROJECT / ALIASES
    aliases = json.loads(aliases_path.read_text()) if aliases_path.exists() else {}
    for image in bpy.data.images:
        if not image.filepath:
            continue
        old = Path(bpy.path.abspath(image.filepath)).resolve()
        if old.is_relative_to(PROJECT.resolve()) and not old.exists():
            new = old.with_suffix(".webp") if old.suffix.lower() == ".png" else old
            if not new.exists():
                alias = aliases.get(new.relative_to(PROJECT.resolve()).as_posix())
                if alias:
                    new = PROJECT / alias
            if new.exists():
                image.filepath = str(new)
