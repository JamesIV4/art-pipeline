# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/fetch_cc0.py (imported 2026-10-25)
# Changed: ROOT = pipeline_paths.GAME_ROOT (library stays <game>/art/source/cc0_library)
"""Root-only: download CC0 PBR material sets into the shared library.

User approval (in chat, 2026-10-02): standing permission to download CC0 PBR sets from
ambientCG and Poly Haven as needed. Workers do not download; they pick from
art/source/cc0_library/ and request missing sets from root.

  python art/tools/fetch_cc0.py ambientcg Metal032 [--res 2K]
  python art/tools/fetch_cc0.py polyhaven rusty_metal_02 [--res 2k]

Each set lands in art/source/cc0_library/<source>/<id>/ with its maps and a
provenance.json (source URL, licence, date, file hashes). index.json lists all sets.
"""
import argparse
import hashlib
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
ROOT = pipeline_paths.GAME_ROOT
LIB = ROOT / "art" / "source" / "cc0_library"
UA = {"User-Agent": "OpenXcom-3D-art-pipeline/1.0 (CC0 material fetch)"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch_ambientcg(asset, res):
    url = f"https://ambientcg.com/get?file={asset}_{res}-PNG.zip"
    try:
        data = _get(url)
    except Exception:
        url = f"https://ambientcg.com/get?file={asset}_{res}-JPG.zip"
        data = _get(url)
    out = LIB / "ambientcg" / asset
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.lower().endswith((".png", ".jpg", ".jpeg")):
                blob = z.read(name)
                (out / Path(name).name).write_bytes(blob)
                files[Path(name).name] = _sha(blob)
    return out, url, files, "CC0 1.0 (https://docs.ambientcg.com/license/)", f"https://ambientcg.com/view?id={asset}"


def fetch_polyhaven(asset, res):
    meta = json.loads(_get(f"https://api.polyhaven.com/files/{asset}"))
    out = LIB / "polyhaven" / asset
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for map_name, by_res in meta.items():
        if map_name in ("blend", "gltf", "mtlx") or not isinstance(by_res, dict):
            continue
        entry = by_res.get(res) or by_res.get(res.lower())
        if not entry:
            continue
        fmt = entry.get("png") or entry.get("jpg")
        if not fmt or "url" not in fmt:
            continue
        blob = _get(fmt["url"])
        name = Path(fmt["url"]).name
        (out / name).write_bytes(blob)
        files[name] = _sha(blob)
    return out, f"https://api.polyhaven.com/files/{asset}", files, "CC0 1.0 (https://polyhaven.com/license)", f"https://polyhaven.com/a/{asset}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", choices=["ambientcg", "polyhaven"])
    p.add_argument("asset")
    p.add_argument("--res", default=None)
    a = p.parse_args()
    if a.source == "ambientcg":
        out, url, files, lic, page = fetch_ambientcg(a.asset, a.res or "2K")
    else:
        out, url, files, lic, page = fetch_polyhaven(a.asset, a.res or "2k")
    if not files:
        raise SystemExit(f"No maps downloaded for {a.source}/{a.asset}")
    prov = {"source": a.source, "asset": a.asset, "page": page, "download": url, "licence": lic,
            "fetched_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "files_sha256": files,
            "approval": "User in-chat standing approval 2026-10-02 (root-run download)"}
    (out / "provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    index_path = LIB / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index[f"{a.source}/{a.asset}"] = {"path": out.relative_to(ROOT).as_posix(), "page": page, "maps": sorted(files)}
    index_path.write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")
    print(out.relative_to(ROOT).as_posix(), len(files), "maps")


if __name__ == "__main__":
    main()
