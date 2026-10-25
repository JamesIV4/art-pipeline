# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/finalize.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths; root_independent_checks is imported from art-pipeline/tools/review
"""Batch deliverables: gates on the exported glTFs, results.json and root_gate_models.json (UTF-8, no BOM).
python finalize.py <batch_dir> <rec,rec,...>
Gates: root_independent_checks.check (the 'not imported' fail is expected before root's Godot import and is
reported separately), plus seals, +Y normal map naming, ORM non-colour, extras identity fields.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT  # noqa: E402  (also puts art-pipeline/tools/review on sys.path)
from root_independent_checks import check  # noqa: E402

REQ = ("asset_id", "reference_mcd", "reference_pck", "reference_pck_frames", "logical_level_m", "visual_level_pitch_m",
       "source_p_level", "source_assumptions", "render_dependency_sha256")


def _src(tex):
    """image index of a texture, including EXT_texture_webp sources"""
    return tex["source"] if "source" in tex else tex["extensions"]["EXT_texture_webp"]["source"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    bdir = Path(sys.argv[1]).resolve()
    recs = [int(r) for r in sys.argv[2].split(",")]
    v2b = {int(r) for r in sys.argv[3].split(",")} if len(sys.argv) > 3 and sys.argv[3] else set()
    var = lambda r: "opus-v2b" if r in v2b else "opus-v2"
    rep = {}
    for p in sorted((bdir / "final").glob("build_report_*.json")):
        rep.update(json.loads(p.read_text(encoding="utf-8")))
    results, gate = [], []
    for r in recs:
        rel = f"xcom-3d-godot/x-com--ufo-defense-3d/assets/models/terrain/AVENGER/{r:03d}.{var(r)}.gltf"
        g = ROOT / rel
        doc = json.loads(g.read_text(encoding="utf-8"))
        ex = doc["asset"]["extras"]
        c = check(f"terrain/AVENGER/{r:03d}", rel)
        fails = [f for f in c["fails"] if f != "not imported"]
        mine = {
            "extras_fields": all(k in ex for k in REQ),
            "normal_maps_named_normal_gl": all("_normal" in doc["images"][_src(doc["textures"][t["normalTexture"]["index"]])]["uri"]
                                               for t in doc["materials"]),
            "orm_shared_for_occlusion_and_mr": all(t["occlusionTexture"]["index"] == t["pbrMetallicRoughness"]["metallicRoughnessTexture"]["index"]
                                                   for t in doc["materials"]),
            "materials_le_5": len(doc["materials"]) <= 5,
        }
        b = rep.get(str(r), {})
        results.append({
            "id": f"terrain/AVENGER/{r:03d}", "variant": var(r),
            "blend": f"art/source/terrain/AVENGER/{r:03d}.{var(r)}.blend", "gltf": rel, "bin": rel[:-5] + ".bin",
            "sha256": {"gltf": sha(g), "bin": sha(g.with_suffix(".bin")),
                       **{im["uri"].split("/")[-1]: sha(g.parent / im["uri"]) for im in doc["images"]}},
            "triangles": c["info"].get("triangles"), "surfaces": [m["name"] for m in doc["materials"]],
            "bounds_blender_local": b.get("bounds_blender_local"), "canonical_tile": b.get("tile"),
            "gates": {"root_independent_checks_pre_import": "pass" if not fails else "fail: " + "; ".join(fails),
                      "not_imported_yet": "not imported" in c["fails"], **{k: ("pass" if v else "fail") for k, v in mine.items()}},
            "signed_volume_m3": c["info"].get("signed_volume_m3"),
            "sheet": f"art/team/avenger_v2/{bdir.name}/sheets/AVENGER_{r:03d}_sheet.png",
            "role": ex.get("role"), "observed_features": ex.get("observed_features"), "inferences": ex.get("inferences"),
            "unused_in_map": ex.get("unused_in_map", False), "supersedes": (f"{r:03d}.opus-v2.gltf" if r in v2b else None),
            "self_flags": ex.get("self_flags", []),
        })
        gate.append({"id": f"terrain/AVENGER/{r:03d}", "model": rel})
        print(f"{r:03d}", c["info"].get("triangles"), "PASS" if not fails and all(mine.values()) else ("FAIL", fails, mine))
    (bdir / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    (bdir / "root_gate_models.json").write_bytes(json.dumps(gate, indent=1).encode("utf-8"))


if __name__ == "__main__":
    main()
