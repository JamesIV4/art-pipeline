# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/terrain_rebuild/opus_batch04/opus_lib.py (imported 2026-10-25)
# Changed: ROOT from xcom_kit_paths; WORK_TEX from $XCOM_OPUS_WORK or <game>/art/team/terrain_rebuild/opus_batch04 (Godot texture dirs stay XCOM-relative)
"""Shared Blender helpers for opus_batch04 (copied from opus_batch01, Opus 5.5 terrain).

Runs inside Blender 5.1 (headless). Owned by opus_batch04; never writes outside
this folder except the explicitly versioned runtime/source paths of this batch,
and refuses to overwrite any existing file.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import struct

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
import sys as _sys
_sys.path.insert(0, str(HERE))
from xcom_kit_paths import ROOT, OPUS_WORK  # noqa: E402
PROJECT = ROOT / "xcom-3d-godot/x-com--ufo-defense-3d"
SCAN = ROOT / "art/team/terrain_rebuild/texture_trials/scans"
VARIANT = "opus-v1"
TEX_DIR = PROJECT / "assets/textures/terrain_opus_batch04"
POLAR032_TEX = PROJECT / "assets/textures/terrain_rebuild/flat-floors-v3"
DESERT_GROUND_TEX = PROJECT / "assets/textures/terrain_rebuild/desert-ground-v1"
WORK_TEX = OPUS_WORK / "textures"
SQ2 = math.sqrt(2.0)
LEVEL_M = math.sqrt(6.0)
LOGICAL_LEVEL_M = 3.0
PX_GROUND = 2 * SQ2 / 32.0          # metres of screen per sprite pixel
PX_HEIGHT = LEVEL_M / 24.0           # metres of height per sprite pixel row
POS_SCALE = 0.15                     # position bake encoding: enc = P*0.15 + 0.5


# ----------------------------------------------------------------- coordinates
def pq_to_xy(p, q):
    """P = screen-right ground axis (NE), Q = toward source viewer (SE)."""
    return ((p + q) / SQ2, (p - q) / SQ2)


def xy_to_pq(x, y):
    return ((x + y) / SQ2, (x - y) / SQ2)


def sprite_point(sx, sy, q=0.0, z=None):
    """World point for sprite pixel (sx, sy) at depth q (Q axis); returns (x, y, z)."""
    p = (sx - 16.0) / 11.3137085
    if z is None:
        z = (32.0 + 5.65685425 * q - sy) / 9.79795897
    x, y = pq_to_xy(p, q)
    return Vector((x, y, z))


def project_to_sprite(co):
    p, q = xy_to_pq(co[0], co[1])
    return (16.0 + 11.3137085 * p, 32.0 + 5.65685425 * q - 9.79795897 * co[2])


# ----------------------------------------------------------------- scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    return scene


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def activate(obj):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def bm_to_object(name, bm, materials=()):
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    obj = link(bpy.data.objects.new(name, mesh))
    for m in materials:
        mesh.materials.append(m)
    return obj


def placeholder_material(name, rgb=(0.6, 0.6, 0.6)):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    return mat


# ----------------------------------------------------------------- geometry
def transport_frames(points):
    n = len(points)
    T = []
    for i in range(n):
        a = points[max(i - 1, 0)]
        b = points[min(i + 1, n - 1)]
        T.append((b - a).normalized())
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - T[0] * up.dot(T[0])).normalized()
    Ns = [N]
    for i in range(1, n):
        axis = T[i - 1].cross(T[i])
        if axis.length > 1e-9:
            angle = T[i - 1].angle(T[i])
            N = Matrix.Rotation(angle, 3, axis.normalized()) @ N
        N = (N - T[i] * N.dot(T[i])).normalized()
        Ns.append(N)
    Bs = [t.cross(nn) for t, nn in zip(T, Ns)]
    return T, Ns, Bs


def add_tube(bm, uv, points, radii, sides, start_cap="flat", end_cap="point", end_len=0.0,
             ref_radius=None, radius_fn=None, v_offset=0.0, mat_index=0, u_start=0.0):
    """Append a closed tube to bmesh.  PhotoUV: U around (metres), V along (metres).

    radius_fn(i, angle, point) -> multiplier for natural irregularity.
    Returns list of rings (lists of BMVerts).
    """
    T, N, B = transport_frames(points)
    ref = ref_radius or max(radii)
    rings = []
    for i, (pt, r) in enumerate(zip(points, radii)):
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            m = radius_fn(i, a, pt) if radius_fn else 1.0
            co = pt + (N[i] * math.cos(a) + B[i] * math.sin(a)) * (r * m)
            ring.append(bm.verts.new(co))
        rings.append(ring)
    # along-length coordinate
    along = [u_start]
    for i in range(1, len(points)):
        along.append(along[-1] + (points[i] - points[i - 1]).length)
    circ = 2 * math.pi * ref
    faces = []
    for i in range(len(points) - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            f.material_index = mat_index
            u0 = circ * k / sides + v_offset
            u1 = circ * (k + 1) / sides + v_offset
            coords = ((u0, along[i]), (u1, along[i]), (u1, along[i + 1]), (u0, along[i + 1]))
            for loop, c in zip(f.loops, coords):
                loop[uv].uv = c
            faces.append(f)

    def cap(ring, center_co, outward_sign, along_value):
        c = bm.verts.new(center_co)
        for k in range(sides):
            k2 = (k + 1) % sides
            if outward_sign < 0:
                f = bm.faces.new((c, ring[k2], ring[k]))
            else:
                f = bm.faces.new((c, ring[k], ring[k2]))
            f.material_index = mat_index
            for loop in f.loops:
                d = loop.vert.co - center_co
                loop[uv].uv = (d.dot(N[0 if outward_sign < 0 else -1]) + v_offset,
                               d.dot(B[0 if outward_sign < 0 else -1]) + along_value)
        return c

    if start_cap:
        cap(rings[0], points[0] - T[0] * (0.0 if start_cap == "flat" else radii[0] * 0.6), -1, along[0])
    if end_cap:
        cap(rings[-1], points[-1] + T[-1] * end_len, +1, along[-1])
    return rings


def catmull(points, samples_per_seg=4):
    """Smooth polyline through control points (centripetal-ish Catmull-Rom)."""
    pts = [Vector(p) for p in points]
    if len(pts) < 3:
        return pts
    out = []
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(samples_per_seg):
            t = s / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def signed_volume(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    v = bm.calc_volume(signed=True)
    bm.free()
    return v


def check_closed(obj, label=""):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bad = [e for e in bm.edges if not e.is_manifold]
    cont = [e for e in bm.edges if not e.is_contiguous]
    vol = bm.calc_volume(signed=True)
    comps = 0
    seen = set()
    for f in bm.faces:
        if f.index in seen:
            continue
        comps += 1
        stack = [f]
        seen.add(f.index)
        while stack:
            g = stack.pop()
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
    bm.free()
    return {"label": label, "non_manifold_edges": len(bad), "non_contiguous_edges": len(cont),
            "signed_volume_m3": vol, "components": comps,
            "closed_outward": len(bad) == 0 and len(cont) == 0 and vol > 0}


def orient_outward(obj):
    """Recalc normals; if the closed consistent volume ends negative, flip all faces."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def boolean_union(target, others, solver="MANIFOLD"):
    for other in others:
        activate(target)
        mod = target.modifiers.new("union", "BOOLEAN")
        mod.operation = "UNION"
        mod.solver = solver
        mod.object = other
        try:
            mod.material_mode = "TRANSFER"
        except (AttributeError, TypeError):
            pass
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(other, do_unlink=True)
    return target


