"""Origin: S:/Repos/trick-or-treat/art/tools/make_materials.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. toon.tres res:// paths, header namespace and output locations are settings/paths; null skips an output.

Builds the material texture arrays from the game's materials spec (default art/materials/materials.json).

For each layer it takes art/materials/source/<name>.png (a painted source; a tileable noise
placeholder is used until one exists), then:
  * resizes to 512 px and makes it seamless if its edges don't already wrap,
  * neutralises it: each channel is normalised to a 0.5 mean and the contrast is levelled, so the
    painted detail modulates the palette tint instead of fighting it,
  * derives a tangent-space normal map (OpenGL / Y+) from its luminance.

Outputs:
  game/assets/materials/albedo_array.png   512 x 512*N vertical strip (Texture2DArray)
  game/assets/materials/normal_array.png   same layout
  game/assets/materials/materials.json     names, scales, strengths (for tools)
  game/materials/toon.tres                 shared material with per-layer scale/strength/normal
  native/src/mesh/materials.gen.h          tot::mat constants for the C++ mesh builder
  art/materials/preview.png                contact sheet of every layer, tinted
Run: python <pipeline>/tools/make_materials.py   (from the game root, or set ART_GAME_ROOT)
Paths above are the defaults; see tools/pipeline_paths.py.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_paths as P  # noqa: E402
ROOT = P.GAME_ROOT
SPEC = json.loads(P.path("materials_spec").read_text())
SOURCE = P.path("materials_source")
OUT = P.path("materials_out")
NS = P.setting("cpp_namespace")
SIZE = 512
TARGET_STD = 0.13


def tileable_noise(size, seed, octaves=5):
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = 4 * 2 ** o
        grid = rng.random((cells, cells)).astype(np.float32)
        coords = np.arange(size) * cells / size
        i0 = np.floor(coords).astype(int) % cells
        i1 = (i0 + 1) % cells
        f = coords - np.floor(coords)
        f = f * f * (3 - 2 * f)
        rows = grid[i0][:, i0] * (1 - f)[None, :] + grid[i0][:, i1] * f[None, :]
        rows2 = grid[i1][:, i0] * (1 - f)[None, :] + grid[i1][:, i1] * f[None, :]
        layer = rows * (1 - f)[:, None] + rows2 * f[:, None]
        out += layer * amp
        total += amp
        amp *= 0.5
    return out / total


def seam_ratio(img):
    lum = img.mean(axis=2)
    edge = (np.abs(lum[0] - lum[-1]).mean() + np.abs(lum[:, 0] - lum[:, -1]).mean()) * 0.5
    inner = (np.abs(np.diff(lum, axis=0)).mean() + np.abs(np.diff(lum, axis=1)).mean()) * 0.5
    return edge / max(inner, 1e-6)


def make_seamless(img, band=0.12):
    """Crossfade only a narrow border band with a half-offset copy, whose edges are continuous
    interior pixels. Keeps the painting intact everywhere else (no ghosted doubles)."""
    h, w, _ = img.shape
    rolled = np.roll(np.roll(img, h // 2, axis=0), w // 2, axis=1)
    dy = np.minimum(np.arange(h), np.arange(h)[::-1]) / (h * band)
    dx = np.minimum(np.arange(w), np.arange(w)[::-1]) / (w * band)
    my = np.clip(dy, 0, 1)[:, None]
    mx = np.clip(dx, 0, 1)[None, :]
    mask = (my * mx)
    mask = mask * mask * (3 - 2 * mask)
    return img * mask[..., None] + rolled * (1 - mask[..., None])


def box_blur_wrap(a, r=1):
    out = a.copy()
    for axis in (0, 1):
        acc = np.zeros_like(out)
        for d in range(-r, r + 1):
            acc += np.roll(out, d, axis=axis)
        out = acc / (2 * r + 1)
    return out


def process(layer, index):
    name = layer["name"]
    if name == "flat":
        albedo = np.full((SIZE, SIZE, 3), 0.5, np.float32)
        normal = np.zeros((SIZE, SIZE, 3), np.float32)
        normal[..., 2] = 1.0
        return albedo, normal, "flat"
    src = SOURCE / f"{name}.png"
    if src.exists():
        img = np.asarray(Image.open(src).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS), np.float32) / 255.0
        origin = "painted"
    else:
        n = tileable_noise(SIZE, 1000 + index)
        img = np.repeat(n[..., None], 3, axis=2) * 0.5 + 0.35
        origin = "placeholder"
    if seam_ratio(img) > 2.2:
        img = make_seamless(img)
    # Neutralise: per-channel mean 0.5, level the luminance contrast.
    img = img / np.maximum(img.reshape(-1, 3).mean(axis=0), 1e-4) * 0.5
    lum = img.mean(axis=2)
    std = float(lum.std())
    k = min(TARGET_STD / max(std, 1e-4), 2.5)  # don't blow faint paintings up into streaks
    albedo = np.clip(0.5 + (img - 0.5) * k, 0.0, 1.0)
    # Normal map from luminance.
    hgt = box_blur_wrap(albedo.mean(axis=2), 1)
    strength = 7.0 * layer["normal"]
    dx = (np.roll(hgt, -1, axis=1) - np.roll(hgt, 1, axis=1)) * strength
    dy = (np.roll(hgt, -1, axis=0) - np.roll(hgt, 1, axis=0)) * strength
    nrm = np.stack([-dx, dy, np.ones_like(dx)], axis=2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return albedo, nrm, origin


def to_u8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def write_import(path, normal):
    path.with_suffix(path.suffix + ".import").write_text(
        "[remap]\n\nimporter=\"2d_array_texture\"\ntype=\"CompressedTexture2DArray\"\n\n[params]\n\n"
        f"compress/mode={0 if normal else 2}\ncompress/channel_pack=0\nmipmaps/generate=true\nmipmaps/limit=-1\n"
        f"slices/horizontal=1\nslices/vertical={len(SPEC['layers'])}\n")


def main():
    layers = SPEC["layers"]
    OUT.mkdir(parents=True, exist_ok=True)
    albedos, normals, origins = [], [], []
    for i, layer in enumerate(layers):
        a, n, origin = process(layer, i)
        albedos.append(to_u8(a))
        normals.append(to_u8(n * 0.5 + 0.5))
        origins.append(origin)
    Image.fromarray(np.concatenate(albedos, axis=0)).save(OUT / "albedo_array.png")
    Image.fromarray(np.concatenate(normals, axis=0)).save(OUT / "normal_array.png")
    write_import(OUT / "albedo_array.png", False)
    write_import(OUT / "normal_array.png", True)
    (OUT / "materials.json").write_text(json.dumps(
        [{"index": i, "name": l["name"], "scale": l["scale"], "strength": l["strength"], "normal": l["normal"], "origin": origins[i]}
         for i, l in enumerate(layers)], indent=1))

    def arr(key):
        # The shader declares 32-entry arrays; pad so the uniform always matches.
        vals = [f"{l[key]:g}" for l in layers] + ["1" if key == "scale" else "0"] * (32 - len(layers))
        return ", ".join(vals)

    toon = P.path("toon_material")
    if toon is not None:
        toon.parent.mkdir(parents=True, exist_ok=True)
    (toon if toon is not None else OUT / "toon.tres").write_text(
        '[gd_resource type="ShaderMaterial" load_steps=6 format=3]\n\n'
        f'[ext_resource type="Shader" path="{P.setting("toon_shader_res")}" id="1_shader"]\n'
        f'[ext_resource type="Texture2D" path="{P.setting("palette_res")}" id="2_pal"]\n'
        f'[ext_resource type="Texture2D" path="{P.setting("palette_emit_res")}" id="3_emit"]\n'
        f'[ext_resource type="Texture2DArray" path="{P.setting("albedo_array_res")}" id="4_alb"]\n'
        f'[ext_resource type="Texture2DArray" path="{P.setting("normal_array_res")}" id="5_nrm"]\n\n'
        '[resource]\nrender_priority = 0\nshader = ExtResource("1_shader")\n'
        'shader_parameter/palette = ExtResource("2_pal")\nshader_parameter/palette_emit = ExtResource("3_emit")\n'
        'shader_parameter/albedo_array = ExtResource("4_alb")\nshader_parameter/normal_array = ExtResource("5_nrm")\n'
        f'shader_parameter/layer_scale = PackedFloat32Array({arr("scale")})\n'
        f'shader_parameter/layer_strength = PackedFloat32Array({arr("strength")})\n'
        f'shader_parameter/layer_normal = PackedFloat32Array({arr("normal")})\n')

    lines = ["// Generated by art/tools/make_materials.py. Do not edit.", "#pragma once", "", f"namespace {NS}::mat {{",
             f"constexpr int COUNT = {len(layers)};"]
    for i, l in enumerate(layers):
        lines.append(f"constexpr int {l['name'].upper()} = {i};")
    lines.append(f"constexpr float SCALE[COUNT] = {{ {', '.join(f'{float(l['scale']):.3f}f' for l in layers)} }};")
    lines += ["", f"}} // namespace {NS}::mat", ""]
    hdr = P.path("native_header_dir")
    if hdr is not None:
        hdr.mkdir(parents=True, exist_ok=True)
        (hdr / "materials.gen.h").write_text("\n".join(lines))

    # Contact sheet: each layer tinted with a sample colour, 7 columns.
    tints = [(0.95, 0.85, 0.7), (0.55, 0.75, 0.7), (0.75, 0.45, 0.4), (0.65, 0.55, 0.85)]
    cols = 7
    rows = (len(layers) + cols - 1) // cols
    tile = 160
    sheet = Image.new("RGB", (cols * tile, rows * tile), (20, 22, 40))
    for i, a in enumerate(albedos):
        t = np.array(tints[i % 4])
        img = np.clip(a.astype(np.float32) / 255.0 * 2.0 * t, 0, 1)
        im = Image.fromarray(to_u8(img)).resize((tile - 8, tile - 8))
        sheet.paste(im, ((i % cols) * tile + 4, (i // cols) * tile + 4))
    prev = P.path("materials_preview")
    if prev is not None:
        prev.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(prev)
    painted = sum(1 for o in origins if o == "painted")
    print(f"{len(layers)} layers ({painted} painted, {origins.count('placeholder')} placeholder) -> {OUT}")


if __name__ == "__main__":
    main()
