"""Origin: S:/Repos/trick-or-treat/art/tools/assemble_vfx.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. Sprite and flipbook name lists are still the trick-or-treat set (edit SINGLES/SHEETS).

Packs the frames rendered by make_vfx.py into the game's particle textures.

Single sprites are downsampled to 128 px; flipbooks become 4x4 atlases of 128 px cells. Colour is
kept white where the art is meant to be tinted in game, and alpha is premultiplied-safe (colour is
set to white wherever alpha is zero, so filtering never pulls in dark fringes).
Run: python <pipeline>/tools/vfx/assemble_vfx.py   (from the game root, or set ART_GAME_ROOT)
"""
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline_paths as P  # noqa: E402
FRAMES = P.path("vfx_frames")
OUT = P.path("vfx_out")
CELL = 128
SINGLES = ("sparkle", "glow", "ring")    # <name>.png -> 128 px sprite
SHEETS = ("smoke", "flame", "swirl")     # <name>_00..15.png -> 4x4 atlas


def clean(img):
    """Unpremultiplied edges: give fully transparent pixels the nearest visible colour (white)."""
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 0:
                px[x, y] = (255, 255, 255, 0)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in SINGLES:
        img = clean(Image.open(FRAMES / f"{name}.png")).resize((CELL, CELL), Image.LANCZOS)
        img.save(OUT / f"{name}.png")
        print("wrote", name)
    for name in SHEETS:
        sheet = Image.new("RGBA", (CELL * 4, CELL * 4), (255, 255, 255, 0))
        for f in range(16):
            img = clean(Image.open(FRAMES / f"{name}_{f:02d}.png")).resize((CELL, CELL), Image.LANCZOS)
            sheet.paste(img, ((f % 4) * CELL, (f // 4) * CELL))
        sheet.save(OUT / f"{name}_4x4.png")
        print("wrote", name, "sheet")


if __name__ == "__main__":
    main()
