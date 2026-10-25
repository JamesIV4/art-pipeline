# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/catalog_reference.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT, PROJECT = pipeline_paths.path('godot_project'), catalog = pipeline_paths.path('catalog')
"""Decode the local UFO reference into individually identified modeling references.

Uses the same PCK framing, palette correction and 62-byte MCD layout as OXCE.
Original files are read only. Run with the system Python (Pillow + PyYAML).
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import struct

from PIL import Image, ImageDraw, ImageFont
import yaml
from renderer_reference import FACINGS, unit_references

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
PROJECT = pipeline_paths.path("godot_project")
PARTS = ("floor", "west_wall", "north_wall", "object")


def save_png(image: Image.Image, path: Path) -> None:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    content = buffer.getvalue()
    if path.exists() and path.read_bytes() == content:
        return
    temporary = path.with_name(path.name+".pending")
    temporary.write_bytes(content)
    temporary.replace(path)


def palette(reference: Path, battlescape: bool = True) -> list[tuple[int, ...]]:
    raw = (reference / "GEODATA/PALETTES.DAT").read_bytes()
    # Each palette is 768 color bytes plus a six-byte trailer (Palette::palOffset).
    offset = 4 * (768 + 6)
    colors = [tuple(v * 4 for v in raw[offset + i * 3:offset + i * 3 + 3])
              + (255 if i else 0,) for i in range(256)]
    if battlescape:
        gradient = [(140, 152, 148), (132, 136, 140), (116, 124, 132),
                    (108, 116, 124), (92, 104, 108), (84, 92, 100),
                    (76, 80, 92), (56, 68, 84), (48, 56, 68),
                    (40, 48, 56), (32, 36, 48), (24, 28, 32),
                    (16, 20, 24), (8, 12, 16), (3, 4, 8), (3, 3, 6)]
        colors[240:] = [(*c, 255) for c in gradient]
    return colors


def decode_pck(path: Path, colors: list[tuple[int, ...]], width: int = 32,
               height: int = 40) -> list[Image.Image]:
    data = path.read_bytes()
    tab = path.with_suffix(".TAB")
    if tab.exists():
        offsets = tab.read_bytes()
        offset_width = 4 if len(offsets) >= 4 and offsets[:4] == b"\0" * 4 else 2
        count = len(offsets) // offset_width
    else:
        count = 1
    frames = []
    indexed_offsets = struct.unpack("<"+("I" if offset_width == 4 else "H")*count, offsets) if tab.exists() else (0,)
    cursor = 0
    for index in range(count):
        if cursor != indexed_offsets[index]:
            raise ValueError(f"TAB/frame mismatch {path.name}:{index}: {indexed_offsets[index]} vs sequential {cursor}")
        if cursor >= len(data):
            raise ValueError(f"Truncated PCK {path.name}, frame {index}")
        pixels = [0] * (width * height)
        pixel = data[cursor] * width
        cursor += 1
        terminated = False
        while cursor < len(data):
            value = data[cursor]
            cursor += 1
            if value == 255:
                terminated = True
                break
            if value == 254:
                if cursor == len(data):
                    raise ValueError(f"Truncated transparent run in {path}")
                pixel += data[cursor]
                cursor += 1
            else:
                if pixel >= len(pixels):
                    raise ValueError(f"PCK pixel overflow {path.name}, frame {index}")
                pixels[pixel] = value
                pixel += 1
        if not terminated:
            raise ValueError(f"Unterminated PCK frame {path.name}:{index}")
        image = Image.new("RGBA", (width, height))
        image.putdata([colors[p] for p in pixels])
        frames.append(image)
    return frames


def sheet(images: list[Image.Image], labels: list[str], output: Path,
          title: str, columns: int = 8, scale: int = 3) -> None:
    cell_width = max(136, max(im.width for im in images) * scale + 16)
    cell_height = max(im.height for im in images) * scale + 38
    rows = (len(images) + columns - 1) // columns
    canvas = Image.new("RGB", (cell_width * columns, rows * cell_height + 36), "#17212b")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
    draw.text((12, 10), title, font=font, fill="#f2ddaa")
    for i, (image, label) in enumerate(zip(images, labels)):
        x, y = (i % columns) * cell_width, 36 + (i // columns) * cell_height
        draw.rectangle((x + 2, y + 2, x + cell_width - 3, y + cell_height - 3), fill="#24323d")
        enlarged = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
        canvas.paste(enlarged, (x + (cell_width - enlarged.width) // 2, y + 5), enlarged)
        draw.text((x + 7, y + cell_height - 27), label, fill="#d1e4e7", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    save_png(canvas, output)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def unit_views(frames: list[Image.Image], routine: int) -> list[Image.Image]:
    """Assemble standing bodies using UnitSprite.cpp, not isolated limb frames."""
    views = []
    for direction in range(8):
        if routine in (2, 3, 5):
            view = Image.new("RGBA", (64, 56))
            for part, pos in enumerate(((16, 0), (32, 8), (0, 8), (16, 16))):
                view.alpha_composite(frames[part*8+direction], pos)
            if routine == 2:
                view.alpha_composite(frames[64+direction], (16, 12))
        elif routine in (0, 10, 6, 7):
            view = Image.new("RGBA", (32, 40))
            torso = 24 if routine in (6, 7) else 32
            order = (0, 16, torso, 8) if direction < 3 else (16, torso, 0, 8) if direction == 3 else (16, 8, torso, 0)
            for base in order:
                view.alpha_composite(frames[base+direction])
        elif routine == 1:
            view = Image.new("RGBA", (32, 40))
            for base in (8, 16, 0):
                view.alpha_composite(frames[base+direction])
        else:
            view = frames[direction % len(frames)].copy()
        views.append(view)
    return views


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=ROOT / "reference")
    parser.add_argument("--output", type=Path, default=ROOT / "art/reference/verified-v2")
    args = parser.parse_args()
    reference = args.reference.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    catalog_path = pipeline_paths.path("catalog")
    old = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {}
    previous = {a["id"]: a for a in old.get("assets", [])}
    assets = []
    colors = palette(reference)
    inventory_colors = palette(reference, False)
    rules = ROOT / "bin/standard/xcom1"
    source_files = {}

    def record(asset: dict) -> None:
        prior = previous.get(asset["id"], {})
        for key in ("status", "recipe", "notes", "visual_review", "model", "blend", "metrics", "review_image",
                    "reference_review", "texture_trials", "quality_review", "rebuild_status", "legacy_review_image",
                    "review_views", "variants", "godot_reviews", "performance_review"):
            if key in prior:
                asset[key] = prior[key]
        asset.setdefault("status", "pending")
        assets.append(asset)

    for path in sorted((reference / "TERRAIN").glob("*.MCD")):
        raw = path.read_bytes()
        if len(raw) % 62:
            raise ValueError(f"Invalid 62-byte MCD record count in {path}")
        frames = decode_pck(path.with_suffix(".PCK"), colors)
        images, labels = [], []
        for index in range(len(raw) // 62):
            data = raw[index * 62:(index + 1) * 62]
            asset_id = f"terrain/{path.stem}/{index:03d}"
            part = PARTS[data[53]] if data[53] < len(PARTS) else f"unknown_raw_type_{data[53]}"
            image_path = output / f"{asset_id}.png"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            save_png(frames[data[0]], image_path)
            images.append(frames[data[0]])
            labels.append(f"M{index:03d}/P{data[0]:03d} {part[:1]}")
            animation_references = []
            for sprite in dict.fromkeys(data[:8]):
                frame_path = output / f"terrain/{path.stem}/frames/P{sprite:03d}.png"
                frame_path.parent.mkdir(parents=True, exist_ok=True)
                save_png(frames[sprite], frame_path)
                animation_references.append({"pck_frame": sprite, "kind": "animation_phase",
                    "phases": [i for i, value in enumerate(data[:8]) if value == sprite],
                    "path": relative(frame_path), "pixel_sha256": hashlib.sha256(frames[sprite].tobytes()).hexdigest()})
            record({"id": asset_id, "category": "terrain", "set": path.stem,
                    "record": index, "part": part, "raw_tile_type": data[53], "source": relative(path),
                    "reference_image": relative(image_path), "frames": list(data[:8]),
                    "reference_frames": animation_references, "frame_semantics": "animation phases; not facings",
                    "source_label": f"TERRAIN/{path.stem}.MCD record {index} -> {path.stem}.PCK frame {data[0]}",
                    "lofts": list(data[8:20]), "door": bool(data[35]),
                    "ufo_door": bool(data[30]), "gravlift": bool(data[34]),
                    "terrain_level": struct.unpack_from("b", data, 48)[0],
                    "sprite_y_offset": data[49], "destroyed_record": data[44],
                    "alternate_record": data[46], "armor": data[42],
                    "light_source": data[58], "big_wall": data[33]})
        sheet(images, labels, output / f"sheets/terrain_{path.stem}.png",
              f"{path.stem}: {len(images)} MCD objects / {len(frames)} sprite frames")

    item_rules = yaml.safe_load((rules / "items.rul").read_text(encoding="utf-8"))["items"]
    # InventoryState.cpp selects PAL_BATTLESCAPE, including its gray correction.
    big = decode_pck(reference / "UNITS/BIGOBS.PCK", colors, 32, 48)
    floor = decode_pck(reference / "UNITS/FLOOROB.PCK", colors)
    item_images, item_labels = [], []
    for item in item_rules:
        if "bigSprite" not in item or item.get("fixedWeapon"):
            continue
        asset_id = "items/" + item["type"]
        image_path = output / f"{asset_id}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image = big[item["bigSprite"]]
        save_png(image, image_path)
        item_images.append(image)
        item_labels.append(f"P{item['bigSprite']:03d} " + item["type"].removeprefix("STR_")[:14])
        item_references = [{"kind": "inventory", "file": "UNITS/BIGOBS.PCK", "pck_frame": item["bigSprite"],
                            "path": relative(image_path), "pixel_sha256": hashlib.sha256(image.tobytes()).hexdigest()}]
        if item.get("floorSprite", -1) >= 0:
            floor_path = image_path.with_name(image_path.stem+"_floor.png")
            save_png(floor[item["floorSprite"]], floor_path)
            item_references.append({"kind": "ground", "file": "UNITS/FLOOROB.PCK", "pck_frame": item["floorSprite"], "path": relative(floor_path)})
        record({"id": asset_id, "category": "item", "name": item["type"],
                "source": "bin/standard/xcom1/items.rul", "big_sprite": item["bigSprite"],
                "floor_sprite": item.get("floorSprite"), "hand_sprite": item.get("handSprite"),
                "reference_image": relative(image_path), "reference_frames": item_references,
                "battle_type": item.get("battleType", 0),
                "inventory_size": [item.get("invWidth", 1), item.get("invHeight", 1)]})
    sheet(item_images, item_labels, output / "sheets/items.png", "Tactical equipment and recoverable objects", columns=6)

    armors = yaml.safe_load((rules / "armors.rul").read_text(encoding="utf-8"))["armors"]
    sprite_sheets = sorted({a["spriteSheet"] for a in armors})
    for sprite_name in sprite_sheets:
        path = reference / "UNITS" / sprite_name
        frames = decode_pck(path, colors)
        routine = next(a.get("drawingRoutine", 0) for a in armors if a["spriteSheet"] == sprite_name)
        views = unit_references(frames, routine)
        sheet([image for image, _ in views], [recipe["label"] for _, recipe in views], output / f"sheets/assembled_{path.stem}.png",
              f"{path.stem}: verified standing assembly / routine {routine}", columns=8)
        view_references = []
        for view_index, (view, composition) in enumerate(views):
            view_path = output / f"units/{path.stem}/standing_{view_index:02d}.png"
            view_path.parent.mkdir(parents=True, exist_ok=True)
            save_png(view, view_path)
            view_references.append({"path": relative(view_path), "pixel_sha256": hashlib.sha256(view.tobytes()).hexdigest(), **composition})
        indices = list(range(min(8, len(frames))))
        indices.extend(i for i in (16, 24, 32, 40, 48, 56, 64, 72, 96, 104, 128, 192, 224, 256) if i < len(frames))
        sheet([frames[i] for i in indices], [str(i) for i in indices],
              output / f"sheets/unit_{path.stem}.png", f"{path.stem}: RAW frames (may be body parts, phases, or tile sections)")
        first_path = output / f"units/{path.stem}.png"
        first_path.parent.mkdir(parents=True, exist_ok=True)
        save_png(views[0][0], first_path)
        record({"id": f"units/{path.stem}", "category": "unit", "set": path.stem,
                "source": relative(path), "reference_image": relative(first_path),
                "frame_count": len(frames), "drawing_routine": routine, "reference_views": view_references,
                "direction_count": 1 if routine in (8, 9) else 8,
                "direction_note": "idle animation has no facing selection" if routine in (8, 9) else "0=N, clockwise through NW",
                "armors": [a["type"] for a in armors if a["spriteSheet"] == sprite_name],
                "footprint": max(a.get("size", 1) for a in armors if a["spriteSheet"] == sprite_name),
                "required_clips": ["Idle", "Walk", "Attack", "Hit", "Death"]})
    for name in ("HANDOB", "FLOOROB", "BIGOBS"):
        frames = decode_pck(reference / f"UNITS/{name}.PCK", colors,
                            32, 48 if name == "BIGOBS" else 40)
        sheet(frames, [str(i) for i in range(len(frames))], output / f"sheets/{name}.png", name)

    for name in ("SMOKE", "HIT", "X1"):
        path = reference / f"UFOGRAPH/{name}.PCK"
        frames = decode_pck(path, colors, 128 if name == "X1" else 32, 64 if name == "X1" else 40)
        sheet(frames, [str(i) for i in range(len(frames))], output / f"sheets/effects_{name}.png", name,
              columns=6 if name == "X1" else 8, scale=2 if name == "X1" else 3)

    for path in sorted(reference.rglob("*")):
        if path.is_file():
            source_files[path.relative_to(reference).as_posix()] = {
                "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    catalog = {"schema": 1, "scope": "UFO Defense tactical scene assets; animation frames are poses, not distinct models",
               "coordinates": {"tile_meters": 2.0, "level_meters": math.sqrt(6),
                               "source_logical_level_meters": 3.0, "source_vertical_voxels_per_level": 24,
                               "vertical_voxel_render_meters": math.sqrt(6)/24,
                               "source_logical_to_render_z": math.sqrt(2/3),
                               "blender": "Z up, +Y north; source map Y is reflected", "godot": "Y up, -Z north; +X east, +Z south"},
               "source_files": source_files, "assets": assets}
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    counts = Counter(a["category"] for a in assets)
    print(f"Cataloged {len(assets)} model identities: {dict(counts)}")
    print(f"Individual art and labeled contact sheets: {output}")


if __name__ == "__main__":
    main()
