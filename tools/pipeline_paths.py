"""Per-game path resolution shared by every art-pipeline tool.

Origin: art-pipeline original (2026-10-25). Replaces the `ROOT = Path(__file__).parents[2]`
constants the tools had while they lived inside S:/Repos/trick-or-treat/art/tools.

The pipeline repo holds tools; a *game repo* holds the data (palette spec, catalog, build
scripts) and receives the outputs (palette textures, models, review sheets). Every tool works on
one game at a time. The game root is resolved in this order:

  1. the ART_GAME_ROOT environment variable,
  2. the nearest folder at or above the current working directory that contains
     art/pipeline.json,
  3. the current working directory.

Paths inside the game come from <game>/art/pipeline.json:

    {
      "paths":  { "models_out": "godot/assets/models", ... },
      "settings": { "cpp_namespace": "mygame", ... }
    }

Every key is optional; missing keys use DEFAULT_PATHS / DEFAULT_SETTINGS below, which reproduce
the trick-or-treat layout (the reference layout, see docs/game-layout.md). Set a path to null to
disable that output (for example "native_header_dir": null for a game without C++).

Inside Blender (`blender --background --python build.py`) the same rules apply, so run Blender
with the game root as the working directory, or set ART_GAME_ROOT first.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PATHS = {
    # inputs (art side)
    "palette_spec": "art/palette/palette.json",
    "materials_spec": "art/materials/materials.json",
    "materials_source": "art/materials/source",
    "catalog": "art/asset_catalog.json",
    "vfx_frames": "art/vfx/_frames",
    # outputs (engine side)
    "palette_out": "game/assets/palette",
    "materials_out": "game/assets/materials",
    "models_out": "game/assets/models",
    "published_catalog": "game/assets/catalog.json",
    "vfx_out": "game/assets/vfx",
    "sfx_out": "game/assets/sfx",
    "music_out": "game/assets/music",
    "toon_material": "game/materials/toon.tres",
    "native_header_dir": "native/src/mesh",
    # review
    "review_sheets": "art/review/sheets",
    "review_engine": "art/review/engine",
    "review_captures": "art/review/captures",
    "materials_preview": "art/materials/preview.png",
    # engine
    "godot_project": "game",
}

DEFAULT_SETTINGS = {
    "cpp_namespace": "tot",            # namespace prefix for generated C++ headers (<ns>::pal, <ns>::mat)
    "palette_grid": 16,
    # Godot res:// paths written into the generated toon material
    "toon_shader_res": "res://shaders/toon.gdshader",
    "palette_res": "res://assets/palette/palette.png",
    "palette_emit_res": "res://assets/palette/palette_emit.png",
    "albedo_array_res": "res://assets/materials/albedo_array.png",
    "normal_array_res": "res://assets/materials/normal_array.png",
    # gates
    "floating_prefixes": ["candy/", "sky/"],
    "floating_ids": ["paper_lantern", "porch_lantern", "string_bulb"],
    "ground_tolerance_m": 0.03,
    # catalog fields copied into the published (engine) catalog
    "publish_fields": ["id", "path", "collision", "walkable", "radius", "height", "collision_top",
                       "bounce", "candy_tier", "glow"],
    # review sheet scale figure (a post the height of the hero character)
    "scale_figure_height_m": 1.1,
    "scale_figure_color": "dragon_teal",
    # glTF scene-extras key stamped with a build id so Godot re-imports every rebuild
    "build_stamp_key": "tot_build",
    # executables (override per machine with the env vars named in docs/toolchain.md)
    "blender_exe": r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    "godot_exe": r"C:\GameDev\Godot_v4.7-stable_win64\Godot_v4.7-stable_win64_console.exe",
}


def _find_game_root() -> Path:
    env = os.environ.get("ART_GAME_ROOT")
    if env:
        return Path(env).resolve()
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        if (d / "art" / "pipeline.json").exists():
            return d
    return here


GAME_ROOT = _find_game_root()
_CONFIG_FILE = GAME_ROOT / "art" / "pipeline.json"
_CONFIG = json.loads(_CONFIG_FILE.read_text()) if _CONFIG_FILE.exists() else {}
PATHS = {**DEFAULT_PATHS, **_CONFIG.get("paths", {})}
SETTINGS = {**DEFAULT_SETTINGS, **_CONFIG.get("settings", {})}
if os.environ.get("BLENDER_EXE"):
    SETTINGS["blender_exe"] = os.environ["BLENDER_EXE"]
if os.environ.get("GODOT_EXE"):
    SETTINGS["godot_exe"] = os.environ["GODOT_EXE"]


def path(key: str) -> Path | None:
    """Absolute path for a layout key, or None when the game disabled it (null in pipeline.json)."""
    rel = PATHS[key]
    if rel is None:
        return None
    p = Path(rel)
    return p if p.is_absolute() else GAME_ROOT / p


def setting(key: str):
    return SETTINGS[key]


def describe() -> str:
    lines = [f"game root: {GAME_ROOT}", f"config:    {_CONFIG_FILE if _CONFIG_FILE.exists() else '(none, defaults)'}"]
    lines += [f"  {k:<20} {path(k)}" for k in PATHS]
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe())
