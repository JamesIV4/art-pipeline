# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/extras.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common
"""asset.extras per record (host Python): exact MCD zero-based fields (+ xcom1 mcdPatches), PCK frames, levels,
map placements and the worker's observed features / inferences from notes/*.json.
python extras.py <batch_label> <rec,rec,...> <out.json>
"""
import json
import math
import struct
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT, WORK  # noqa: E402


def notes():
    d = {}
    for p in sorted((WORK / "notes").glob("*.json")):
        d.update(json.loads(p.read_text(encoding="utf-8")))
    return d


def main():
    label, recs, out = sys.argv[1], [int(r) for r in sys.argv[2].split(",")], Path(sys.argv[3])
    variant = sys.argv[4] if len(sys.argv) > 4 else "opus-v2"
    raw = (ROOT / "reference/TERRAIN/AVENGER.MCD").read_bytes()
    patches = next((p["data"] for p in yaml.safe_load((ROOT / "bin/standard/xcom1/mcdPatches.rul").read_text(encoding="utf-8"))["MCDPatches"]
                    if p["type"] == "AVENGER"), [])
    pmap = {}
    for pt in patches:
        pmap.setdefault(pt["MCDIndex"], {}).update({k: v for k, v in pt.items() if k != "MCDIndex"})
    import master as craft
    N = notes()
    H = math.sqrt(6)
    res = {}
    for r in recs:
        d = raw[r * 62:(r + 1) * 62]
        frames = list(d[0:8])
        pl = craft.PLACEMENTS.get(r, [])
        tile = craft.canonical(r)
        n = N.get(str(r), {})
        res[str(r)] = {
            "asset_id": f"terrain/AVENGER/{r:03d}", "variant": variant, "geometry_version": f"avenger_v2b master {label}",
            "role": n.get("role", ""),
            "reference_mcd": r, "reference_mcd_file": "reference/TERRAIN/AVENGER.MCD",
            "reference_pck": frames[0], "reference_pck_file": "reference/TERRAIN/AVENGER.PCK", "reference_pck_frames": frames,
            "frame_semantics": "MCD Frame[8] = fixed-camera animation frames (not facings)" + (" ; static (one frame repeated)" if len(set(frames)) == 1 else " ; animated: " + str(sorted(set(frames)))),
            "state_relation": {"Die_MCD@44": d[44], "Alt_MCD@46": d[46], "Door@35": d[35], "UFO_Door@30": d[30]},
            "mcd_zero_based_fields": {"Tile_Type@53": d[53], "T_Level@48": struct.unpack_from("b", d, 48)[0], "P_Level@49": d[49],
                                      "Big_Wall@33_raw": d[33], "Door@35": d[35], "UFO_Door@30": d[30], "Die_MCD@44": d[44],
                                      "Alt_MCD@46": d[46], "Armor@42": d[42], "Light_Source@58": d[58], "TU_Walk@39": d[39],
                                      "Stop_LOF@31": d[31], "LOFT@8": list(d[8:20])},
            "mcd_patch_xcom1": pmap.get(r),
            "logical_level_m": 3.0, "logical_level_voxels": 24, "visual_level_pitch_m": H, "voxel_pitch_m": H / 24, "tile_m": 2.0,
            "source_p_level": d[49], "source_sprite_y_offset": -d[49],
            "coordinates": "glTF Y-up, -Z north, +X east; tile centred on the origin; walking surface of the tile's level at y=0 (Blender Z-up, +Y north before export)",
            "terrain_set": "AVENGER craft (crafts.rul STR_AVENGER: mapDataSets BLANKS, AVENGER; mcdPatches AVENGER)",
            "master_frame": "cut from the complete AVENGER v2b master craft (art/team/avenger_v2/common/master.py + craft.py roof), craft X = 2*map_x, Y = -2*map_y, Z = level*sqrt6",
            "unused_in_map": not pl,
            "canonical_tile_xyz": list(tile),
            "original_map_placements": {"map": "AVENGER", "count": len(pl), "positions": [[*p, part] for p, part in pl]},
            "observed_features": n.get("observed", []), "inferences": n.get("inferences", []),
            "source_assumptions": ["unobserved sides inferred from the craft composite and the UFOpaedia Avenger art (UFOGRAPH UP001)",
                                   "faces cut on tile planes use the sprites' flat lilac section colour; hidden when the craft is assembled"],
            "colour_policy": "albedo close to the sprite colours (2026-10-02 policy); paints metallic 0, steel bolts metallic 1",
            "texture_sources": "image_gen (Codex) textures with provenance in art/team/avenger_v2/common/textures/*.provenance.json; normal/ORM derived",
            "import_note": "cut multi-tile craft piece: import without generated LODs (renderer lane, like XBASE1/UFO1)",
            "godot_review_complete": False, "final_art_approved": False,
        }
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("extras", out, len(res))


if __name__ == "__main__":
    main()
