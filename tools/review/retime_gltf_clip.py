# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/retime_gltf_clip.py (imported 2026-10-25)
# Changed: header only
"""Scale one glTF clip's independent time accessors without changing its poses.

Used for the existing psi exporter, which inherits a run source's 60 fps despite
authoring AttackPsi at 30 fps. Run on staged files before Godot imports them.
python retime_gltf_clip.py model.gltf --clip AttackPsi --factor 2 --apply
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("model", type=Path)
parser.add_argument("--clip", required=True)
parser.add_argument("--factor", type=float, required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
assert args.factor > 0
doc = json.loads(args.model.read_text(encoding="utf-8"))
clip = next(a for a in doc["animations"] if a["name"] == args.clip)
inputs = {s["input"] for s in clip["samplers"]}
others = {s["input"] for a in doc["animations"] if a is not clip for s in a["samplers"]}
assert not inputs & others, "Time accessors are shared with another animation"
assert len(doc["buffers"]) == 1
buffer_path = args.model.parent / doc["buffers"][0]["uri"]
blob = bytearray(buffer_path.read_bytes())
for index in inputs:
    accessor = doc["accessors"][index]
    view = doc["bufferViews"][accessor["bufferView"]]
    assert accessor["componentType"] == 5126 and accessor["type"] == "SCALAR"
    assert view.get("byteStride", 4) == 4
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    for i in range(accessor["count"]):
        value = struct.unpack_from("<f", blob, offset + i * 4)[0]
        struct.pack_into("<f", blob, offset + i * 4, value * args.factor)
    for bound in ("min", "max"):
        if bound in accessor:
            accessor[bound] = [x * args.factor for x in accessor[bound]]
extras = doc["asset"]["extras"]
seal = extras["render_dependency_sha256"]
digest = hashlib.sha256(blob).hexdigest()
if isinstance(seal, dict):
    seal[buffer_path.name] = digest
else:
    next(entry for entry in seal if entry["uri"] == buffer_path.name)["sha256"] = digest
extras["psi_timing_correction"] = "AttackPsi at its authored 30 fps; run clips remain at 60 fps"
if args.apply:
    buffer_path.write_bytes(blob)
    args.model.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
print(args.clip, "duration", max(doc["accessors"][i]["max"][0] for i in inputs), "applied" if args.apply else "preview")
