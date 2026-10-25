# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/natural_details_opus55/tools/derive_maps.py (imported 2026-10-25)
# Changed: header only
"""Derive runtime albedo/normal/ORM PNGs from one generated albedo (utility maps only).

python derive_maps.py <src.png> <out_prefix> --size 1024 --rough 0.55 --strength 2.0 [--heal 48] [--alpha]
Writes <out_prefix>_albedo.png, _normal.png (+Y, OpenGL), _orm.png (R AO, G rough, B metal 0) and
<out_prefix>_maps.json (seam metrics, parameters). Never overwrites.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def seam_error(a):
    a = a.astype(np.float32)
    inner = np.abs(a[:, 1:] - a[:, :-1]).mean()
    lr = np.abs(a[:, 0] - a[:, -1]).mean()
    tb = np.abs(a[0] - a[-1]).mean()
    return float(lr / inner), float(tb / inner)


def heal(img, band):
    """Edge cross-fade: pixel i from an edge mixes with its mirror across the seam, weight 0.5 at the
    edge falling to 0 at `band`, so opposite edges meet with equal values (both axes)."""
    a = np.asarray(img).astype(np.float32)
    w = 0.5 * (1 - np.arange(band) / band)
    for axis in (1, 0):
        b = a.copy()
        n = a.shape[axis]
        for i in range(band):
            lo = np.take(a, i, axis=axis)
            hi = np.take(a, n - 1 - i, axis=axis)
            idx_lo = [slice(None)] * a.ndim
            idx_hi = [slice(None)] * a.ndim
            idx_lo[axis], idx_hi[axis] = i, n - 1 - i
            b[tuple(idx_lo)] = (1 - w[i]) * lo + w[i] * hi
            b[tuple(idx_hi)] = (1 - w[i]) * hi + w[i] * lo
        a = b
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("prefix")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--rough", type=float, default=0.8)
    ap.add_argument("--strength", type=float, default=2.0)
    ap.add_argument("--heal", type=int, default=0)
    ap.add_argument("--alpha", action="store_true")
    args = ap.parse_args()
    prefix = Path(args.prefix)
    outs = {k: Path(str(prefix) + f"_{k}.png") for k in ("albedo", "normal", "orm")}
    for p in outs.values():
        if p.exists():
            raise SystemExit("refusing to overwrite " + str(p))
    prefix.parent.mkdir(parents=True, exist_ok=True)
    src = Image.open(args.src).convert("RGBA" if args.alpha else "RGB")
    before = seam_error(np.asarray(src.convert("L")))
    if args.heal:
        rgb = heal(src.convert("RGB"), args.heal)
        src = rgb if not args.alpha else Image.merge("RGBA", (*rgb.split(), src.split()[3]))
    after = seam_error(np.asarray(src.convert("L")))
    w0, h0 = src.size
    k = args.size / max(w0, h0)
    dims = (args.size, args.size) if not args.alpha else (round(w0 * k), round(h0 * k))
    alb = src.resize(dims, Image.Resampling.LANCZOS)
    if args.alpha:  # dilate colour under transparent texels so mipmaps do not fringe
        a = np.asarray(alb).astype(np.float32)
        rgb, al = a[..., :3], a[..., 3] > 8
        filled = rgb * al[..., None]
        mask = al.astype(np.float32)
        for _ in range(64):
            if mask.min() > 0:
                break
            s = sum(np.roll(np.roll(filled, dy, 0), dx, 1) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            m = sum(np.roll(np.roll(mask, dy, 0), dx, 1) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            grow = (mask == 0) & (m > 0)
            filled[grow] = s[grow] / m[grow][:, None]
            mask[grow] = 1
        a[..., :3] = filled
        alb = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    alb.save(outs["albedo"])
    lum = np.asarray(alb.convert("L").filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    low = np.asarray(alb.convert("L").filter(ImageFilter.GaussianBlur(args.size / 64))).astype(np.float32) / 255
    height = lum - low * 0.6
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * args.strength * args.size / 256
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * args.strength * args.size / 256
    n = np.stack([-gx, gy, np.ones_like(gx)], -1)  # +Y up (OpenGL): image rows go down
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255).round().astype(np.uint8)).save(outs["normal"])
    ao = np.clip(0.75 + (height - height.mean()) * 1.2, 0.45, 1.0)
    orm = np.stack([ao, np.full_like(ao, args.rough), np.zeros_like(ao)], -1)
    Image.fromarray((orm * 255).round().astype(np.uint8)).save(outs["orm"])
    meta = {"source": str(args.src), "size": args.size, "roughness": args.rough, "normal_strength": args.strength,
            "heal_band_px": args.heal, "seam_ratio_before_lr_tb": before, "seam_ratio_after_lr_tb": after,
            "normal_convention": "+Y (OpenGL), derived from albedo luminance (utility map)",
            "orm": "R AO (derived), G roughness constant, B metallic 0"}
    Path(str(prefix) + "_maps.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
