# Origin: S:/Repos/OpenXcom-Extended-3D/art/source/vfx/pack_atlases.py (imported 2026-10-25)
# Changed: header only (paths are CLI arguments)
# Packs the Blender renders (16-bit straight-alpha PNG, sRGB) into the 8x8 flipbook atlases the effects use,
# as 8-bit lossless WebP (2048x2048, 256 px frames) plus the scorch decal maps (512x512).
#   emission atlases: rgb = sqrt(linear fire light over black / scale), a = opacity
#   light-map atlases: r, g, b = sqrt(smoke lit from the sprite's right / top / left, normalised), a = opacity
# Usage: python pack_atlases.py <renders root> <textures out dir> [fireball_dir smoke_dir fire_dir scorch_dir]
#        (a "jet" folder under the renders root packs the fire-jet loop, fx_fire_jet_8x8.webp, 2026-10-13)
import sys, json, hashlib
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
DIRS = dict(zip(("fireball", "smoke", "fire", "scorch"), sys.argv[3:7])) if len(sys.argv) > 6 else {
    "fireball": "fireball", "smoke": "smoke", "fire": "fire", "scorch": "scorch"}
DIRS.setdefault("jet", "jet")
CELL = 256
DERIVED = True   # light maps from the opacity (see derived_light), not from the EEVEE lit passes
OUT.mkdir(parents=True, exist_ok=True)
report = {}


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def load(path):
    a = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if a is None:
        raise FileNotFoundError(path)
    a = a.astype(np.float32) / (65535.0 if a.dtype == np.uint16 else 255.0)
    a = a[..., [2, 1, 0, 3]]
    rgb = srgb_to_linear(a[..., :3])
    al = a[..., 3]
    return np.dstack([rgb * al[..., None], al])          # premultiplied linear


def down(p):
    return cv2.resize(p, (CELL, CELL), interpolation=cv2.INTER_AREA)


def border(n=CELL, w=0.06):
    x = np.linspace(0.0, 1.0, n)
    m = np.clip(np.minimum(x, 1.0 - x) / w, 0.0, 1.0)
    m = m * m * (3.0 - 2.0 * m)
    return np.outer(m, m).astype(np.float32)


BORDER = border()


def frames(sim, pass_name):
    d = ROOT / DIRS[sim] / pass_name
    return sorted(d.glob("*.png"))


def straight(p, eps=0.06):
    # unpremultiplied colour; thin edges take the colour of their neighbourhood
    a = p[..., 3]
    s = p[..., :3] / np.maximum(a, 1e-4)[..., None]
    bp = cv2.GaussianBlur(p[..., :3], (0, 0), 3.0)
    ba = cv2.GaussianBlur(a, (0, 0), 3.0)
    sb = bp / np.maximum(ba, 1e-4)[..., None]
    w = np.clip(a / eps, 0.0, 1.0)[..., None]
    return np.clip(s * w + sb * (1.0 - w), 0.0, 4.0)


def atlas(cells):
    out = np.zeros((CELL * 8, CELL * 8, 4), np.float32)
    for i, c in enumerate(cells[:64]):
        y, x = divmod(i, 8)
        out[y * CELL:(y + 1) * CELL, x * CELL:(x + 1) * CELL] = c
    return out