def mark_sharp_by_angle(obj, degrees):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    lim = math.radians(degrees)
    for e in bm.edges:
        e.smooth = not (e.is_manifold and e.calc_face_angle(0.0) > lim)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def triangulate(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def dissolve_slivers(obj, dist=1e-4):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    before = len(bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=list(bm.edges))
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=dist * 0.5)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    after = len(bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return before, after


def tri_count(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


# ----------------------------------------------------------------- UVs
def metric_scale_uv(obj, layer_name):
    """Scale a UV layer so 1 UV unit = 1 metre (area-weighted)."""
    me = obj.data
    me.calc_loop_triangles()
    uv = me.uv_layers[layer_name]
    a3 = a2 = 0.0
    for tri in me.loop_triangles:
        p = [me.vertices[v].co for v in tri.vertices]
        u = [uv.data[i].uv for i in tri.loops]
        a3 += ((p[1] - p[0]).cross(p[2] - p[0])).length * 0.5
        a2 += abs((u[1].x - u[0].x) * (u[2].y - u[0].y) - (u[1].y - u[0].y) * (u[2].x - u[0].x)) * 0.5
    s = math.sqrt(a3 / max(a2, 1e-12))
    arr = np.zeros(len(uv.data) * 2, np.float32)
    uv.data.foreach_get("uv", arr)
    uv.data.foreach_set("uv", arr * s)
    return s


def smart_uv(obj, layer_name, angle=62.0, margin=0.006, pack=True):
    me = obj.data
    if layer_name not in me.uv_layers:
        me.uv_layers.new(name=layer_name)
    me.uv_layers.active = me.uv_layers[layer_name]
    activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.7,
                             correct_aspect=True, scale_to_bounds=False)
    if pack:
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def atlas_from_layer(obj, src_name, dst_name="UVMap", margin=0.008):
    """Copy an existing (photo/metric) unwrap and pack it into 0..1 as the atlas."""
    me = obj.data
    src = me.uv_layers[src_name]
    dst = me.uv_layers.new(name=dst_name)
    arr = np.zeros(len(src.data) * 2, np.float32)
    src.data.foreach_get("uv", arr)
    dst.data.foreach_set("uv", arr)
    me.uv_layers.active = dst
    activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    # photo UV is already metric: keep relative island scale (hidden faces were shrunk on purpose)
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
    return dst


def repair_degenerate_uv(obj, layer_name, eps=1e-10):
    """Give collapsed-UV triangles their own planar metric chart (dominant normal axis)."""
    me = obj.data
    uv = me.uv_layers[layer_name]
    fixed = 0
    for poly in me.polygons:
        li = list(poly.loop_indices)
        if len(li) != 3:
            continue
        a, b, c = [uv.data[i].uv.copy() for i in li]
        area = abs((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)) * 0.5
        if area > eps:
            continue
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        u_ax, v_ax = ((1, 2), (0, 2), (0, 1))[ax]
        for i in li:
            co = me.vertices[me.loops[i].vertex_index].co
            uv.data[i].uv = (co[u_ax] + 40.0 + fixed * 0.0, co[v_ax] + 40.0)
        fixed += 1
    return fixed


def uv_density(obj, layer_name, size):
    me = obj.data
    me.calc_loop_triangles()
    uv = me.uv_layers[layer_name]
    dens = []
    bad = 0
    for tri in me.loop_triangles:
        p = [me.vertices[v].co for v in tri.vertices]
        u = [uv.data[i].uv for i in tri.loops]
        a3 = ((p[1] - p[0]).cross(p[2] - p[0])).length * 0.5
        a2 = abs((u[1].x - u[0].x) * (u[2].y - u[0].y) - (u[1].y - u[0].y) * (u[2].x - u[0].x)) * 0.5
        if a2 < 1e-12 or a3 < 1e-12:
            bad += 1
            continue
        dens.append(size * math.sqrt(a2 / a3))
    return {"texels_per_m_min_median_max": [float(np.min(dens)), float(np.median(dens)), float(np.max(dens))],
            "degenerate_uv_or_geometry_triangles": bad}


# ----------------------------------------------------------------- scans
def scan_record(candidate, resolution="2k"):
    entries = json.loads((SCAN / "provenance.json").read_text(encoding="utf-8"))
    return next(r for r in entries if r["id"] == candidate and r["resolution"] == resolution)


def scan_images(candidate, resolution="2k"):
    rec = scan_record(candidate, resolution)
    out = {"width_m": rec["physical_dimensions"][0] / 1000.0, "source": rec["source"], "license": rec.get("license", "CC0"),
           "files": {}}
    for role, colorspace in (("Diffuse", "sRGB"), ("nor_gl", "Non-Color"), ("arm", "Non-Color")):
        path = SCAN / candidate / rec["maps"][role]["file"]
        img = bpy.data.images.load(str(path), check_existing=True)
        img.colorspace_settings.name = colorspace
        out[role] = img
        out["files"][role] = {"path": path.relative_to(ROOT).as_posix(), "md5_recorded": rec["maps"][role].get("md5")}
    return out


def shared_floor_maps(kind):
    """The exact runtime maps of an approved family floor, as a scan-like dict.

    kind 'polar032_snow': POLAR032 flat-floors-v3 (snow_02 calibrated-v2 albedo, nor_gl, arm),
    2 m physical width, normal strength 0.3 (its glTF normalTexture.scale).
    kind 'desert_sand': desert-ground-v1 (sand_02 calibrated-v2 albedo, nor_gl, arm), 2 m width,
    normal strength 0.45.
    """
    if kind == "polar032_snow":
        folder, files, strength, url = POLAR032_TEX, {
            "Diffuse": "terrain_snow_snow_02_2k_calibrated-v2_albedo.png", "nor_gl": "snow_02_nor_gl_2k.png",
            "arm": "snow_02_arm_2k.png"}, 0.3, "https://polyhaven.com/a/snow_02"
    else:
        folder, files, strength, url = DESERT_GROUND_TEX, {
            "Diffuse": "terrain_desert_sand_02_2k_calibrated-v2_albedo.png", "nor_gl": "sand_02_nor_gl_2k.png",
            "arm": "sand_02_arm_2k.png"}, 0.45, "https://polyhaven.com/a/sand_02"
    out = {"width_m": 2.0, "source": url, "license": "CC0", "files": {}, "floor_normal_strength": strength}
    for role, name in files.items():
        path = folder / name
        img = bpy.data.images.load(str(path), check_existing=True)
        img.colorspace_settings.name = "sRGB" if role == "Diffuse" else "Non-Color"
        out[role] = img
        out["files"][role] = {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
    return out


# ----------------------------------------------------------------- baking
def _img(name, size, float_buffer=True):
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, width=size, height=size, alpha=False, float_buffer=float_buffer)
    img.colorspace_settings.name = "Non-Color"
    return img


def _bake_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return mat, nt, out


def _image_to_array(img):
    w, h = img.size
    arr = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape(h, w, 4)[..., :3].copy()


def setup_cycles(samples=1):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.bake.margin = 16
    scene.render.bake.margin_type = "EXTEND"
    scene.render.bake.use_clear = True
    scene.render.bake.normal_space = "TANGENT"
    scene.render.bake.normal_r = "POS_X"
    scene.render.bake.normal_g = "POS_Y"
    scene.render.bake.normal_b = "POS_Z"


def bake_pass(obj, size, kind, build_shader, name):
    """Bake one pass into the atlas.  build_shader(nt, out_node, slot_index) wires the
    material for each slot (EMIT passes connect Emission; NORMAL connects a BSDF)."""
    me = obj.data
    original = [s.material for s in obj.material_slots]
    img = _img(name, size)
    temp = []
    for i in range(max(1, len(obj.material_slots))):
        mat, nt, out = _bake_material(f"bake_{name}_{i}")
        build_shader(nt, out, i)
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.nodes.active = node
        temp.append(mat)
    if not obj.material_slots:
        me.materials.append(temp[0])
    else:
        for slot, mat in zip(obj.material_slots, temp):
            slot.material = mat
    activate(obj)
    bpy.ops.object.bake(type=kind, margin=16, use_clear=True, uv_layer="UVMap")
    arr = _image_to_array(img)
    for slot, mat in zip(obj.material_slots, original):
        slot.material = mat
    for mat in temp:
        bpy.data.materials.remove(mat)
    bpy.data.images.remove(img)
    return arr


def emit_geometry(kind):
    """Shader builder: emission of encoded object-space position or normal."""
    def build(nt, out, slot):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        em = nt.nodes.new("ShaderNodeEmission")
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "MULTIPLY_ADD"
        if kind == "position":
            nt.links.new(geo.outputs["Position"], vm.inputs[0])
            vm.inputs[1].default_value = (POS_SCALE, POS_SCALE, POS_SCALE)
            vm.inputs[2].default_value = (0.5, 0.5, 0.5)
        else:
            nt.links.new(geo.outputs["Normal"], vm.inputs[0])
            vm.inputs[1].default_value = (0.5, 0.5, 0.5)
            vm.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(vm.outputs[0], em.inputs["Color"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return build


def emit_slot_value(values):
    def build(nt, out, slot):
        em = nt.nodes.new("ShaderNodeEmission")
        v = values[slot] if slot < len(values) else 0.0
        em.inputs["Color"].default_value = (v, v, v, 1)
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return build


def emit_uv(layer):
    def build(nt, out, slot):
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = layer
        em = nt.nodes.new("ShaderNodeEmission")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(uvn.outputs["UV"], sep.inputs[0])
        # encode metric photo UV (wrap-safe): fractional parts handled in numpy
        nt.links.new(sep.outputs[0], comb.inputs[0])
        nt.links.new(sep.outputs[1], comb.inputs[1])
        nt.links.new(comb.outputs[0], em.inputs["Color"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return build


def emit_scan(scan, role, layer="PhotoUV", scale_mult=1.0):
    """Emission of a scan map sampled through the metric photo UV."""
    def build(nt, out, slot):
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = layer
        sc = nt.nodes.new("ShaderNodeVectorMath")
        sc.operation = "SCALE"
        sc.inputs[3].default_value = 1.0 / (scan["width_m"] * scale_mult)
        nt.links.new(uvn.outputs["UV"], sc.inputs[0])
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = scan[role]
        tex.interpolation = "Cubic"
        nt.links.new(sc.outputs[0], tex.inputs["Vector"])
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return build


def normal_scan(scan, strength, layer="PhotoUV", scale_mult=1.0):
    """Principled surface whose normal comes from the scan normal map through PhotoUV;
    baked to the atlas tangent frame by a TANGENT normal bake."""
    def build(nt, out, slot):
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = layer
        sc = nt.nodes.new("ShaderNodeVectorMath")
        sc.operation = "SCALE"
        sc.inputs[3].default_value = 1.0 / (scan["width_m"] * scale_mult)
        nt.links.new(uvn.outputs["UV"], sc.inputs[0])
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = scan["nor_gl"]
        tex.interpolation = "Cubic"
        nt.links.new(sc.outputs[0], tex.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.uv_map = layer
        nm.inputs["Strength"].default_value = strength
        nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return build


def flat_normal():
    def build(nt, out, slot):
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return build


def coverage_mask(obj, size):
    arr = bake_pass(obj, size, "EMIT", emit_slot_value([1.0] * 8), "coverage")
    return arr[..., 0] > 0.5


# ----------------------------------------------------------------- numpy material helpers
def srgb_to_linear(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _hash3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float32) / float(0xFFFFFF)


def value_noise(P, freq, seed=0):
    p = P * freq
    i0 = np.floor(p).astype(np.int64)
    f = (p - i0).astype(np.float32)
    w = f * f * (3 - 2 * f)
    res = np.zeros(len(P), np.float32)
    for dx in (0, 1):
        wx = w[:, 0] if dx else 1 - w[:, 0]
        for dy in (0, 1):
            wy = w[:, 1] if dy else 1 - w[:, 1]
            for dz in (0, 1):
                wz = w[:, 2] if dz else 1 - w[:, 2]
                res += wx * wy * wz * _hash3(i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz, seed)
    return res * 2 - 1


def fbm(P, freq, octaves=4, seed=0, gain=0.5):
    total = np.zeros(len(P), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        total += amp * value_noise(P, freq * (2.03 ** o), seed + 17 * o)
        norm += amp
        amp *= gain
    return total / norm


def write_png(path, rgb, srgb_encode=False):
    """rgb: HxWx3 float (linear if srgb_encode).  Writes 8-bit PNG via Blender image."""
    path = Path(path)
    assert not path.exists(), f"refusing to overwrite {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w, _ = rgb.shape
    data = linear_to_srgb(rgb) if srgb_encode else np.clip(rgb, 0, 1)
    rgba = np.concatenate([data, np.ones((h, w, 1), np.float32)], axis=2).astype(np.float32)
    img = bpy.data.images.new(path.stem, width=w, height=h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "sRGB" if srgb_encode else "Non-Color"
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def encode_normals(nvec):
    n = nvec / np.maximum(np.linalg.norm(nvec, axis=-1, keepdims=True), 1e-6)
    return n * 0.5 + 0.5


def decode_normals(enc):
    n = enc * 2 - 1
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)


# ----------------------------------------------------------------- final material
def final_material(name, paths, extras):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    for k, v in extras.items():
        mat[k] = v
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    imgs = {}
    for role, p in paths.items():
        img = bpy.data.images.load(str(p), check_existing=False)
        img.colorspace_settings.name = "sRGB" if role == "albedo" else "Non-Color"
        img.name = Path(p).stem
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        imgs[role] = node
    nt.links.new(imgs["albedo"].outputs["Color"], bsdf.inputs["Base Color"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    nm.inputs["Strength"].default_value = 1.0
    nt.links.new(imgs["normal"].outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(imgs["orm"].outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    group = bpy.data.node_groups.get("glTF Material Output")
    if not group:
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    hook = nt.nodes.new("ShaderNodeGroup")
    hook.node_tree = group
    nt.links.new(sep.outputs["Red"], hook.inputs["Occlusion"])
    return mat


def clay_material(name="clay"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "preview"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    return mat


# ----------------------------------------------------------------- rendering
def setup_review_scene(sun=True):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    world = bpy.data.worlds.new("opus review sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.36, 0.41, 0.47, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    scene.world = world
    lights = []
    for label, location, energy, size in (("Key", (-4, 3, 9), 1100, 6), ("Fill", (6, -5, 5), 420, 6), ("Rim", (5, 7, 7), 520, 6)):
        data = bpy.data.lights.new("opus_" + label, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = link(bpy.data.objects.new("opus_" + label, data))
        light.location = location
        light.rotation_euler = (Vector((0, 0, 0.6)) - light.location).to_track_quat("-Z", "Y").to_euler()
        light["review_only"] = True
        lights.append(light)
    cam_data = bpy.data.cameras.new("opus review camera")
    cam_data.type = "ORTHO"
    cam = link(bpy.data.objects.new("opus review camera", cam_data))
    cam["review_only"] = True
    scene.camera = cam
    return cam


def review_stage(z=-0.004, size=6.0, rgb=(0.23, 0.25, 0.27)):
    mat = placeholder_material("opus neutral review stage", rgb)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    bm = bmesh.new()
    vs = [bm.verts.new((x * size, y * size, z)) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(vs)
    obj = bm_to_object("opus review stage", bm, [mat])
    bm.free()
    obj["review_only"] = True
    return obj


def place_camera(cam, azimuth_deg, target, ortho_scale, distance=30.0, elevation_deg=30.0):
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
    cam.location = Vector(target) + d * distance
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = ortho_scale
    cam.data.clip_end = 200


def render_source_camera(path, px=10):
    """Exact original projection: 32x40 sprite at px pixels per sprite pixel, SE camera."""
    scene = bpy.context.scene
    cam = scene.camera
    scene.render.resolution_x = 32 * px
    scene.render.resolution_y = 40 * px
    scene.render.resolution_percentage = 100
    place_camera(cam, -45.0, (0, 0, LEVEL_M / 2), 40 * PX_GROUND)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_four(folder, center, span, size=512, prefix="view"):
    scene = bpy.context.scene
    cam = scene.camera
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    out = []
    for i, az in enumerate((-45, 45, 135, 225)):
        place_camera(cam, az, center, span * 1.55)
        p = Path(folder) / f"{prefix}_{i + 1:02d}.png"
        scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        out.append(p)
    return out


def bounds(obj):
    cs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs)))
    hi = Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))
    return lo, hi


# ----------------------------------------------------------------- export + seal
def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export_gltf(obj, gltf_path):
    gltf_path = Path(gltf_path)
    assert not gltf_path.exists(), f"refusing to overwrite {gltf_path}"
    assert not gltf_path.with_suffix(".bin").exists(), "refusing to overwrite bin"
    gltf_path.parent.mkdir(parents=True, exist_ok=True)
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    for o in bpy.context.scene.objects:
        o.select_set(o == obj)
    bpy.context.view_layer.objects.active = obj
    rel = os.path.relpath(TEX_DIR, gltf_path.parent)
    bpy.ops.export_scene.gltf(filepath=str(gltf_path), export_format="GLTF_SEPARATE", use_selection=True,
                              export_texture_dir=rel, export_apply=False, export_texcoords=True,
                              export_normals=True, export_tangents=True, export_extras=True,
                              export_animations=False, export_cameras=False, export_lights=False,
                              export_vertex_color="NONE", export_image_format="AUTO")
    return gltf_path


TYPES = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _accessor(doc, buffers, index):
    acc = doc["accessors"][index]
    view = doc["bufferViews"][acc["bufferView"]]
    fmt = "<" + TYPES[acc["componentType"]] * WIDTHS[acc["type"]]
    stride = view.get("byteStride", struct.calcsize(fmt))
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    return view, stride, start, fmt, acc


def orthonormalize_tangents(gltf_path):
    from urllib.parse import unquote
    doc = json.loads(Path(gltf_path).read_text(encoding="utf-8"))
    buffers = [bytearray((Path(gltf_path).parent / unquote(b["uri"])).read_bytes()) for b in doc["buffers"]]
    count = 0
    repaired = []
    for mesh in doc["meshes"]:
        for prim in mesh["primitives"]:
            na = prim["attributes"]["NORMAL"]
            ta = prim["attributes"]["TANGENT"]
            nview, nstride, nstart, nfmt, nacc = _accessor(doc, buffers, na)
            tview, tstride, tstart, tfmt, tacc = _accessor(doc, buffers, ta)
            iview, istride, istart, ifmt, iacc = _accessor(doc, buffers, prim["indices"])
            idx = [struct.unpack_from(ifmt, buffers[iview["buffer"]], istart + k * istride)[0] for k in range(iacc["count"])]
            NN = [struct.unpack_from(nfmt, buffers[nview["buffer"]], nstart + i * nstride) for i in range(nacc["count"])]
            TT = [list(struct.unpack_from(tfmt, buffers[tview["buffer"]], tstart + i * tstride)) for i in range(nacc["count"])]

            def resid(i):
                n, t = NN[i], TT[i]
                d = sum(a * b for a, b in zip(n, t[:3]))
                return math.sqrt(sum((t[k] - d * n[k]) ** 2 for k in range(3)))
            badv = [i for i in range(len(TT)) if resid(i) < 1e-4]
            if badv:
                # exporter returned a zero/parallel tangent although the UV triangle is valid:
                # take the same-triangle MikkTSpace tangents of its corners (never invent one)
                adj = {}
                for f in range(0, len(idx), 3):
                    tri = idx[f:f + 3]
                    for v in tri:
                        adj.setdefault(v, set()).update(tri)
                for v in badv:
                    good = [u for u in adj.get(v, ()) if u != v and resid(u) >= 1e-4]
                    assert good, "degenerate tangent basis with no valid same-triangle corner"
                    acc = [sum(TT[u][k] for u in good) for k in range(3)]
                    ws = [TT[u][3] for u in good]
                    assert all(w == ws[0] for w in ws), "mixed handedness around a repaired corner"
                    TT[v] = acc + [ws[0]]
                    repaired.append(v)
            for i in range(nacc["count"]):
                n = NN[i]
                t = TT[i]
                nl = math.sqrt(sum(c * c for c in n))
                un = [c / nl for c in n]
                d = sum(a * b for a, b in zip(un, t[:3]))
                pr = [t[k] - d * un[k] for k in range(3)]
                ln = math.sqrt(sum(c * c for c in pr))
                assert ln > 1e-8, "degenerate tangent basis"
                struct.pack_into("<4f", buffers[tview["buffer"]], tstart + i * tstride,
                                 *([c / ln for c in pr] + [1.0 if t[3] >= 0 else -1.0]))
                struct.pack_into(nfmt, buffers[nview["buffer"]], nstart + i * nstride, *un)
                count += 1
    for b, data in zip(doc["buffers"], buffers):
        (Path(gltf_path).parent / unquote(b["uri"])).write_bytes(bytes(data))
    return doc, count, repaired


def finalize_gltf(gltf_path, asset_extras):
    """Tangent Gram-Schmidt, identity extras, dependency seal, final hash (in that order)."""
    from urllib.parse import unquote
    gltf_path = Path(gltf_path)
    doc, count, repaired = orthonormalize_tangents(gltf_path)
    extras = doc.setdefault("asset", {}).setdefault("extras", {})
    extras.update(asset_extras)
    extras["tangent_basis_contract"] = {
        "method": "Blender MikkTSpace export, then float32 Gram-Schmidt against exported NORMAL; handedness kept as +/-1",
        "vertices_processed": count,
        "zero_exported_tangents_rebuilt_from_same_triangle_corners": len(repaired)}
    deps = []
    for entry in doc.get("buffers", []) + doc.get("images", []):
        uri = entry["uri"]
        assert not uri.startswith("data:")
        deps.append({"uri": uri, "sha256": sha256(gltf_path.parent / unquote(uri))})
    extras["render_dependency_sha256"] = deps
    gltf_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {"model_sha256": sha256(gltf_path), "sealed_dependencies": deps, "tangent_vertices_processed": count,
            "zero_tangent_corners_rebuilt": repaired,
            "hash_order": "tangent orthonormalisation -> identity extras -> dependency seal -> final glTF hash"}


# ----------------------------------------------------------------- source identity
def mcd_record(set_name, record):
    raw_all = (ROOT / f"reference/TERRAIN/{set_name}.MCD").read_bytes()
    raw = raw_all[record * 62:(record + 1) * 62]
    named = {"UFO_Door30": raw[30], "No_Floor32": raw[32], "Big_Wall33": raw[33], "Gravlift34": raw[34],
             "Door35": raw[35], "Armor42": raw[42], "Die_MCD44": raw[44], "Alt_MCD46": raw[46],
             "T_Level48": struct.unpack_from("b", raw, 48)[0], "P_Level49": raw[49], "Tile_Type53": raw[53],
             "Light_Source58": raw[58], "Target_Type59": raw[59]}
    return {"frames": list(raw[:8]), "lofts": list(raw[8:20]), "named_zero_based_fields": named,
            "raw_record_sha256": hashlib.sha256(raw).hexdigest(),
            "mcd_file": f"reference/TERRAIN/{set_name}.MCD", "mcd_file_sha256": hashlib.sha256(raw_all).hexdigest()}


