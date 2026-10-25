# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/inspect_v2.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""AVENGER v2 read-only source inspection.

Outputs (into ./sources): per-record 8x sheets with every PCK frame, a full-craft sprite
composite at 4x/6x (OpenXcom draw order: level, then screen rows, parts floor/west/north/object,
sprite raised by P_Level), and decoded UFOpaedia SPK images (GEOGRAPH/UP*.SPK, palette 3/4).
"""
import json
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT, WORK  # noqa: E402  (also puts art-pipeline/tools/review on sys.path)
from catalog_reference import palette, decode_pck  # noqa: E402

OUT = WORK / "sources"
OUT.mkdir(exist_ok=True)
FONT = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)


def mcd(name):
    raw = (ROOT / f"reference/TERRAIN/{name}.MCD").read_bytes()
    recs = []
    for i in range(len(raw) // 62):
        d = raw[i * 62:(i + 1) * 62]
        recs.append({"record": i, "frames": list(d[0:8]), "lofts": list(d[8:20]), "ufo_door": d[30], "big_wall": d[33],
                     "door": d[35], "die_mcd": d[44], "alt_mcd": d[46], "t_level": struct.unpack_from("b", d, 48)[0],
                     "p_level": d[49], "tile_type": d[53], "armor": d[42], "light_source": d[58], "tu_walk": d[39]})
    return recs


def load_map():
    data = (ROOT / "reference/MAPS/AVENGER.MAP").read_bytes()
    sy, sx, sz = data[:3]
    nblank = len((ROOT / "reference/TERRAIN/BLANKS.MCD").read_bytes()) // 62
    grid = {}
    for i in range(sx * sy * sz):
        pos = (i % sx, i // sx % sy, sz - 1 - i // (sx * sy))
        grid[pos] = [None if not v else (None if v < nblank else v - nblank) for v in data[3 + i * 4:7 + i * 4]]
    return (sx, sy, sz), grid


def composite(frames, recs, size, grid, zmax, scale, frame_index=0, highlight=None):
    sx, sy, sz = size
    W, H = (sx + sy) * 16 + 64, (sx + sy) * 8 + sz * 24 + 80
    can = Image.new("RGBA", (W, H), (30, 36, 44, 255))
    ox, oy = sy * 16 + 16, 24 * sz + 24
    for z in range(zmax + 1):
        for y in range(sy):
            for x in range(sx):
                for part in (0, 1, 2, 3):
                    r = grid[(x, y, z)][part]
                    if r is None:
                        continue
                    fr = frames[recs[r]["frames"][frame_index % 8]]
                    if highlight is not None and r not in highlight:
                        fr = Image.blend(Image.new("RGBA", fr.size, (0, 0, 0, 0)), fr, 1.0)
                        a = fr.split()[3].point(lambda v: v // 3)
                        fr = fr.copy(); fr.putalpha(a)
                    px, py = ox + (x - y) * 16 - 16, oy + (x + y) * 8 - z * 24 - recs[r]["p_level"]
                    can.alpha_composite(fr, (px, py))
    bbox = can.getbbox()
    return can.resize((W * scale, H * scale), Image.Resampling.NEAREST)


def decode_spk(path, colors):
    data = path.read_bytes()
    px = [0] * (320 * 200)
    i, p = 0, 0
    while i + 1 < len(data):
        cmd = struct.unpack_from("<H", data, i)[0]; i += 2
        if cmd == 0xFFFF:
            n = struct.unpack_from("<H", data, i)[0]; i += 2; p += n * 2
        elif cmd == 0xFFFE:
            n = struct.unpack_from("<H", data, i)[0]; i += 2
            for k in range(n * 2):
                if p < len(px):
                    px[p] = data[i + k]
                p += 1
            i += n * 2
        elif cmd == 0xFFFD:
            break
    im = Image.new("RGB", (320, 200))
    im.putdata([colors[v][:3] for v in px])
    return im


def pal_index(idx):
    raw = (ROOT / "reference/GEODATA/PALETTES.DAT").read_bytes()
    off = idx * (768 + 6)
    return [tuple(v * 4 for v in raw[off + k * 3:off + k * 3 + 3]) for k in range(256)]


def main():
    colors = palette(ROOT / "reference")
    frames = decode_pck(ROOT / "reference/TERRAIN/AVENGER.PCK", colors)
    recs = mcd("AVENGER")
    size, grid = load_map()
    # per-record 8x sheets with all distinct frames
    S = 8
    for r in recs:
        fs = sorted(set(r["frames"]), key=r["frames"].index)
        W = Image.new("RGB", (len(fs) * (32 * S + 20) + 20, 40 * S + 60), "#1b232c")
        d = ImageDraw.Draw(W)
        d.text((10, 6), f"AVENGER rec {r['record']:03d} type {r['tile_type']} frames {r['frames']} P_Level {r['p_level']}", font=FONT, fill="#f2ddaa")
        for k, f in enumerate(fs):
            big = frames[f].resize((32 * S, 40 * S), Image.Resampling.NEAREST)
            bg = Image.new("RGBA", big.size, (40, 52, 64, 255)); bg.alpha_composite(big)
            ox = 20 + k * (32 * S + 20)
            W.paste(bg.convert("RGB"), (ox, 40))
            for (x0, y0, x1, y1) in ((16, 24, 32, 32), (32, 32, 16, 40), (16, 40, 0, 32), (0, 32, 16, 24)):
                d.line((ox + x0 * S, 40 + y0 * S, ox + x1 * S, 40 + y1 * S), fill="#806a30")
        W.save(OUT / f"rec{r['record']:03d}_8x.png")
    for zmax in range(3):
        composite(frames, recs, size, grid, zmax, 4).save(OUT / f"composite_upto_z{zmax}_4x.png")
    # anim frame variants of the full composite
    for fi in (0, 4):
        composite(frames, recs, size, grid, 2, 3, frame_index=fi).save(OUT / f"composite_full_frame{fi}_3x.png")
    # UFOpaedia
    for pidx in (3, 4):
        cols = pal_index(pidx)
        ims = []
        for f in sorted((ROOT / "reference/GEOGRAPH").glob("UP0*.SPK")):
            try:
                ims.append((f.stem, decode_spk(f, cols)))
            except Exception as e:  # noqa
                print("spk fail", f, e)
        n = len(ims)
        sheet = Image.new("RGB", (6 * 330, ((n + 5) // 6) * 220), "#111")
        dd = ImageDraw.Draw(sheet)
        for k, (nm, im) in enumerate(ims):
            sheet.paste(im, ((k % 6) * 330, (k // 6) * 220))
            dd.text(((k % 6) * 330 + 4, (k // 6) * 220 + 202), nm, font=FONT, fill="#ff0")
        sheet.save(OUT / f"ufopaedia_pal{pidx}.png")
        if pidx == 3:
            for nm, im in ims:
                im.save(OUT / f"{nm}_pal3.png")
    (OUT / "records.json").write_text(json.dumps(recs, indent=0), encoding="utf-8")


if __name__ == "__main__":
    main()
