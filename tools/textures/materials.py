# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/materials.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT; TEXTURES = <godot_project>/assets/textures
"""Original, seamless PBR texture library, generated inside Blender with NumPy.

Files are shared by all exported glTF models. Surface relief is tangent-space
normal mapping; no microgeometry or stacked coplanar overlays are necessary.
"""
from pathlib import Path
import hashlib
import math
import struct
import zlib

import bpy
import numpy as np

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
TEXTURES = pipeline_paths.path("godot_project") / "assets/textures"
PRESETS = {
    "grass": ("ground", "456f26", .94, 0), "soil": ("ground", "684432", .96, 0),
    "sand": ("ground", "b99664", .92, 0), "snow": ("ground", "dce5e9", .78, 0),
    "mars": ("rock", "bf884e", .9, 0), "rock": ("rock", "767673", .9, 0),
    "charcoal": ("rock", "2c292b", .87, 0), "asphalt": ("ground", "40444b", .91, 0),
    "concrete": ("stone", "adb1b1", .86, 0), "stone": ("brick", "8c817c", .9, 0),
    "brick": ("brick", "a28b55", .9, 0), "plaster": ("stone", "c4b9aa", .88, 0),
    "cream": ("stone", "c9bca7", .85, 0), "wood": ("wood", "987047", .74, 0),
    "wood_dark": ("wood", "64412e", .79, 0), "wood_white": ("wood", "d6cdc5", .71, 0),
    "bark": ("bark", "705641", .93, 0), "hay": ("fiber", "c49f4d", .96, 0),
    "leaf": ("leaf", "356b2b", .88, 0), "leaf_light": ("leaf", "739637", .89, 0),
    "palm": ("leaf", "317c48", .76, 0), "wheat": ("blade", "bea457", .93, 0),
    "blade": ("blade", "497832", .93, 0), "metal": ("metal", "858995", .38, .82),
    "metal_dark": ("metal", "38424c", .46, .78), "metal_white": ("metal", "cad0d4", .38, .7),
    "blue": ("paint", "658aa7", .51, .25), "purple": ("paint", "89809f", .42, .35),
    "alien": ("metal", "a593ba", .39, .7), "gold": ("metal", "b38b41", .39, .68),
    "orange": ("paint", "bf782d", .53, .18), "red": ("paint", "c04c4e", .55, .1),
    "green": ("paint", "3b795b", .56, .18), "white": ("paint", "e5e1d8", .5, .1),
    "black": ("rubber", "182029", .71, 0), "rubber": ("rubber", "272b30", .83, 0),
    "fabric": ("fabric", "7d8296", .92, 0), "fabric_blue": ("fabric", "556f97", .89, 0),
    "fabric_red": ("fabric", "88556a", .93, 0), "fabric_gold": ("fabric", "c28c36", .9, 0),
    "skin": ("skin", "cfa17d", .71, 0), "sectoid": ("skin", "a1aaa6", .7, 0),
    "snake": ("scales", "b07a38", .71, 0), "muton": ("scales", "4b9c46", .65, 0),
    "pink": ("skin", "b77f9f", .58, 0), "chitin": ("scales", "435a68", .37, .15),
    "fur": ("fiber", "a9907d", .95, 0), "obsidian": ("lava", "46424c", .3, .25),
    "glass": ("glass", "455367", .18, .18), "eye": ("glass", "09161c", .11, .1),
    "water": ("glass", "19495f", .16, .12), "ice": ("rock", "b4d4e2", .32, .05),
    "glass_clear": ("glass", "b4d4dd", .10, 0),
    "circuit": ("tech", "b0a499", .58, .42), "alien_panel": ("tech", "9392af", .43, .64),
    "glow_blue": ("emission", "54b8ec", .35, .15), "glow_green": ("emission", "70c96b", .44, .1),
    "glow_amber": ("emission", "efad51", .45, .1), "glow_pink": ("emission", "c77ce5", .4, .1),
}
MATERIALS = {}


