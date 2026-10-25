"""Simulates the gameplay camera distance on an engine preview sheet: each quadrant of a 2x2
sheet is shrunk so the subject is about `--px` pixels tall, then blown back up with
nearest-neighbour so the pixels can be judged. Optionally pastes a concept-image crop (same
treatment) alongside for comparison.

Origin: S:/Repos/trick-or-treat/art/team/characters_candy/batch03/distance_check.py
(imported 2026-10-25). Changed: the concept image is --concept-image (was a hard-coded
trick-or-treat path); the quadrant size is derived from the sheet instead of 800x450.
In trick-or-treat the hero at ~15 m is ~70 px tall on a 900 px screen; measure your own game.

    python <pipeline>/tools/review/distance_check.py <engine.png> <out.png> [--subject 300] [--px 70]
        [--concept-image art/review/concept/target.png --concept x0,y0,x1,y1]
"""
import sys

from PIL import Image

args = sys.argv[1:]
if len(args) < 2:
    raise SystemExit(__doc__)
src, out = args[0], args[1]


def opt(name, default):
    return args[args.index(name) + 1] if name in args else default


subject = float(opt("--subject", 300))
px = float(opt("--px", 70))
k = px / subject
im = Image.open(src).convert("RGB")
qw, qh = im.width // 2, im.height // 2
tiles = []
for qy in range(2):
    for qx in range(2):
        q = im.crop((qx * qw, qy * qh, qx * qw + qw, qy * qh + qh))
        small = q.resize((max(1, int(qw * k)), max(1, int(qh * k))), Image.LANCZOS)
        tiles.append(small.resize((small.width * 3, small.height * 3), Image.NEAREST))
conc = opt("--concept", None)
if conc:
    x0, y0, x1, y1 = [int(v) for v in conc.split(",")]
    concept_path = opt("--concept-image", None)
    if not concept_path:
        raise SystemExit("--concept needs --concept-image <path>")
    c = Image.open(concept_path).convert("RGB").crop((x0, y0, x1, y1))
    ck = px / (y1 - y0)
    cs = c.resize((max(1, int(c.width * ck)), max(1, int(c.height * ck))), Image.LANCZOS)
    tiles.append(cs.resize((cs.width * 3, cs.height * 3), Image.NEAREST))
W = sum(t.width for t in tiles[:2]) + (tiles[4].width if len(tiles) > 4 else 0)
H = max(tiles[0].height * 2, tiles[4].height if len(tiles) > 4 else 0)
sheet = Image.new("RGB", (W, H), (20, 20, 30))
sheet.paste(tiles[0], (0, 0))
sheet.paste(tiles[1], (tiles[0].width, 0))
sheet.paste(tiles[2], (0, tiles[0].height))
sheet.paste(tiles[3], (tiles[0].width, tiles[0].height))
if len(tiles) > 4:
    sheet.paste(tiles[4], (tiles[0].width * 2, 0))
sheet.save(out)
print(out, sheet.size)
