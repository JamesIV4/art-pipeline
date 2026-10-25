# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/textures.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""AVENGER v2 texture processing (host Python: Pillow + numpy).

Turns image_gen outputs (textures/gen_*.png, provenance beside them) into tiling PBR sets:
seam heal (offset + narrow seam blend), resample, regrade toward the sprite colour, and derived
utility maps (normal GL from a luminance height, ORM = AO / roughness / metal).
Writes to textures/out/<name>_{albedo,normal,orm}.png (never overwrites; bump the name to revise).
Usage: python textures.py <name> [<name> ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import WORK  # noqa: E402
GEN = WORK / "textures"
OUT = WORK / "textures/out"
OUT.mkdir(parents=True, exist_ok=True)

# name: source image, output size, target sRGB mean (None = keep), roughness base, height sigma, normal strength, metal
SETS = {
    "avg2_xpanel": dict(src="gen_roof_plate_a.png", size=1024, target=(116, 124, 126), rough=0.62, sigma=24, strength=5.0, metal=0.0, contrast=1.45),
    "avg2_hull": dict(src="gen_hull_plate_a.png", size=1024, target=(140, 148, 146), rough=0.60, sigma=24, strength=5.0, metal=0.0),
    "avg2_hull_b": dict(src="gen_hull_plate_a.png", size=1024, target=(116, 121, 128), rough=0.60, sigma=24, strength=9.0, metal=0.0, contrast=1.35),
    "avg2_xpanel_b": dict(src="gen_roof_plate_a.png", size=1024, target=(96, 101, 110), rough=0.62, sigma=24, strength=10.0, metal=0.0, contrast=1.9),
    "avg2_greeble_b": dict(src="gen_hull_greeble_a.png", size=1024, target=(108, 113, 122), rough=0.62, sigma=18, strength=10.0, metal=0.0, contrast=1.4),
    "avg2_nacelle": dict(src="gen_nacelle_a.png", size=1024, target=(116, 120, 126), rough=0.58, sigma=16, strength=9.0, metal=0.0, contrast=1.2),
    "avg2_greeble_c": dict(src="gen_hull_greeble_c.png", size=1024, target=(120, 126, 130), rough=0.60, sigma=20, strength=7.0, metal=0.0, contrast=1.1),
    "avg2_greeble": dict(src="gen_hull_greeble_a.png", size=1024, target=(118, 126, 128), rough=0.62, sigma=18, strength=6.0, metal=0.0),
    "avg2_interior": dict(src="gen_interior_a.png", size=1024, target=(196, 180, 176), rough=0.66, sigma=18, strength=4.0, metal=0.0),
    "avg2_deck": dict(src="gen_deck_a.png", size=1024, target=(196, 178, 172), rough=0.58, sigma=16, strength=4.0, metal=0.0),
}


def srgb_to_lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * l ** (1 / 2.4) - 0.055) * 255.0


def heal(img, band=6):
    """Roll by half, blend a narrow band across the centre seams, roll back."""
    a = np.asarray(img, dtype=np.float32)
    h, w = a.shape[:2]
    r = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    blur = np.asarray(Image.fromarray(r.astype(np.uint8)).filter(ImageFilter.GaussianBlur(band * 0.6)), dtype=np.float32)
    m = np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    m = np.maximum(np.clip(1 - np.abs(yy - h / 2) / band, 0, 1), np.clip(1 - np.abs(xx - w / 2) / band, 0, 1))[..., None]
    r = r * (1 - m) + blur * m
    r = np.roll(np.roll(r, -(h // 2), 0), -(w // 2), 1)
    return Image.fromarray(np.clip(r, 0, 255).astype(np.uint8))


def seam_error(a):
    a = np.asarray(a, dtype=np.float32)
    return float(np.abs(a[0] - a[-1]).mean()), float(np.abs(a[:, 0] - a[:, -1]).mean())


def gaussian(a, sigma):
    # wrap-aware (tileable) gaussian blur via FFT
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi ** 2) * (sigma ** 2) * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g)).astype(np.float32)


def derive(name, cfg):
    src = GEN / cfg["src"]
    img = Image.open(src).convert("RGB")
    before = seam_error(img)
    s = min(img.size)
    img = img.crop(((img.width - s) // 2, (img.height - s) // 2, (img.width - s) // 2 + s, (img.height - s) // 2 + s))
    img = heal(img)
    img = img.resize((cfg["size"], cfg["size"]), Image.Resampling.LANCZOS)
    a = np.asarray(img, dtype=np.float32)
    if cfg["target"]:
        lin = srgb_to_lin(a)
        tgt = srgb_to_lin(np.array(cfg["target"], dtype=np.float32))
        med = np.median(lin.reshape(-1, 3), axis=0)
        lin = lin * (tgt / np.maximum(med, 1e-4))
        a = lin_to_srgb(lin)
    if cfg.get("contrast"):
        m = np.median(a.reshape(-1, 3), axis=0)
        a = m + (a - m) * cfg["contrast"]
    alb = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    lum = (a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11) / 255.0
    hp = lum - gaussian(lum, cfg["sigma"])
    hp = gaussian(hp, 0.8)
    k = cfg["strength"]
    dx = (np.roll(hp, -1, 1) - np.roll(hp, 1, 1)) * 0.5 * k * cfg["size"] / 64.0
    dy = (np.roll(hp, -1, 0) - np.roll(hp, 1, 0)) * 0.5 * k * cfg["size"] / 64.0
    # GL convention: +Y = image up; rows grow downward -> dh/dup = -dy
    nx, ny, nz = -dx, dy, np.ones_like(dx)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / L, ny / L, nz / L], -1)
    nimg = Image.fromarray(np.clip((nrm * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8))
    cav = gaussian(lum, 6) - lum
    ao = np.clip(1.0 - np.maximum(cav, 0) * 3.0, 0.55, 1.0)
    rough = np.clip(cfg["rough"] - (lum - np.median(lum)) * 0.35 + np.maximum(cav, 0) * 0.5, 0.25, 0.95)
    metal = np.full_like(lum, cfg["metal"])
    orm = Image.fromarray(np.clip(np.stack([ao, rough, metal], -1) * 255 + 0.5, 0, 255).astype(np.uint8))
    paths = {}
    for kind, im in (("albedo", alb), ("normal", nimg), ("orm", orm)):
        p = OUT / f"{name}_{kind}.png"
        if p.exists() and "--force" not in sys.argv:   # out/ holds only this task's unpublished working maps
            print("exists, kept:", p.name)
        else:
            im.save(p)
        paths[kind] = p.name
    # 2x2 tiling check image
    t = Image.new("RGB", (cfg["size"] * 2, cfg["size"] * 2))
    for i in range(2):
        for j in range(2):
            t.paste(alb, (i * cfg["size"], j * cfg["size"]))
    t.resize((1024, 1024)).save(OUT / f"{name}_tile2x2_check.png")
    info = {"source": cfg["src"], "seam_error_before_heal_rows_cols": before, "after": seam_error(alb), **{k: v for k, v in cfg.items()}, "maps": paths}
    (OUT / f"{name}.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(name, info["seam_error_before_heal_rows_cols"], "->", info["after"])


if __name__ == "__main__":
    for n in [a for a in sys.argv[1:] if not a.startswith("--")]:
        derive(n, SETS[n])
