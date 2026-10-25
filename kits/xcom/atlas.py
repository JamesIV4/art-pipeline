# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/atlas.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""AVENGER v2 trim atlas (2048 px): image_gen decals (nose band, badge, consoles, engine markings) plus flat
paint swatches sampled from the sprites' palette, with derived normal / ORM and an emissive map
(lamp pixels of the console decals, light swatches). Cell layout lives in meshdata.py (SWATCH, DECAL).
Writes textures/out/avg2_trim_{albedo,normal,orm,emissive}.png (never overwrites; bump NAME to revise).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import WORK  # noqa: E402
import meshdata as MD  # noqa: E402
from textures import gaussian  # noqa: E402

NAME = sys.argv[1] if len(sys.argv) > 1 else "avg2_trim"
FORCE = "--force" in sys.argv   # out/ holds only this task's unpublished working maps
GEN = WORK / "textures"
OUT = WORK / "textures/out"
S = 2048

# swatch: sRGB colour, roughness, metal, emissive strength (0..1 of the colour)
SW = {
    "section": ((190, 156, 226), 0.80, 0.0, 0.0),   # sprites' flat lilac cut-section colour
    "yellow": ((228, 178, 52), 0.50, 0.0, 0.0),
    "orange": ((214, 132, 24), 0.50, 0.0, 0.0),
    "purple": ((150, 88, 180), 0.30, 0.0, 0.0),     # engine exhaust domes (glossy paint / ceramic)
    "lavender": ((126, 118, 162), 0.55, 0.0, 0.0),  # landing legs, hatch (P052/P053 mid lavender)
    "white": ((200, 200, 200), 0.50, 0.0, 0.0),
    "red": ((236, 104, 104), 0.45, 0.0, 0.0),
    "glass": ((140, 184, 226), 0.12, 0.0, 0.0),
    "steel": ((160, 164, 168), 0.40, 1.0, 0.0),
    "dark": ((84, 92, 100), 0.60, 0.0, 0.0),
    "black": ((34, 36, 40), 0.50, 0.0, 0.0),
    "bluelight": ((90, 170, 255), 0.30, 0.0, 1.0),
    "hullgrey": ((132, 138, 140), 0.60, 0.0, 0.0),
    "beige": ((204, 188, 184), 0.65, 0.0, 0.0),
    "taupe": ((148, 124, 116), 0.65, 0.0, 0.0),
    "rubber": ((52, 56, 60), 0.85, 0.0, 0.0),
    "amber": ((244, 192, 48), 0.35, 0.0, 1.0),
    "pinkpanel": ((216, 160, 164), 0.55, 0.0, 0.0),
    "redglow": ((252, 112, 104), 0.40, 0.0, 0.9),
    "purpledark": ((120, 50, 140), 0.40, 0.0, 0.0),
    "lavlight": ((164, 160, 196), 0.55, 0.0, 0.0),
    "greymid": ((124, 124, 124), 0.55, 0.0, 0.0),
    "seat": ((168, 166, 200), 0.75, 0.0, 0.0),
    "orangedark": ((186, 140, 58), 0.55, 0.0, 0.0),
}


def put(dst, cell, img):
    x, y, w, h = cell
    dst.paste(img.convert("RGB").resize((w, h), Image.Resampling.LANCZOS), (x, y))


