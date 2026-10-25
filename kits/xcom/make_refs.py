# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/make_refs.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""Enlarged sprite crops used as image_gen references (read-only sources -> ./refs)."""
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT, WORK  # noqa: E402  (also puts art-pipeline/tools/review on sys.path)
from catalog_reference import palette, decode_pck  # noqa: E402

OUT = WORK / "refs"
OUT.mkdir(exist_ok=True)
fr = decode_pck(ROOT / "reference/TERRAIN/AVENGER.PCK", palette(ROOT / "reference"))
comp = Image.open(WORK / "sources/composite_upto_z2_4x.png").convert("RGB")
comp1 = Image.open(WORK / "sources/composite_upto_z1_4x.png").convert("RGB")


def strip(ids, name, S=10, bg=(40, 52, 64)):
    W = Image.new("RGB", (len(ids) * 32 * S, 40 * S), bg)
    for k, i in enumerate(ids):
        b = Image.new("RGBA", (32, 40), bg + (255,)); b.alpha_composite(fr[i])
        W.paste(b.convert("RGB").resize((32 * S, 40 * S), Image.Resampling.NEAREST), (k * 32 * S, 0))
    W.save(OUT / name)


# composite crops (composite 4x: crop origin 300,560 in the full image)
comp.crop((300 + 280, 560 + 130, 300 + 880, 560 + 420)).resize((1200, 580), Image.Resampling.NEAREST).save(OUT / "ref_roof_composite.png")
comp.crop((300 + 360, 560 + 380, 300 + 780, 560 + 560)).resize((1260, 540), Image.Resampling.NEAREST).save(OUT / "ref_hull_side_composite.png")
comp1.crop((300 + 250, 560 + 130, 300 + 760, 560 + 470)).resize((1020, 680), Image.Resampling.NEAREST).save(OUT / "ref_interior_composite.png")
comp.crop((300 + 10, 560 + 420, 300 + 360, 560 + 640)).resize((1050, 660), Image.Resampling.NEAREST).save(OUT / "ref_nose_composite.png")
strip([8, 1, 2], "ref_roof_sprites.png")
strip([12, 34, 35, 36], "ref_hull_side_sprites.png")
strip([46, 47, 49, 51], "ref_interior_sprites.png")
strip([37, 38], "ref_deck_sprites.png")
strip([10, 33, 11], "ref_nose_badge_sprites.png")
strip([20, 21, 22, 30, 31], "ref_engine_sprites.png")
strip([24, 42, 44, 45], "ref_cockpit_sprites.png")
strip([52, 53, 61, 54], "ref_legs_ramp_sprites.png")
print("ok")
