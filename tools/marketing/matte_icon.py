"""Origin: art-pipeline original (2026-10-26), from trick-or-treat's game-icon session.

Cuts an engine-rendered subject out of its background with a difference matte and centres it in a
square, transparent icon (see techniques/engine-rendered-icon.md).

Render the same frame twice, once on a black background and once on a white one (trick-or-treat:
`--preview=<res gltf> --icon` and `--icon-white`). Then, per pixel:
    alpha = 1 - (white - black)          coverage, including soft glow and anti-aliased edges
    colour = black / alpha               un-premultiplied
Godot's lens vignette darkens the white background towards the frame edges, so only the --box crop
(the middle, where the white stays ~255) is used.

    python matte_icon.py black.png white.png out.png [--box 400,60,1200,860] [--size 1024]
        [--margin 0.92] [--min-alpha 14] [--sizes-sheet sheet.png]
--sizes-sheet writes the icon at 1024/256/64/32 px on a checker and on a light strip, to judge how it
reads in a taskbar. Needs Pillow.
"""
import argparse

from PIL import Image, ImageChops


def matte(black: Image.Image, white: Image.Image, min_alpha: int) -> Image.Image:
    alpha = ImageChops.subtract(white, black).convert("L").point(lambda v: 255 - v)
    px_b, px_a = black.load(), alpha.load()
    out = Image.new("RGBA", black.size)
    px_o = out.load()
    for y in range(black.size[1]):
        for x in range(black.size[0]):
            a = px_a[x, y]
            if a < min_alpha:
                continue  # the vignette and noise in the background, not the subject
            r, g, b = px_b[x, y]
            k = 255.0 / a
            px_o[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)), a)
    return out


def sizes_sheet(icon: Image.Image, path: str) -> None:
    sizes = (1024, 256, 64, 32)
    width = sum(sizes) + 40 * len(sizes)
    sheet = Image.new("RGBA", (width, 1024 + 300), (40, 40, 48, 255))
    for i in range(0, width, 32):
        for j in range(0, 1024, 32):
            if (i // 32 + j // 32) % 2:
                sheet.paste((58, 58, 66, 255), (i, j, i + 32, j + 32))
    sheet.paste((235, 235, 240, 255), (0, 1024, width, 1024 + 300))
    x = 0
    for s in sizes:
        small = icon.resize((s, s), Image.LANCZOS)
        sheet.alpha_composite(small, (x, (1024 - s) // 2))
        if s < 1024:
            sheet.alpha_composite(small, (x, 1024 + (300 - s) // 2))
        x += s + 40
    sheet.save(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("black")
    ap.add_argument("white")
    ap.add_argument("out")
    ap.add_argument("--box", default="", help="crop x0,y0,x1,y1 applied to both renders first")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--margin", type=float, default=0.92, help="subject's longest side as a fraction of the icon")
    ap.add_argument("--min-alpha", type=int, default=14)
    ap.add_argument("--sizes-sheet", default="")
    a = ap.parse_args()
    black = Image.open(a.black).convert("RGB")
    white = Image.open(a.white).convert("RGB")
    if black.size != white.size:
        raise SystemExit("the two renders must be the same size")
    if a.box:
        box = tuple(int(v) for v in a.box.split(","))
        black, white = black.crop(box), white.crop(box)
    fg = matte(black, white, a.min_alpha)
    bbox = fg.getbbox()
    if not bbox:
        raise SystemExit("nothing left after the matte: check the renders and --min-alpha")
    fg = fg.crop(bbox)
    side = int(max(fg.size) / a.margin)
    canvas = Image.new("RGBA", (side, side))
    canvas.alpha_composite(fg, ((side - fg.size[0]) // 2, (side - fg.size[1]) // 2))
    icon = canvas.resize((a.size, a.size), Image.LANCZOS)
    icon.save(a.out)
    if a.sizes_sheet:
        sizes_sheet(icon, a.sizes_sheet)
    print(a.out)


if __name__ == "__main__":
    main()
