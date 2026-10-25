# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/avenger_v2/common/blender_build.py (imported 2026-10-25)
# Changed: ROOT now comes from xcom_kit_paths (pipeline_paths.GAME_ROOT); lane data (sources/, notes/, textures/, refs/) is read from WORK = $XCOM_AVENGER_WORK or <game>/art/team/avenger_v2/common; Godot/.blend output folders stay XCOM-relative to ROOT
"""AVENGER v2 record build (Blender 5.1 headless).

blender --background --factory-startup --threads 2 --python blender_build.py -- --records 0,1,2 --out DIR
        [--final --variant opus-v2] [--tex DIR] [--no-render]

Per record: craft.py solids -> meshdata buffers -> Blender object (UVs, custom normals, PBR materials)
-> .blend + GLTF_SEPARATE (gltf_writer) -> renders: the sprite-matched game camera (ortho, az -45, el 30,
8 px per sprite px) and four orbit angles. Trial runs write everything under --out; --final writes the
.blend to art/source/terrain/AVENGER and the glTF to the Godot assets folder (refuses to overwrite).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import master as craft  # noqa: E402  (v2b: the complete-craft master)
import meshdata as MD  # noqa: E402
import gltf_writer  # noqa: E402
from avgeo import H  # noqa: E402

from xcom_kit_paths import ROOT, WORK  # noqa: E402
GAME = ROOT / "xcom-3d-godot/x-com--ufo-defense-3d"
MODELS = GAME / "assets/models/terrain/AVENGER"
PUBTEX = GAME / "assets/textures/avenger_v2"
SRC = ROOT / "art/source/terrain/AVENGER"

# v2b texture sets (root 2026-10-03: darker neutral hull, deeper relief, 4-stripe nose band, canopy glass)
TEXSETS = {"AVENGER_v2_hull": "avg2_hull_b", "AVENGER_v2_hull_dark": "avg2_hull_b", "AVENGER_v2_xpanel": "avg2_xpanel_b",
           "AVENGER_v2_greeble": "avg2_greeble_c", "AVENGER_v2_interior": "avg2_interior", "AVENGER_v2_deck": "avg2_deck",
           "AVENGER_v2_trim": "avg2_trim_b", "AVENGER_v2_ramp": "avg2_deck",
           "AVENGER_v2_gear": "avg2_hull_b"}
BASE_FACTOR = {"AVENGER_v2_hull_dark": (0.74, 0.76, 0.78), "AVENGER_v2_ramp": (0.70, 0.56, 0.52),
               "AVENGER_v2_gear": (0.90, 0.72, 1.0)}


def mat_defs(texdir):
    d = {}
    for m, s in TEXSETS.items():
        e = {"albedo": str(texdir / f"{s}_albedo.png"), "normal": str(texdir / f"{s}_normal.png"),
             "orm": str(texdir / f"{s}_orm.png"), "metallic": 1.0, "roughness": 1.0,
             "extras": {"avenger_v2_texture_set": s}}
        if m in BASE_FACTOR:
            e["base_factor"] = BASE_FACTOR[m]
            e["extras"]["tint_of"] = s
        if m == "AVENGER_v2_trim":
            e["emissive"] = str(texdir / f"{s}_emissive.png")
            e["emissive_factor"] = (1.0, 1.0, 1.0)
        d[m] = e
    return d


def _img(path, noncolor):
    p = Path(path)
    if not p.exists() and p.with_suffix(".webp").exists():
        p = p.with_suffix(".webp")
    for im in bpy.data.images:
        if Path(bpy.path.abspath(im.filepath)) == p:
            return im
    im = bpy.data.images.load(str(p))
    if noncolor:
        im.colorspace_settings.name = "Non-Color"
    return im


def blender_material(name, d):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = lambda p, nc: (lambda n: (setattr(n, "image", _img(p, nc)), n)[1])(nt.nodes.new("ShaderNodeTexImage"))
    a = tex(d["albedo"], False)
    if d.get("base_factor"):
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["B"].default_value = tuple(d["base_factor"]) + (1.0,)
        nt.links.new(a.outputs["Color"], mix.inputs["A"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        nt.links.new(a.outputs["Color"], bsdf.inputs["Base Color"])
    o = tex(d["orm"], True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(o.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    n = tex(d["normal"], True)
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if d.get("emissive"):
        e = tex(d["emissive"], False)
        nt.links.new(e.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    return m


def make_object(name, bufs, mats):
    verts, faces, uvs, nrms, mi = [], [], [], [], []
    names = sorted(b for b in bufs if bufs[b]["idx"])
    for k, mname in enumerate(names):
        b = bufs[mname]
        base = len(verts)
        verts.extend(b["pos"])
        for (i, j, l) in b["idx"]:
            faces.append((base + i, base + j, base + l))
            uvs.extend([b["uv"][i], b["uv"][j], b["uv"][l]])
            nrms.extend([b["nrm"][i], b["nrm"][j], b["nrm"][l]])
            mi.append(k)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for k, mname in enumerate(names):
        me.materials.append(blender_material(mname, mats[mname]))
    me.polygons.foreach_set("material_index", mi)
    uvl = me.uv_layers.new(name="UVMap")
    flat = [c for uv in uvs for c in uv]
    uvl.data.foreach_set("uv", flat)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    me.normals_split_custom_set(nrms)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def setup_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    try:
        sc.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.43, 0.46, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.2; sun.angle = math.radians(3)
    sun.color = (1.0, 0.94, 0.83)
    so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    # the game viewer's sun (perf-lab bench.gd: rotation_degrees (-51, -28, 0)) comes from the south-west, 51 deg up
    az, el = math.radians(-118), math.radians(51)
    so.rotation_euler = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))).to_track_quat("Z", "Y").to_euler()
    cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    return sc, co, cam


def shoot(sc, co, cam, path, target, w, h, az=-45, el=30, ortho=None, lens=35, dist=30, up_shift=0.0):
    sc.render.resolution_x, sc.render.resolution_y = w, h
    a, e = math.radians(az), math.radians(el)
    off = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * dist
    rot = (-off).to_track_quat("-Z", "Y")
    up = rot @ Vector((0, 0, 0)) if False else (rot.to_matrix() @ Vector((0, 1, 0)))
    tgt = Vector(target) + up * up_shift
    co.location = tgt + off
    co.rotation_euler = rot.to_euler()
    if ortho:
        cam.type = "ORTHO"; cam.ortho_scale = ortho
    else:
        cam.type = "PERSP"; cam.lens = lens
    cam.clip_start, cam.clip_end = 0.05, 500
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_record(sc, co, cam, ob, outdir, rid, p_level):
    outdir.mkdir(parents=True, exist_ok=True)
    # sprite camera: tile centre at sprite px (16, 32); 32 px = 2*sqrt2 m; 8x
    px = 2 * math.sqrt(2) / 32
    S = 8
    shoot(sc, co, cam, outdir / "game_camera_8x.png", (0, 0, 0), 32 * S, 40 * S, ortho=32 * px,
          dist=30, up_shift=12 * px + 0.0)
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    c = sum(bb, Vector()) / 8
    rad = max((v - c).length for v in bb)
    for k, (az, el) in enumerate(((-45, 30), (-135, 25), (135, 35), (45, 25))):
        shoot(sc, co, cam, outdir / f"view_{k + 1}.png", c, 640, 640, az=az, el=el, lens=50,
              dist=max(rad, 0.8) * 3.3)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--variant", default="opus-v2")
    ap.add_argument("--tex", default=str(WORK / "textures/out"))
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--extras", default="")
    args = ap.parse_args(argv)
    recs = [int(r) for r in args.records.split(",")]
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    texdir = Path(args.tex).resolve()
    mats = mat_defs(texdir)
    extras_all = json.loads(Path(args.extras).read_text(encoding="utf-8")) if args.extras else {}
    report = {}
    for rid in recs:
        sc, co, cam = setup_scene()
        for m in list(bpy.data.materials):
            bpy.data.materials.remove(m)
        tile, solids = craft.record_faces(rid)
        bufs = MD.build(solids, tile, clip=True)
        st = MD.stats(bufs)
        name = f"AVENGER_{rid:03d}_{args.variant}"
        ob = make_object(name, bufs, mats)
        if args.final:
            gl = MODELS / f"{rid:03d}.{args.variant}.gltf"
            bl = SRC / f"{rid:03d}.{args.variant}.blend"
        else:
            gl = out / "models" / f"{rid:03d}.{args.variant}.gltf"
            bl = out / "blend" / f"{rid:03d}.{args.variant}.blend"
        for p in (gl, gl.with_suffix(".bin"), bl):
            if p.exists():
                raise FileExistsError(p)
        gl.parent.mkdir(parents=True, exist_ok=True); bl.parent.mkdir(parents=True, exist_ok=True)
        ex = dict(extras_all.get(str(rid), {}))
        ex.setdefault("asset_id", f"terrain/AVENGER/{rid:03d}")
        res = gltf_writer.write(gl, bufs, mats, ex, name)
        bpy.ops.wm.save_as_mainfile(filepath=str(bl), compress=True)
        if not args.no_render:
            render_record(sc, co, cam, ob, out / "renders" / f"{rid:03d}", rid, craft.RECS[rid]["p_level"])
        report[rid] = {"tile": tile, **st, **res, "blend": str(bl)}
        print("BUILT", rid, st["triangles"], st["materials"], flush=True)
    (out / f"build_report_{'_'.join(str(r) for r in recs[:3])}.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