def png(path, rgba):
    """Write exact sRGB/non-color bytes without an image-library dependency."""
    pixels = np.clip(rgba * 255, 0, 255).astype(np.uint8)
    h, w, _ = pixels.shape
    def chunk(kind, content):
        return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content))
    raw = b"".join(b"\0" + row.tobytes() for row in pixels)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def texture_set(key, size=512):
    TEXTURES.mkdir(parents=True, exist_ok=True)
    paths = {name: TEXTURES / f"{key}_{name}.png" for name in ("albedo", "normal", "orm")}
    for name, path in paths.items():
        if path.with_suffix(".webp").exists():
            paths[name] = path.with_suffix(".webp")
    if all(p.exists() for p in paths.values()):
        return paths
    kind, hex_color, roughness, metallic = PRESETS[key]
    seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size] / size
    noise = np.zeros((size, size))
    for frequency, amplitude in ((2, .3), (5, .22), (13, .15), (29, .08), (67, .04)):
        for _ in range(3):
            a, b = rng.integers(1, frequency + 1, 2)
            noise += amplitude * np.sin(math.tau * (x*a+y*b) + rng.random()*math.tau) / 3
    grain = rng.normal(0, .04, (size, size))
    height = noise * .22 + grain * .13
    modulation = 1 + noise * .18 + grain
    alpha = np.ones_like(x)
    if kind in ("wood", "bark", "fiber"):
        waves = np.sin(math.tau * (x * 19 + .45*np.sin(y*math.tau*3)))
        height += waves * (.10 if kind != "fiber" else .025)
        modulation += waves * .13
        if kind == "wood":
            seam = np.minimum((x*5) % 1, 1-(x*5) % 1)
            height -= np.clip(1-seam*75, 0, 1)*.2
            modulation *= 1 - np.clip(1-seam*75, 0, 1)*.25
    if kind == "brick":
        row = np.floor(y*7)
        xx = (x*4 + (row % 2)*.5) % 1
        yy = (y*7) % 1
        mortar = np.minimum(np.minimum(xx, 1-xx), np.minimum(yy, 1-yy)) < .055
        height = np.where(mortar, -.26, height)
        modulation = np.where(mortar, .63, modulation)
    if kind == "fabric":
        weave = np.sin(x*math.tau*128)*np.sin(y*math.tau*128)
        height += weave*.018
        modulation += weave*.025
    if kind == "scales":
        xx = (x*18 + (np.floor(y*24) % 2)*.5) % 1 - .5
        yy = (y*24) % 1 - .5
        scale = np.maximum(0, 1-(xx/.5)**2-(yy/.6)**2)
        height += scale*.11
        modulation += (scale-.4)*.12
    if kind in ("leaf", "blade"):
        if kind == "leaf":
            distance = ((x-.5)/.43)**2 + ((y-.5)/.48)**2
            alpha = (distance < 1).astype(float)
            vein = np.exp(-np.abs(x-.5)*80)
            side_veins = np.maximum(0, np.sin((y+np.abs(x-.5)*.8)*math.tau*9))**12
            height += vein*.1 + side_veins*.026
            modulation += (1-distance)*.23 + vein*.12
        else:
            width = .25*(1-y)**.6 + .015
            center = .5+.13*np.sin(y*2.3)
            alpha = ((np.abs(x-center) < width) & (y < .99)).astype(float)
            height += np.exp(-np.abs(x-center)*25)*.07
            modulation += .15*y
    if kind in ("metal", "paint", "glass", "emission", "rubber"):
        height *= .07
        modulation = 1+noise*.04+grain*.16
    if kind == "lava":
        fissure = np.exp(-np.abs(noise)*90)
        height -= fissure*.18
        modulation += fissure*.3
    if kind == "tech":
        xx, yy = (x*4) % 1, (y*4) % 1
        perimeter = np.minimum(np.minimum(xx, 1-xx), np.minimum(yy, 1-yy)) < .025
        traces = ((np.abs(xx-.22) < .01) & (yy > .18) & (yy < .78)) | ((np.abs(yy-.78) < .01) & (xx > .22) & (xx < .65))
        height = np.where(perimeter, -.12, np.where(traces, -.04, height*.2))
        modulation = np.where(perimeter, .58, np.where(traces, .7, modulation))
    rgb = np.array([int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)])
    albedo = np.dstack([np.clip(rgb[c]*modulation, 0, 1) for c in range(3)] + [alpha])
    dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))*3.5
    dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))*3.5
    norm = np.sqrt(dx*dx+dy*dy+1)
    normal = np.dstack(((-dx/norm+1)*.5, (-dy/norm+1)*.5, (1/norm+1)*.5, np.ones_like(x)))
    ao = np.clip(1+height*.12, .75, 1)
    orm = np.dstack((ao, np.clip(roughness+noise*.055, 0, 1), np.full_like(x, metallic), np.ones_like(x)))
    for name, pixels in (("albedo", albedo), ("normal", normal), ("orm", orm)):
        if not paths[name].exists():
            png(paths[name], pixels)
    return paths


def material(key):
    if key in MATERIALS and MATERIALS[key].name in bpy.data.materials:
        return MATERIALS[key]
    kind, color, roughness, metallic = PRESETS[key]
    paths = texture_set(key)
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = (*[int(color[i:i+2], 16)/255 for i in (0, 2, 4)], 1)
    maps = {}
    for index, name in enumerate(("albedo", "normal", "orm")):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(paths[name]), check_existing=True)
        tex.image.colorspace_settings.name = "sRGB" if name == "albedo" else "Non-Color"
        tex.location = (-600, 300-index*260)
        maps[name] = tex
    links.new(maps["albedo"].outputs["Color"], bsdf.inputs["Base Color"])
    normal = nodes.new("ShaderNodeNormalMap")
    links.new(maps["normal"].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(maps["orm"].outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    group = bpy.data.node_groups.get("glTF Material Output")
    if not group:
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    occlusion = nodes.new("ShaderNodeGroup")
    occlusion.node_tree = group
    links.new(split.outputs["Red"], occlusion.inputs["Occlusion"])
    if kind in ("leaf", "blade"):
        round_alpha = nodes.new("ShaderNodeMath")
        round_alpha.operation = "ROUND"
        links.new(maps["albedo"].outputs["Alpha"], round_alpha.inputs[0])
        links.new(round_alpha.outputs[0], bsdf.inputs["Alpha"])
        mat.use_backface_culling = False
    else:
        mat.use_backface_culling = True
    if kind == "emission":
        links.new(maps["albedo"].outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.8
    if key == "glass_clear":
        bsdf.inputs["Alpha"].default_value = .22
        mat.use_backface_culling = False
    MATERIALS[key] = mat
    return mat
