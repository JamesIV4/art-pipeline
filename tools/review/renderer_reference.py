# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/renderer_reference.py (imported 2026-10-25)
# Changed: header only (dependency of catalog_reference/audit_reference)
"""Standing reference assembly transcribed from the root OXCE renderer.

UnitSprite.cpp routines 0-10; Pathfinding.h defines facings 0=N clockwise.
Terrain MCD Frame[8] entries are animation phases, never camera directions.
"""
from PIL import Image

FACINGS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
NORMAL_ORDER = (
    ("left_arm", "legs", "torso", "right_arm"),
    ("left_arm", "legs", "torso", "right_arm"),
    ("left_arm", "legs", "torso", "right_arm"),
    ("legs", "torso", "left_arm", "right_arm"),
    ("legs", "right_arm", "torso", "left_arm"),
    ("right_arm", "legs", "torso", "left_arm"),
    ("right_arm", "legs", "torso", "left_arm"),
    ("left_arm", "right_arm", "legs", "torso"),
)
FLOATER_ORDER = (
    ("left_arm", "torso", "right_arm"), ("left_arm", "torso", "right_arm"),
    ("left_arm", "torso", "right_arm"), ("torso", "left_arm", "right_arm"),
    ("torso", "left_arm", "right_arm"), ("right_arm", "torso", "left_arm"),
    ("right_arm", "torso", "left_arm"), ("right_arm", "left_arm", "torso"),
)


def standing_recipe(routine, direction=0, torso_variant="male", hover=False, turret=0):
    if routine in (8, 9):
        return {"label": "idle animation phase 0 (no directional sprite selection)",
                "kind": "animation", "direction": None, "canvas": [32, 40],
                "layers": [{"part": "body", "frame": 0, "offset": [0, 0]}]}
    result = {"label": f"facing {direction} {FACINGS[direction]}", "kind": "direction",
              "direction": direction, "canvas": [32, 40], "layers": []}
    if routine in (0, 10, 6, 7):
        base = {"left_arm": 0, "right_arm": 8, "legs": 16,
                "torso": 24 if routine in (6, 7) else 267 if torso_variant == "female" else 32}
        order = ("right_arm", "legs", "torso", "left_arm") if routine in (6, 7) and direction == 4 else NORMAL_ORDER[direction]
        result["layers"] = [{"part": name, "frame": base[name]+direction, "offset": [0, 0]}
                            for name in order]
    elif routine == 1:
        base = {"left_arm": 8, "right_arm": 0, "torso": 16}
        result["layers"] = [{"part": name, "frame": base[name]+direction, "offset": [0, 0]}
                            for name in FLOATER_ORDER[direction]]
    elif routine in (2, 3, 5):
        result["canvas"] = [64, 56]
        offsets = ((16, 0), (32, 8), (0, 8), (16, 16))
        for part, offset in enumerate(offsets):
            if hover and routine == 2 and part:
                result["layers"].append({"part": f"propulsion_{part}", "frame": 104+(part-1)*8, "offset": list(offset)})
            elif routine == 3 and part:
                result["layers"].append({"part": f"propulsion_{part}", "frame": 32+(part-1)*8, "offset": list(offset)})
            result["layers"].append({"part": f"body_tile_{part}",
                "frame": (32 if hover and routine == 2 else 0)+part*8+direction, "offset": list(offset)})
        if routine == 2 and turret >= 0:
            ox = (-2, -7, -5, 0, 5, 7, 2, 0)[direction] if hover else 0
            oy = (-1, -3, -4, -5, -4, -3, -1, -1)[direction] if hover else 0
            result["layers"].append({"part": "turret", "frame": 64+turret*8+direction, "offset": [16+ox, 12+oy]})
    elif routine == 4:
        result["layers"] = [{"part": "body", "frame": direction, "offset": [0, 0]}]
    else:
        raise ValueError(f"Standing reference for drawing routine {routine} has not been verified")
    return result


def assemble(frames, recipe):
    canvas = Image.new("RGBA", tuple(recipe["canvas"]))
    for layer in recipe["layers"]:
        if not 0 <= layer["frame"] < len(frames):
            raise ValueError(f"Assembly frame out of bounds: {layer}")
        canvas.alpha_composite(frames[layer["frame"]], tuple(layer["offset"]))
    return canvas


def unit_references(frames, routine, **kwargs):
    count = 1 if routine in (8, 9) else 8
    recipes = [standing_recipe(routine, i, **kwargs) for i in range(count)]
    return [(assemble(frames, recipe), recipe) for recipe in recipes]
