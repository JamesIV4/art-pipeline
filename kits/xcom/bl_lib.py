# Origin: S:/Repos/OpenXcom-Extended-3D/art/team/natural_details_opus55/tools/bl_lib.py (imported 2026-10-25)
# Changed: PROJECT is now ROOT (xcom_kit_paths) / the XCOM Godot project
"""Blender authoring helpers for natural terrain details (run inside Blender)."""
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from xcom_kit_paths import ROOT  # noqa: E402
PROJECT = ROOT / "xcom-3d-godot/x-com--ufo-defense-3d"


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def ellipsoid(name, centre, radii, rot=(0, 0, 0), segments=32, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = link(bpy.data.objects.new(name, mesh))
    obj.scale = radii
    obj.rotation_euler = rot
    obj.location = centre
    apply(obj)
    return obj


def box(name, centre, size, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = link(bpy.data.objects.new(name, mesh))
    obj.scale = size
    obj.rotation_euler = rot
    obj.location = centre
    apply(obj)
    return obj


def apply(obj):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def catmull(points, samples):
    pts = [Vector(p) for p in points]
    pts = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    segs = len(pts) - 3
    for i in range(samples):
        t = i / (samples - 1) * segs
        k = min(int(t), segs - 1)
        u = t - k
        p0, p1, p2, p3 = pts[k:k + 4]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return out


def tube(name, points, radius_fn, samples=48, sides=16, cap_start=True, cap_end=True, section_fn=None, twist_fn=None,
         up_frame=False, phase=0.0, v_scale=1.0):
    """Sweep a circle along a Catmull-Rom path. radius_fn(t)->r; section_fn(t, angle)->(sx, sy) scale of the
    local cross-section axes (normal, binormal). up_frame: normal = horizontal side, binormal = up-ish
    (no parallel transport). UV: u around (0..1, angle = 2*pi*u + phase), v = arc length / v_scale."""
    path = catmull(points, samples)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings, vs = [], []
    up = Vector((0, 0, 1))
    length = 0.0
    lengths = [0.0]
    for i in range(1, len(path)):
        length += (path[i] - path[i - 1]).length
        lengths.append(length)
    prev_n = None
    for i, p in enumerate(path):
        t = i / (len(path) - 1)
        tan = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        if up_frame:
            n = tan.cross(up).normalized()
        elif prev_n is None:
            ref = up if abs(tan.dot(up)) < 0.9 else Vector((1, 0, 0))
            n = tan.cross(ref).normalized()
        else:
            n = (prev_n - tan * prev_n.dot(tan)).normalized()
        prev_n = n
        b = n.cross(tan).normalized() if up_frame else tan.cross(n).normalized()
        r = radius_fn(t)
        ring = []
        tw = twist_fn(t) if twist_fn else 0.0
        for j in range(sides):
            a = 2 * math.pi * j / sides + tw + phase
            sx, sy = section_fn(t, a) if section_fn else (1.0, 1.0)
            ring.append(bm.verts.new(p + (n * math.cos(a) * sx + b * math.sin(a) * sy) * r))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(sides):
            f = bm.faces.new((rings[i][j], rings[i][(j + 1) % sides], rings[i + 1][(j + 1) % sides], rings[i + 1][j]))
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                loop[uv].uv = (jj / sides, lengths[ii] / v_scale)
    for cap, ring in ((cap_start, rings[0]), (cap_end, rings[-1])):
        if cap:
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            for j in range(sides):
                bm.faces.new((ring[j], ring[(j + 1) % sides], c) if ring is rings[-1] else (ring[(j + 1) % sides], ring[j], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return link(bpy.data.objects.new(name, mesh))


def boolean(target, cutter, op="DIFFERENCE", solver="EXACT", keep=False, min_keep=0.5):
    backup = target.data.copy()
    before = len(target.data.vertices)
    for attempt in (solver, "FLOAT" if solver == "EXACT" else "EXACT"):
        mod = target.modifiers.new("bool", "BOOLEAN")
        mod.operation = op
        mod.solver = attempt
        mod.object = cutter
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=mod.name)
        after = len(target.data.vertices)
        if op != "DIFFERENCE" or after > max(before * min_keep, 8):
            break
        print(f"BOOLEAN WARNING {target.name} {op} {cutter.name} [{attempt}]: {before} -> {after} vertices; retrying")
        old = target.data
        target.data = backup.copy()
        bpy.data.meshes.remove(old)
    bpy.data.meshes.remove(backup)
    if not keep:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def join(objs, name):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    return obj


def remesh(obj, voxel, smooth_iter=0, smooth_factor=0.5):
    mod = obj.modifiers.new("remesh", "REMESH")
    mod.mode = "VOXEL"
    mod.voxel_size = voxel
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if smooth_iter:
        mod = obj.modifiers.new("smooth", "SMOOTH")
        mod.iterations = smooth_iter
        mod.factor = smooth_factor
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def decimate(obj, target_tris):
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tris > target_tris:
        mod = obj.modifiers.new("dec", "DECIMATE")
        mod.ratio = target_tris / tris
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def triangulate(obj):
    mod = obj.modifiers.new("tri", "TRIANGULATE")
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    clean(obj)


def fix_degenerate_uvs(obj, scale=0.05, tol=1e-11):
    """Per triangle: if UV area < tol, set its UVs to the nearest valid-triangle UV plus a planar projection of
    the vertex positions on the triangle's dominant plane (`scale` UV per metre). Returns the count fixed."""
    from mathutils import kdtree
    mesh = obj.data
    uvl = mesh.uv_layers.active.data

    def area(p):
        a, b, c = (uvl[li].uv for li in p.loop_indices)
        return abs((b - a).cross(c - a))
    bad = [p for p in mesh.polygons if len(p.vertices) == 3 and area(p) < tol]
    good = [p for p in mesh.polygons if not (len(p.vertices) == 3 and area(p) < tol)]
    if not bad or not good:
        return 0
    kd = kdtree.KDTree(len(good))
    for i, p in enumerate(good):
        kd.insert(p.center, i)
    kd.balance()
    for p in bad:
        _, i, _ = kd.find(p.center)
        base_uv = uvl[list(good[i].loop_indices)[0]].uv.copy()
        nx, ny, nz = (abs(c) for c in p.normal)
        for li in p.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            proj = (co.x, co.y) if nz >= max(nx, ny) else ((co.y, co.z) if nx >= ny else (co.x, co.z))
            uvl[li].uv = (base_uv[0] + scale * proj[0], base_uv[1] + scale * proj[1])
    return len(bad)


def clean(obj, dist=2e-5):
    """Dissolve degenerate (zero-area) faces/edges and drop loose geometry."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for _ in range(3):
        bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges)
    bad = [f for f in bm.faces if f.calc_area() < 1e-9]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(obj.data)
    bm.free()


def shade_smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def world_uv(obj, metres_per_uv, angle=66):
    """Smart-project, then scale UVs so 1 UV unit spans `metres_per_uv` of surface (tiling maps)."""
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.01, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    rescale_uv(obj, metres_per_uv)


def rescale_uv(obj, metres_per_uv, polys=None):
    mesh = obj.data
    uv = mesh.uv_layers.active.data
    area3, area2 = 0.0, 0.0
    sel = polys if polys is not None else range(len(mesh.polygons))
    for pi in sel:
        p = mesh.polygons[pi]
        area3 += p.area
        li = list(p.loop_indices)
        a = uv[li[0]].uv
        for k in range(1, len(li) - 1):
            b, c = uv[li[k]].uv, uv[li[k + 1]].uv
            area2 += abs((b - a).cross(c - a)) / 2
    s = math.sqrt(area3 / max(area2, 1e-12)) / metres_per_uv
    for pi in sel:
        for li in mesh.polygons[pi].loop_indices:
            uv[li].uv *= s


def material(name, albedo, normal=None, orm=None, normal_scale=1.0, rough=0.85, alpha_clip=None, double=False):
    """Material named exactly `name` (finalize copies source glTF materials by this name)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough

    def img(path, colour=True):
        path = Path(path)
        if not path.exists():  # the root gate converts runtime PNGs to lossless WebP in place
            for ext in (".webp", ".png"):
                if path.with_suffix(ext).exists():
                    path = path.with_suffix(ext)
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(path), check_existing=True)
        if not colour:
            node.image.colorspace_settings.name = "Non-Color"
        return node

    a = img(albedo)
    vc = nt.nodes.new("ShaderNodeVertexColor")
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(a.outputs["Color"], mul.inputs["A"])
    nt.links.new(vc.outputs["Color"], mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
    if alpha_clip is not None:
        cmp = nt.nodes.new("ShaderNodeMath")
        cmp.operation = "GREATER_THAN"
        cmp.inputs[1].default_value = alpha_clip
        nt.links.new(a.outputs["Alpha"], cmp.inputs[0])
        nt.links.new(cmp.outputs[0], bsdf.inputs["Alpha"])
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "DITHERED"
    if normal:
        n = img(normal, False)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal_scale
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if orm:
        o = img(orm, False)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(o.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    mat.use_backface_culling = not double
    return mat


def dirt(obj, clean=0.6, blur=1):
    """COLOR_0 cavity darkening (Blender 'dirty vertex colors'), floor at `clean` so it stays subtle."""
    mesh = obj.data
    if "Color" not in mesh.color_attributes:
        mesh.color_attributes.new("Color", "FLOAT_COLOR", "POINT")
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="VERTEX_PAINT")
    bpy.ops.paint.vertex_color_dirt(blur_strength=1.0, blur_iterations=blur, clean_angle=math.radians(180),
                                    dirt_angle=0.0, dirt_only=False, normalize=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    attr = mesh.color_attributes["Color"]
    for d in attr.data:
        c = d.color
        v = clean + (1 - clean) * c[0]
        d.color = (v, v, v, 1)


def set_colour(obj, fn):
    """Per-vertex COLOR_0 from fn(co) -> (r, g, b) multiplied into existing values."""
    mesh = obj.data
    if "Color" not in mesh.color_attributes:
        attr = mesh.color_attributes.new("Color", "FLOAT_COLOR", "POINT")
        for d in attr.data:
            d.color = (1, 1, 1, 1)
    attr = mesh.color_attributes["Color"]
    mesh.color_attributes.active_color = attr
    for v, d in zip(mesh.vertices, attr.data):
        r, g, b = fn(v.co)
        c = d.color
        d.color = (c[0] * r, c[1] * g, c[2] * b, 1)


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def save_and_export(obj_name, blend, gltf):
    blend, gltf = Path(blend), Path(gltf)
    blend.parent.mkdir(parents=True, exist_ok=True)
    gltf.parent.mkdir(parents=True, exist_ok=True)
    import os
    if blend.exists() and os.environ.get("DETAILS_REPLACE_OWN") != "1":
        raise SystemExit("refusing to overwrite " + str(blend))
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    bpy.ops.export_scene.gltf(filepath=str(gltf), export_format="GLTF_SEPARATE", export_tangents=True,
                              export_normals=True, export_vertex_color="ACTIVE",
                              export_active_vertex_color_when_no_material=True, export_image_format="AUTO",
                              use_selection=False, export_yup=True)


def report(obj, path, extra=None):
    import json
    mesh = obj.data
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    rep = {"name": obj.name, "godot_anchor_of_source": [0.0, 0.0],
           "bounds_blender": [[min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]],
           "triangles": sum(len(p.vertices) - 2 for p in mesh.polygons),
           "materials": [m.name for m in mesh.materials], "color_attributes": [c.name for c in mesh.color_attributes]}
    rep.update(extra or {})
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(rep, indent=1))
    print("AUTHORED", json.dumps(rep))