def main():
    alb = Image.new("RGB", (S, S), (132, 138, 140))
    rough = np.full((S, S), 0.55, np.float32)
    metal = np.zeros((S, S), np.float32)
    emis_mask = np.zeros((S, S), np.float32)
    for n, (c, r, m, e) in SW.items():
        x, y, w, h = MD.SWATCH[n]
        alb.paste(Image.new("RGB", (w, h), c), (x, y))
        rough[y:y + h, x:x + w] = r
        metal[y:y + h, x:x + w] = m
        emis_mask[y:y + h, x:x + w] = e
    nose = Image.open(GEN / "gen_noseband_a.png")
    if NAME.endswith("_b"):
        # exactly four stripe periods (gap to gap), so the band tiles every 2 m with ~4 stripes per tile like P010
        nose = nose.crop((182, 0, 1297, nose.height))
    put(alb, MD.DECAL["noseband"], nose)
    put(alb, MD.DECAL["badge"], Image.open(GEN / "gen_badge_a.png"))
    con = Image.open(GEN / "gen_console_a.png")
    hw = con.width // 2
    put(alb, MD.DECAL["console_pink"], con.crop((0, 0, hw, con.height)))
    put(alb, MD.DECAL["console_beige"], con.crop((hw, 0, con.width, con.height)))
    em = Image.open(GEN / "gen_engine_marks_a.png")
    put(alb, MD.DECAL["mark_18"], em.crop((200, 160, 760, 720)))
    put(alb, MD.DECAL["mark_red"], em.crop((1026, 154, 1586, 714)))
    if NAME.endswith("_b"):
        # root 2026-10-03: nose band mostly solid yellow; diagonals toned down to subtle orange, orange lower edge
        x, y, w, h = MD.DECAL["noseband"]
        nb = np.asarray(alb.crop((x, y, x + w, y + h)), dtype=np.float32)
        yel = np.array([232.0, 180.0, 44.0])
        org = np.array([214.0, 128.0, 20.0])
        nb = yel + (nb - yel) * 0.35
        rows = np.linspace(0.0, 1.0, h)[:, None, None]
        lower = np.clip((rows - 0.70) / 0.12, 0.0, 1.0) * (rows < 0.93)
        nb = nb * (1 - 0.55 * lower) + org * 0.55 * lower
        alb.paste(Image.fromarray(np.clip(nb, 0, 255).astype(np.uint8)), (x, y))
        put(alb, MD.DECAL["glass"], Image.open(GEN / "gen_glass_a.png"))
        put(alb, MD.DECAL["grille"], Image.open(GEN / "gen_grille_a.png"))
        x, y, w, h = MD.SWATCH["hullgrey"]
        alb.paste(Image.new("RGB", (w, h), (116, 121, 128)), (x, y))
        x, y, w, h = MD.DECAL["glass"]
        rough[y:y + h, x:x + w] = 0.10
    a = np.asarray(alb, dtype=np.float32) / 255.0
    # console lamps glow: saturated bright pixels inside the console cells
    for key in ("console_pink", "console_beige"):
        x, y, w, h = MD.DECAL[key]
        sub = a[y:y + h, x:x + w]
        mx, mn = sub.max(-1), sub.min(-1)
        sat = (mx - mn) / np.maximum(mx, 1e-3)
        lamp = ((sat > 0.45) & (mx > 0.55)).astype(np.float32)
        # screens: dark blue-green interiors with cyan lines -> faint glow
        screen = ((sub[..., 2] > sub[..., 0] + 0.05) & (mx < 0.45)).astype(np.float32) * 0.35
        emis_mask[y:y + h, x:x + w] = np.maximum(lamp, screen)
    for key in ("noseband", "badge", "console_pink", "console_beige", "mark_18", "mark_red", "grille"):
        x, y, w, h = MD.DECAL[key]
        rough[y:y + h, x:x + w] = 0.5
    lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    hp = lum - gaussian(lum, 10)
    # flat normals in swatch rows
    hp[1280:, :] = 0.0
    k = 4.0 * S / 1024
    dx = (np.roll(hp, -1, 1) - np.roll(hp, 1, 1)) * 0.5 * k
    dy = (np.roll(hp, -1, 0) - np.roll(hp, 1, 0)) * 0.5 * k
    nx, ny, nz = -dx, dy, np.ones_like(dx)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / L, ny / L, nz / L], -1)
    cav = np.maximum(gaussian(lum, 4) - lum, 0)
    ao = np.clip(1 - cav * 2.5, 0.6, 1.0)
    ao[1280:, :] = 1.0
    orm = np.stack([ao, rough, metal], -1)
    emis = a * emis_mask[..., None]
    out = {"albedo": alb, "normal": Image.fromarray(np.clip((nrm * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)),
           "orm": Image.fromarray(np.clip(orm * 255 + 0.5, 0, 255).astype(np.uint8)),
           "emissive": Image.fromarray(np.clip(emis * 255 + 0.5, 0, 255).astype(np.uint8))}
    for k_, im in out.items():
        p = OUT / f"{NAME}_{k_}.png"
        if p.exists() and not FORCE:
            print("exists, kept", p.name)
            continue
        im.save(p)
    alb.resize((1024, 1024)).save(OUT / f"{NAME}_preview.png")
    print("atlas written", NAME)


if __name__ == "__main__":
    main()