def save(img01, name):
    path = OUT / name
    im = Image.fromarray((np.clip(img01, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), "RGBA")
    im.save(path, "WEBP", lossless=True, quality=100, method=6, exact=True)
    report[name] = {"bytes": path.stat().st_size, "size": im.size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    print("wrote", path, path.stat().st_size)


def extent(alphas):
    # largest share of the frame covered by opacity > 0.1 (width, height), and the frame where it peaks
    best = (0.0, 0.0, 0)
    for i, a in enumerate(alphas):
        ys, xs = np.nonzero(a > 0.1)
        if len(xs):
            w = (xs.max() - xs.min() + 1) / a.shape[1]
            h = (ys.max() - ys.min() + 1) / a.shape[0]
            if w * h > best[0] * best[1]:
                best = (round(w, 3), round(h, 3), i)
    return best


def derived_light(alpha, k=1.0 / 100.0):
    # Directional self-shadowing from the sprite's own opacity (EEVEE's volume shadows left dark caps in the
    # renders): optical depth along the view per pixel, accumulated toward the light across the frame, divided by
    # a typical puff thickness (k = 1 / ~70 px). Light from the right / top / left = transmittance to the edge.
    tau = -np.log(np.clip(1.0 - alpha * 0.995, 1e-4, 1.0))
    tau = cv2.GaussianBlur(tau, (0, 0), 2.0)
    def acc(t):   # sum of t from the light's edge (index 0) up to, not including, each pixel
        s = np.cumsum(t, axis=1)
        return s - t * 0.5
    right = np.exp(-k * acc(tau[:, ::-1])[:, ::-1])
    left = np.exp(-k * acc(tau))
    top = np.exp(-k * acc(tau.T).T)
    return (0.12 + 0.88 * np.dstack([right, top, left])).astype(np.float32)


def light_atlas(sim, name, idx=None):
    if DERIVED:
        R = frames(sim, "R")
        if idx is not None:
            R = [R[i] for i in idx]
        cells = []
        for fr in R:
            a = down(load(fr))[..., 3] * BORDER
            lm = derived_light(a)
            cells.append(np.dstack([np.sqrt(np.clip(lm, 0, 1)), a]))
        save(atlas(cells), name)
        report[name].update({"light": "derived from opacity", "frames": len(cells), "extent_w_h_frame": extent([c[..., 3] for c in cells])})
        return
    R, T, L = (frames(sim, p) for p in "RTL")
    if idx is not None:
        R, T, L = [R[i] for i in idx], [T[i] for i in idx], [L[i] for i in idx]
    cells_p = []
    for fr, ft, fl in zip(R, T, L):
        pr, pt, pl = (down(load(f)) for f in (fr, ft, fl))
        lum = [straight(p).mean(axis=2) for p in (pr, pt, pl)]
        cells_p.append((np.dstack(lum), pr[..., 3] * BORDER))
    peaks = []
    for lum, a in cells_p:
        m = a > 0.3
        if m.any():
            peaks.append(lum.max(axis=2)[m])
    scale = 1.0 / max(np.percentile(np.concatenate(peaks), 99.5), 1e-4)
    cells = [np.dstack([np.sqrt(np.clip(lum * scale, 0, 1)), a]) for lum, a in cells_p]
    save(atlas(cells), name)
    report[name].update({"light_scale": float(scale), "frames": len(cells), "extent_w_h_frame": extent([c[..., 3] for c in cells])})


def emission_cells(sim, idx=None):
    E = frames(sim, "E")
    if idx is not None:
        E = [E[i] for i in idx]
    return [down(load(f)) for f in E]


FIRE_RAMP = np.array([[0.0, 0.0, 0.0, 0.0], [0.12, 0.40, 0.05, 0.01], [0.35, 1.0, 0.30, 0.04], [0.6, 1.0, 0.58, 0.14],
                      [0.85, 1.0, 0.82, 0.42], [1.0, 1.0, 0.95, 0.78]])


def fire_ramp(lum):
    # gradient map on brightness: dim flame deep red, then orange, yellow, pale yellow-white at the hottest
    out = np.zeros(lum.shape + (3,), np.float32)
    for ch in range(3):
        out[..., ch] = np.interp(lum, FIRE_RAMP[:, 0], FIRE_RAMP[:, ch + 1])
    return out * np.clip(lum * 1.15, 0, 1)[..., None] ** 0.5


def emission_atlas(cells_p, name, recolour=False, heat=1.0):
    peak = np.percentile(np.concatenate([c[..., :3].max(axis=2)[c[..., 3] > 0.02] for c in cells_p if (c[..., 3] > 0.02).any()]), 99.9)
    scale = 1.0 / max(peak, 1e-4)
    if recolour:
        cells = []
        for c in cells_p:
            lum = np.clip((c[..., 0] * 0.3 + c[..., 1] * 0.59 + c[..., 2] * 0.11) * scale * heat, 0, 1)
            cells.append(np.dstack([np.sqrt(np.clip(fire_ramp(lum), 0, 1)), c[..., 3] * BORDER]))
    else:
        cells = [np.dstack([np.sqrt(np.clip(c[..., :3] * scale, 0, 1)), c[..., 3] * BORDER]) for c in cells_p]
    save(atlas(cells), name)
    report[name].update({"emission_scale": float(scale), "frames": len(cells), "extent_w_h_frame": extent([c[..., 3] for c in cells])})


# fireball: 64 frames of emission and light map
if (ROOT / DIRS["fireball"] / "E").exists():
    emission_atlas(emission_cells("fireball"), "fx_fireball_emission_8x8.webp", recolour=True, heat=0.72)
    light_atlas("fireball", "fx_fireball_light_8x8.webp")

# smoke puff light map
if (ROOT / DIRS["smoke"] / "R").exists():
    light_atlas("smoke", "fx_smoke_light_8x8.webp")

def loop_cells(raw, N=64, K=16):
    # 80 rendered frames -> 64 looping frames (the last 16 cross-fade into the frames before the first)
    if len(raw) < N + K:
        print("loop: only", len(raw), "frames, no cross-fade")
        return raw[:N]
    loop = []
    for i in range(N):
        a = raw[i + K]
        if i >= N - K:
            w = (i - (N - K) + 1) / K
            w = w * w * (3 - 2 * w)
            a = a * (1 - w) + raw[i + K - N] * w
        loop.append(a)
    return loop


# fire loop
if (ROOT / DIRS["fire"] / "E").exists():
    emission_atlas(loop_cells(emission_cells("fire")), "fx_fire_loop_8x8.webp", recolour=True, heat=0.8)

# fire jet loop (the blown-open tank's crater): hotter core, the same ramp
if (ROOT / DIRS["jet"] / "E").exists():
    emission_atlas(loop_cells(emission_cells("jet")), "fx_fire_jet_8x8.webp", recolour=True, heat=0.75)

# scorch decal: the ground burst's density seen from above
sc = frames("scorch", "A")
if sc:
    a = cv2.imread(str(sc[-1]), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535.0
    al = a[..., 3]
    ys, xs = np.nonzero(al > 0.02)
    cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
    r = max(ys.max() - ys.min(), xs.max() - xs.min()) * 0.56
    y0, y1, x0, x1 = int(cy - r), int(cy + r), int(cx - r), int(cx + r)
    crop = al[max(y0, 0):y1, max(x0, 0):x1]
    crop = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_AREA)
    d = np.clip(crop / max(np.percentile(crop, 99.5), 1e-4), 0, 1)
    yy, xx = np.mgrid[0:512, 0:512]
    rr = np.hypot(yy - 255.5, xx - 255.5) / 256.0
    core = np.clip(1.0 - rr * 1.1, 0, 1) ** 0.7
    alpha = np.clip((d ** 0.8) * 0.85 + core * 0.35, 0, 1) * np.clip((1.0 - rr) / 0.12, 0, 1)
    # albedo: black soot at the centre, brown-grey ash outward, darker where the burst was dense
    soot = np.array([0.025, 0.022, 0.020])
    ash = np.array([0.16, 0.13, 0.10])
    k = np.clip(rr * 1.3 - d * 0.4, 0, 1)[..., None]
    rgb = soot * (1 - k) + ash * k
    rgb_s = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    save(np.dstack([rgb_s, alpha]), "fx_scorch.webp")
    # glow: embers in the dense middle (neutral warm white, tinted by the decal's modulate)
    rng = np.random.default_rng(5)
    speck = cv2.GaussianBlur(rng.random((512, 512)).astype(np.float32), (0, 0), 2.0)
    speck = np.clip((speck - 0.5) * 8.0, 0, 1)
    glow = np.clip(d * core * 1.6, 0, 1) * (0.35 + 0.65 * speck)
    g = np.dstack([glow, glow * 0.85, glow * 0.7, np.ones_like(glow)])
    save(g, "fx_scorch_glow.webp")

(ROOT / "atlas_report.json").write_text(json.dumps(report, indent=1))
print(json.dumps(report, indent=1))
