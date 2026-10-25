"""Origin: S:/Repos/trick-or-treat/art/tools/make_fire.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. Frames dir is vfx_frames.

Renders the flame flipbook (flame_4x4) procedurally: a soft, turbulent tongue of fire.

Replaces the Blender teardrop from make_vfx.py, which read as a cartoon raindrop. Here the flame
is a heat field rather than a shape: a soft envelope (wide at the base, narrowing upward) warped
sideways by scrolling noise and eaten away from the edges and top by a second, finer noise, so
it breaks into licking tongues and wisps instead of having an outline. Heat maps through a
fire ramp (deep red edges, orange body, yellow, near-white core) with alpha following heat, and
it is drawn additively in game, so the dim red fringe just warms whatever is behind it.

The 16 frames play once over a particle's life: the flame swells up, flickers as the noise rises
through it, then cools and breaks apart into wisps.

Writes <vfx_frames>/flame_00..15.png (default art/vfx/_frames); assemble_vfx.py packs them into the game atlas.
Run:
  python <pipeline>/tools/vfx/make_fire.py      (from the game root, or set ART_GAME_ROOT)
  python <pipeline>/tools/vfx/assemble_vfx.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline_paths as P  # noqa: E402
ROOT = P.GAME_ROOT
FRAMES = P.path("vfx_frames")
N = 256


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def fbm(rng, w, h, cells, weights):
    """Fractal value noise, 0..1, as an (h, w) array (smooth bicubic upsampling of random grids)."""
    out = np.zeros((h, w), np.float32)
    for c, wt in zip(cells, weights):
        grid = rng.random((max(2, int(c * h / w)), c)).astype(np.float32)
        img = Image.fromarray(grid, mode="F").resize((w, h), Image.BICUBIC)
        out += np.asarray(img) * wt
    out /= sum(weights)
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / (hi - lo), 0.0, 1.0)


# Fire ramp over heat 0..1: colour stops (heat, r, g, b).
RAMP = np.array([
    (0.00, 0.45, 0.04, 0.00),
    (0.18, 0.80, 0.14, 0.02),
    (0.38, 1.00, 0.38, 0.05),
    (0.60, 1.00, 0.66, 0.18),
    (0.82, 1.00, 0.90, 0.55),
    (1.00, 1.00, 0.98, 0.88),
], np.float32)


def ramp(heat):
    rgb = np.stack([np.interp(heat, RAMP[:, 0], RAMP[:, k]) for k in (1, 2, 3)], axis=-1)
    return rgb


def main():
    FRAMES.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(23)
    tall = N * 4
    # Coarse turbulence warps the flame sideways; fine noise erodes it into tongues and wisps.
    warp = fbm(rng, N, tall, (5, 10, 20), (0.6, 0.3, 0.1))
    erode = fbm(rng, N, tall, (8, 16, 32, 64), (0.45, 0.3, 0.17, 0.08))
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    X = xs / (N - 1) * 2.0 - 1.0
    Y = 1.0 - ys / (N - 1) * 2.0  # up is +Y
    for f in range(16):
        t = f / 15.0
        grow = smoothstep(0.0, 0.3, t)
        cool = smoothstep(0.45, 1.0, t)
        # Noise rises through the flame: a window sliding down the tall field moves it up on screen.
        rise = int(t * N * 1.6)
        w_s = warp[rise // 2:rise // 2 + N]
        e_s = erode[rise:rise + N]
        base, height = -0.78, 1.25 + 0.3 * grow
        yn = (Y - base) / height  # 0 at the base, 1 at the top of the flame
        ynn = np.clip(yn, 0.0, 1.0)
        width = (0.36 + 0.12 * grow) * (1.0 - ynn) ** 0.75 + 0.04
        sway = (w_s - 0.5) * (0.12 + 0.55 * ynn ** 1.3)
        envelope = np.exp(-((X - sway) / width) ** 2 * 1.6)
        envelope *= smoothstep(-0.12, 0.12, yn)  # a soft rounded base, no hard bottom edge
        envelope *= 1.0 - smoothstep(0.75, 1.15, yn)
        # Erode: the edges and top burn away into tongues, more as the flame ages.
        bite = (0.45 + 0.5 * cool) * (0.35 + 0.9 * ynn) * (1.0 - e_s)
        heat = envelope * (1.0 - 0.4 * cool) - bite
        heat *= 0.55 + 0.45 * grow
        heat = np.clip(heat, 0.0, 1.0)
        rgb = ramp(heat)
        alpha = smoothstep(0.02, 0.42, heat) * (1.0 - 0.35 * cool)
        img = np.concatenate([rgb, alpha[..., None]], axis=-1)
        Image.fromarray((img * 255.0 + 0.5).astype(np.uint8), "RGBA").save(FRAMES / f"flame_{f:02d}.png")
    print("FIRE_DONE")


if __name__ == "__main__":
    main()
