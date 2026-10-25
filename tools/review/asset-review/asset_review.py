# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/asset-review/asset_review.py (imported 2026-10-25)
# Changed: REPO = pipeline_paths.GAME_ROOT, GODOT = pipeline_paths.path('godot_project')
"""Asset revision reviewer: a standalone local tool (Python stdlib + a browser).

    python art/tools/asset-review/asset_review.py [--port 8765] [--no-browser]

Every asset in the game catalog (terrain tiles by family, the natural terrain detail models, units,
items) is shown in a small live 3D view under the game's night lighting (global shade 15). Checking an
asset opens a note field; notes are saved to art/asset_revisions/revisions.json, one entry per
asset id with the model file it refers to, so the rework can be found and done from it. A subset can be
exported as a zip (contact sheet PNGs, per-asset previews, the original sprites, the models with their
textures and the notes) for outside contributors.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import http.server
import io
import json
import os
import re
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOL.parents[1]))  # art-pipeline/tools (pipeline_paths)
import pipeline_paths  # noqa: E402
REPO = pipeline_paths.GAME_ROOT
GODOT = pipeline_paths.path("godot_project")
ASSETS = GODOT / "assets"
REFERENCE = REPO / "art" / "reference"
DATA = REPO / "art" / "asset_revisions"
REVISIONS = DATA / "revisions.json"
EXPORTS = DATA / "exports"

CATEGORY_LABELS = {"terrain": "Terrain", "terrain_detail": "Terrain details", "unit": "Units", "item": "Items"}
CATEGORY_ORDER = ["terrain", "terrain_detail", "unit", "item"]
STATUSES = ("open", "in_progress", "done", "wont_fix")
_lock = threading.Lock()


# ---------------------------------------------------------------------------------------------- index

def res_to_path(res: str) -> Path | None:
    if not res or not res.startswith("res://"):
        return None
    return GODOT / res[len("res://"):]


def res_to_url(res: str) -> str:
    return "/res/" + urllib.parse.quote(res[len("res://"):])


def repo_rel(path: Path) -> str:
    path = path.resolve()
    return path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else path.as_posix()


def parse_tres(path: Path) -> dict:
    """The few StandardMaterial3D / natural_shore ShaderMaterial fields the browser view needs."""
    ext, props = {}, {}
    section = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\[ext_resource type="(\w+)" path="([^"]+)" id="([^"]+)"\]', line)
        if m:
            ext[m.group(3)] = m.group(2)
            continue
        if line.startswith("[resource]"):
            section = "resource"
            continue
        if section == "resource":
            m = re.match(r"^([a-z_0-9/]+) = (.+)$", line)
            if m:
                props[m.group(1)] = m.group(2).strip()

    def tex(key):
        v = props.get(key, "")
        m = re.match(r'ExtResource\("([^"]+)"\)', v)
        return res_to_url(ext[m.group(1)]) if m and m.group(1) in ext else None

    def num(key, default):
        try:
            return float(props.get(key, default))
        except ValueError:
            return default

    def color(key):
        m = re.match(r"Color\(([^)]*)\)", props.get(key, ""))
        return [float(x) for x in m.group(1).split(",")] if m else None

    if "shader" in props:
        return {"type": "shore", "shore_mask": tex("shader_parameter/shore_mask"), "snow_albedo": tex("shader_parameter/snow_albedo"),
                "snow_normal": tex("shader_parameter/snow_normal"), "water": [0.049, 0.104, 0.277]}
    return {
        "type": "standard",
        "albedo": tex("albedo_texture"), "albedo_color": color("albedo_color"),
        "metallic": num("metallic", 0.0), "metallic_texture": tex("metallic_texture"),
        "metallic_channel": int(num("metallic_texture_channel", 0)),
        "roughness": num("roughness", 1.0), "roughness_texture": tex("roughness_texture"),
        "roughness_channel": int(num("roughness_texture_channel", 0)),
        "normal": tex("normal_texture") if props.get("normal_enabled") == "true" else None,
        "normal_scale": num("normal_scale", 1.0),
        "ao": tex("ao_texture") if props.get("ao_enabled") == "true" else None,
        "transparency": int(num("transparency", 0)), "alpha_scissor": num("alpha_scissor_threshold", 0.5),
        "double_sided": int(num("cull_mode", 0)) == 2,
    }


def sprites_for(category: str, family: str, asset_id: str) -> list[str]:
    name = asset_id.split("/")[-1]
    if category == "terrain":
        candidates = [REFERENCE / "terrain" / family / f"{name}.png"]
    elif category == "unit":
        candidates = [REFERENCE / "units" / family / f"standing_{i:02d}.png" for i in (3, 2, 4, 1, 5, 0, 6, 7)]
    elif category == "item":
        candidates = [REFERENCE / "items" / f"{name}.png", REFERENCE / "items" / f"{name}_floor.png"]
    else:
        candidates = []
    return ["/ref/" + urllib.parse.quote(p.relative_to(REFERENCE).as_posix()) for p in candidates if p.exists()]


def build_index() -> dict:
    catalog = json.loads((ASSETS / "catalog.json").read_text(encoding="utf-8"))
    manifest = json.loads((ASSETS / "shared_natural_terrain" / "manifest.json").read_text(encoding="utf-8"))
    materials, shapes, assets = {}, {}, []

    def material(res):
        if res not in materials:
            p = res_to_path(res)
            materials[res] = parse_tres(p) if p and p.exists() else None
        return res

    for a in catalog["assets"]:
        aid, cat, fam = a["id"], a["category"], a.get("family", "")
        model = a.get("model") or ""
        entry = {
            "id": aid, "category": cat, "family": fam, "status": a.get("status", ""),
            "source_label": a.get("source_label", ""), "part": a.get("part"), "record": a.get("record"),
            "light_source": a.get("light_source", 0), "door": a.get("door", False),
            "triangles": (a.get("metrics") or {}).get("triangles"), "model": model, "kind": "none",
            "sprites": sprites_for(cat, fam, aid),
        }
        if model.startswith("res://"):
            p = res_to_path(model)
            if p and p.exists():
                entry.update(kind="gltf", url=res_to_url(model), model_file=repo_rel(p))
            else:
                entry["missing"] = True
        elif model.startswith("procedural://natural/") and aid in manifest["assets"]:
            n = manifest["assets"][aid]
            shapes[n["shape"]] = manifest["shapes"][n["shape"]]
            entry.update(kind="natural", recipe=n.get("recipe"), natural={
                "shape": n["shape"], "materials": [material(m) for m in n["materials"]],
                "details": [{"url": res_to_url(d["scene"]), "scene": d["scene"], "anchor": d.get("surface_anchor", [0, 0]),
                             "height_offset": d.get("height_offset", 0.0), "rotation": d.get("rotation_degrees", 0.0),
                             "scale": d.get("scale", 1.0)} for d in n.get("details", []) if d.get("enabled", True)],
            }, model_file="xcom-3d-godot/x-com--ufo-defense-3d/scripts/natural_terrain.gd (shape %s)" % n["shape"],
                material_files=[repo_rel(res_to_path(m)) for m in n["materials"]])
        assets.append(entry)

    # The natural terrain detail models (rocks, skulls, plants) are assets of their own, placed by the manifest.
    used_by: dict[str, list[str]] = {}
    for aid, n in manifest["assets"].items():
        for d in n.get("details", []):
            used_by.setdefault(d["scene"], []).append(aid)
    for scene, tiles in sorted(used_by.items()):
        p = res_to_path(scene)
        fam = p.parent.name
        stem = p.name.split(".")[0]
        entry = {"id": f"terrain_details/{fam}/{stem}", "category": "terrain_detail", "family": fam, "status": "",
                 "source_label": "natural terrain detail on " + ", ".join(tiles), "part": "detail", "model": scene,
                 "kind": "none", "sprites": [], "used_by": tiles}
        if p.exists():
            entry.update(kind="gltf", url=res_to_url(scene), model_file=repo_rel(p))
        assets.append(entry)

    # Sidebar folders: terrain and its details by family (the environment), units and items as one folder each.
    for a in assets:
        a["folder"] = a["family"] if a["category"] in ("terrain", "terrain_detail") else "ALL"
    groups = []
    for cat in CATEGORY_ORDER:
        fams = sorted({a["folder"] for a in assets if a["category"] == cat})
        groups.append({"category": cat, "label": CATEGORY_LABELS[cat],
                       "families": [{"family": f, "count": sum(1 for a in assets if a["category"] == cat and a["folder"] == f)} for f in fams]})
    return {"groups": groups, "assets": assets, "materials": materials, "shapes": shapes,
            "voxel_pitch": manifest["voxel_pitch"], "revisions_file": repo_rel(REVISIONS)}


_index_cache: dict = {}


def index() -> dict:
    stamp = ((ASSETS / "catalog.json").stat().st_mtime, (ASSETS / "shared_natural_terrain" / "manifest.json").stat().st_mtime)
    if _index_cache.get("stamp") != stamp:
        _index_cache.update(stamp=stamp, data=build_index())
    return _index_cache["data"]


# ------------------------------------------------------------------------------------------ revisions

ABOUT = ("Asset revision notes written in art/tools/asset-review (one entry per flagged asset id). 'note' is the reviewer's "
         "feedback verbatim; 'model'/'model_file' is the exact file that was reviewed. Work flow: status open -> in_progress "
         "-> done (fill 'resolution' and 'resolved_model') or wont_fix. A reopened entry keeps earlier rounds in 'history'.")


def folder_label(asset: dict) -> str:
    label = CATEGORY_LABELS[asset["category"]]
    return f"{label} / {asset['family']}" if asset["folder"] != "ALL" else label


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_revisions() -> dict:
    if REVISIONS.exists():
        return json.loads(REVISIONS.read_text(encoding="utf-8"))
    return {"schema": 1, "about": ABOUT, "updated": None, "revisions": {}}


def save_revisions(doc: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    doc["about"] = ABOUT
    doc["updated"] = now()
    doc["revisions"] = dict(sorted(doc["revisions"].items()))
    tmp = REVISIONS.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, REVISIONS)


def update_revision(body: dict) -> dict:
    aid = body["id"]
    asset = next((a for a in index()["assets"] if a["id"] == aid), None)
    if asset is None:
        raise ValueError("unknown asset " + aid)
    with _lock:
        doc = load_revisions()
        revs = doc["revisions"]
        if body.get("delete"):
            revs.pop(aid, None)
        else:
            old = revs.get(aid, {})
            status = body.get("status", old.get("status", "open"))
            if status not in STATUSES:
                raise ValueError("bad status " + status)
            entry = dict(old)
            if old.get("status") in ("done", "wont_fix") and status == "open":
                entry.setdefault("history", []).append({k: old.get(k) for k in ("note", "status", "model", "resolution", "resolved", "updated")})
                for k in ("resolution", "resolved", "resolved_model"):
                    entry.pop(k, None)
            entry.update({
                "id": aid, "category": asset["category"], "family": asset["family"],
                "folder": folder_label(asset),
                "part": asset.get("part"), "source_label": asset.get("source_label"), "catalog_status": asset.get("status"),
                "model": asset.get("model"), "model_file": asset.get("model_file"),
                "note": body.get("note", old.get("note", "")), "status": status,
                "view": body.get("view", old.get("view")), "lighting": body.get("lighting", old.get("lighting")),
                "created": old.get("created") or now(), "updated": now(),
            })
            if asset.get("material_files"):
                entry["material_files"] = asset["material_files"]
            if asset.get("sprites"):
                entry["reference_sprites"] = ["art/reference/" + urllib.parse.unquote(u[len("/ref/"):]) for u in asset["sprites"]]
            revs[aid] = entry
        save_revisions(doc)
        return doc


# --------------------------------------------------------------------------------------------- export

def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "export"


def add_gltf(zf: zipfile.ZipFile, gltf_path: Path, dest: str, texture_names: dict) -> list[str]:
    """Copies a .gltf with its buffers and images under dest/, rewriting their uris to stay relative."""
    files = []
    if gltf_path.suffix.lower() == ".glb":
        zf.write(gltf_path, f"{dest}/{gltf_path.name}")
        return [gltf_path.name]
    g = json.loads(gltf_path.read_text(encoding="utf-8"))
    for buf in g.get("buffers", []):
        uri = buf.get("uri")
        if uri and not uri.startswith("data:"):
            src = (gltf_path.parent / urllib.parse.unquote(uri)).resolve()
            if src.exists():
                zf.write(src, f"{dest}/{src.name}")
                buf["uri"] = src.name
                files.append(src.name)
    for img in g.get("images", []):
        uri = img.get("uri")
        if uri and not uri.startswith("data:"):
            src = (gltf_path.parent / urllib.parse.unquote(uri)).resolve()
            name = src.name
            key = (dest, name)
            if key in texture_names and texture_names[key] != src:   # two different files share a name
                name = f"{src.parent.name}_{name}"
            texture_names[(dest, name)] = src
            if src.exists():
                arc = f"{dest}/textures/{name}"
                if arc not in zf.namelist():
                    zf.write(src, arc)
                img["uri"] = "textures/" + name
    zf.writestr(f"{dest}/{gltf_path.name}", json.dumps(g, indent=1))
    files.append(gltf_path.name)
    # sidecars the game reads next to a model (sockets, handling, locomotion, ...)
    stem = gltf_path.name[: -len(gltf_path.suffix)]
    for side in gltf_path.parent.glob(stem + ".*.json"):
        zf.write(side, f"{dest}/{side.name}")
        files.append(side.name)
    return files


def b64(data: str) -> bytes:
    return base64.b64decode(data.split(",", 1)[1] if data.startswith("data:") else data)


def export_zip(body: dict) -> Path:
    idx = {a["id"]: a for a in index()["assets"]}
    revs = load_revisions()["revisions"]
    ids = [i for i in body["ids"] if i in idx]
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    pkg = safe_name(body.get("name") or "asset_revisions") + "_" + stamp
    EXPORTS.mkdir(parents=True, exist_ok=True)
    out = EXPORTS / f"{pkg}.zip"
    items, texture_names = [], {}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, data in enumerate(body.get("sheets", []), 1):
            zf.writestr(f"{pkg}/sheets/sheet_{i:02d}.png", b64(data))
        for aid in ids:
            a, rev = idx[aid], revs.get(aid, {})
            safe = safe_name(aid)
            item = {"id": aid, "folder": folder_label(a), "note": rev.get("note", ""),
                    "status": rev.get("status"), "part": a.get("part"), "source_label": a.get("source_label"),
                    "game_model": a.get("model"), "triangles": a.get("triangles"), "preview": None, "reference": [], "files": []}
            if body.get("previews", {}).get(aid):
                zf.writestr(f"{pkg}/previews/{safe}.png", b64(body["previews"][aid]))
                item["preview"] = f"previews/{safe}.png"
            for url in a.get("sprites", []):
                src = REFERENCE / urllib.parse.unquote(url[len("/ref/"):])
                arc = f"reference/{safe}/{src.name}"
                zf.write(src, f"{pkg}/{arc}")
                item["reference"].append(arc)
            dest = f"{pkg}/models/{safe}"
            if a["kind"] == "gltf":
                item["files"] = [f"models/{safe}/{f}" for f in add_gltf(zf, res_to_path(a["model"]), dest, texture_names)]
            if body.get("glbs", {}).get(aid):
                zf.writestr(f"{dest}/{safe}.glb", b64(body["glbs"][aid]))
                item["files"].append(f"models/{safe}/{safe}.glb")
            items.append(item)
        zf.writestr(f"{pkg}/revisions.json", json.dumps({
            "package": pkg, "exported": now(), "lighting": body.get("lighting", ""),
            "conventions": CONVENTIONS, "assets": items}, indent=2, ensure_ascii=False))
        zf.writestr(f"{pkg}/README.md", readme(pkg, body, items))
    return out


CONVENTIONS = {
    "units": "metres, glTF 2.0, +Y up, +X east, +Z south (-Z north); units face -Z",
    "tile": "a terrain tile is 2 x 2 m (x and z from -1 to 1, origin at the tile centre on the floor); one level is sqrt(6) = 2.449 m high",
    "textures": "deliver 8-bit WebP (albedo, ORM = occlusion/roughness/metal in R/G/B, OpenGL +Y normal)",
    "camera": "the game looks down 30 degrees from the south-east (yaw 45) with an orthographic camera",
}


def readme(pkg: str, body: dict, items: list[dict]) -> str:
    lines = [f"# {pkg}", "", f"Exported {now()} from the OpenXcom Extended 3D asset reviewer. {len(items)} asset(s) need rework.", "",
             "## What is here", "",
             "- `sheets/` - contact sheets: each asset from four sides, its original X-COM sprite and the note",
             "- `previews/` - one image per asset (four views)",
             "- `reference/` - the original X-COM sprites the model has to match",
             "- `models/<asset>/` - the current game model (glTF + buffers + `textures/`; natural ground tiles as one .glb)",
             "- `revisions.json` - the same notes as data", "",
             f"Previews are lit like the game: {body.get('lighting', '')}.", "",
             "## Conventions", ""]
    lines += [f"- {k}: {v}" for k, v in CONVENTIONS.items()]
    lines += ["", "## Assets", ""]
    for it in items:
        lines += [f"### {it['id']}", "", f"- Folder: {it['folder']}" + (f" ({it['part']})" if it.get("part") else ""),
                  f"- Source: {it.get('source_label') or '-'}", f"- Game file: `{it.get('game_model') or '-'}`",
                  f"- Files: " + (", ".join(f"`{f}`" for f in it["files"]) or "none (no model yet)"), "",
                  "> " + (it["note"] or "(no note)").replace("\n", "\n> "), ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------------- server

class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".mjs": "text/javascript",
                      ".gltf": "model/gltf+json", ".glb": "model/gltf-binary", ".bin": "application/octet-stream",
                      ".webp": "image/webp", ".png": "image/png", ".json": "application/json", ".css": "text/css"}

    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ("200", "304"):
            sys.stderr.write("%s\n" % (fmt % args))

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def translate_path(self, path):
        path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        for prefix, root in (("/res/", GODOT), ("/ref/", REFERENCE), ("/exports/", EXPORTS)):
            if path.startswith(prefix):
                target = (root / path[len(prefix):]).resolve()
                return str(target) if target.is_relative_to(root.resolve()) else str(root / "__denied__")
        if path in ("", "/"):
            path = "/index.html"
        target = (TOOL / path.lstrip("/")).resolve()
        return str(target) if target.is_relative_to(TOOL) else str(TOOL / "__denied__")

    def send_json(self, obj, code=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        route = urllib.parse.urlsplit(self.path).path
        if route == "/api/index":
            return self.send_json(index())
        if route == "/api/revisions":
            return self.send_json(load_revisions())
        return super().do_GET()

    def do_POST(self):
        route = urllib.parse.urlsplit(self.path).path
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if route == "/api/revision":
                return self.send_json(update_revision(body))
            if route == "/api/export":
                out = export_zip(body)
                return self.send_json({"path": repo_rel(out), "url": "/exports/" + urllib.parse.quote(out.name), "size": out.stat().st_size})
            if route == "/api/reveal":
                target = (REPO / body["path"]).resolve()
                if target.is_relative_to(DATA.resolve()) and target.exists():
                    if os.name == "nt":
                        subprocess.Popen(["explorer", "/select,", str(target)])
                    else:
                        subprocess.Popen(["xdg-open" if sys.platform != "darwin" else "open", str(target.parent)])
                return self.send_json({"ok": True})
            self.send_json({"error": "no such route"}, 404)
        except Exception as exc:  # report to the page
            self.send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--data", type=Path, help="notes folder (default art/asset_revisions; for trying the tool out)")
    args = ap.parse_args()
    if args.data:
        global DATA, REVISIONS, EXPORTS
        DATA = args.data.resolve()
        REVISIONS, EXPORTS = DATA / "revisions.json", DATA / "exports"
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Asset reviewer: {url}  (notes: {repo_rel(REVISIONS)}; Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
