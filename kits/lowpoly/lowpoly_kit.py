"""Origin: S:/Repos/trick-or-treat/art/tools/lowpoly_kit.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. Scale-figure height/colour and the glTF build-stamp key are settings.

Shared low-poly kit (v2, textured) for headless Blender asset scripts.

Usage inside a build script (run with Blender 5.1):
    cd <game root>   (or set ART_GAME_ROOT)
    blender --background --factory-startup --python art/team/<lane>/<batch>/build_x.py

    import os, sys
    sys.path.insert(0, os.path.join(os.environ.get("ART_PIPELINE", r"S:/Repos/art-pipeline"), "kits", "lowpoly"))
    import lowpoly_kit as K
    K.reset()
    body = K.sphere("body", 0.4, color="pumpkin", mat="pumpkin", project="cyl", scale=(1, 1, 0.75), loc=(0, 0, 0.3))
    stem = K.cylinder("stem", 0.05, 0.15, color="stem_brown", mat="wood", project="cyl", loc=(0, 0, 0.62))
    pumpkin = K.merge([body, stem], "pumpkin_a")
    K.bake_ao([pumpkin])
    K.export([pumpkin], "props/pumpkin_a")
    K.review_sheet([pumpkin], "pumpkin_a")

Conventions (see docs/asset-conventions.md and techniques/lowpoly-textured-style.md):
  * 1 Blender unit = 1 m, Z up, origin at the ground contact point, front faces Blender -Y
    (glTF/Godot +Z, Godot's MODEL_FRONT).
  * Every face has a palette tint (color=<palette name>) and a painted material
    (mat=<layer name> from the game's materials spec, default "flat"). The material tiles in
    metres via the face's projection UVs ("UVMap"); the tint and layer ride in the second UV map
    ("Tint": u = layer + cell u, v = cell v). Glow cells (glow_*) light up in game.
  * bake_ao() stores per-vertex ambient occlusion in the "AO" colour attribute (exported as COLOR_0).
  * Export is glTF separate (.gltf + .bin), no materials: the game applies the shared toon material.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import pipeline_paths as P  # noqa: E402

ROOT = P.GAME_ROOT
CELLS = json.loads((P.path("palette_out") / "palette_cells.json").read_text())
PALETTE_PNG = P.path("palette_out") / "palette.png"
PALETTE_SPEC = json.loads(P.path("palette_spec").read_text())
MATERIALS = [l["name"] for l in json.loads(P.path("materials_spec").read_text())["layers"]]
MODELS = P.path("models_out")
REVIEW = P.path("review_sheets")
GRID = int(P.setting("palette_grid"))
SCALE_H = float(P.setting("scale_figure_height_m"))
SCALE_COLOR = P.setting("scale_figure_color")


# ---------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _uv_cell(color):
    if color not in CELLS:
        raise KeyError(f"unknown palette colour '{color}'")
    c = CELLS[color]
    # Blender UV origin is bottom-left; PNG row 0 is the top (glTF export flips v back).
    return c["u"], 1.0 - c["v"]


def _layer(mat):
    if mat not in MATERIALS:
        raise KeyError(f"unknown material '{mat}' (see {P.path('materials_spec')})")
    return MATERIALS.index(mat)


def _uv_layers(bm):
    proj = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    tint = bm.loops.layers.uv.get("Tint") or bm.loops.layers.uv.new("Tint")
    return proj, tint


def _paint_bm(bm, color, mat="flat", faces=None):
    _, tint = _uv_layers(bm)
    u, v = _uv_cell(color)
    u += _layer(mat)
    for f in faces if faces is not None else bm.faces:
        for loop in f.loops:
            loop[tint].uv = (u, v)


def _project_bm(bm, mode="box", faces=None, center=None):
    """Material UVs in metres. box: per face along its dominant axis (walls upright);
    cyl: around Z (seam-safe); sphere: around Z with latitude arc length."""
    proj, _ = _uv_layers(bm)
    if center is None:
        center = Vector((0, 0, 0))
        if bm.verts:
            for v in bm.verts:
                center += v.co
            center /= len(bm.verts)
    for f in faces if faces is not None else bm.faces:
        n = f.normal
        if mode == "box":
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in f.loops:
                p = loop.vert.co
                if ax == 2:
                    loop[proj].uv = (p.x, p.y)
                elif ax == 0:
                    loop[proj].uv = (p.y if n.x > 0 else -p.y, p.z)
                else:
                    loop[proj].uv = (-p.x if n.y > 0 else p.x, p.z)
        else:
            uvs = []
            for loop in f.loops:
                d = loop.vert.co - center
                r = max(math.hypot(d.x, d.y), 1e-4)
                a = math.atan2(d.y, d.x)
                if mode == "cyl":
                    uvs.append([a, d.z])
                else:
                    rr = max(d.length, 1e-4)
                    uvs.append([a, math.asin(max(-1.0, min(1.0, d.z / rr))) * rr])
            # Unwrap faces that straddle the seam.
            angs = [uv[0] for uv in uvs]
            if max(angs) - min(angs) > math.pi:
                for uv in uvs:
                    if uv[0] < 0:
                        uv[0] += 2 * math.pi
            rad = 0.0
            for loop in f.loops:
                d = loop.vert.co - center
                rad += math.hypot(d.x, d.y) if mode == "cyl" else d.length
            rad = max(rad / len(f.loops), 0.02)
            for loop, uv in zip(f.loops, uvs):
                loop[proj].uv = (uv[0] * rad, uv[1])


def _finish(bm, name, color, loc, rot, scale, smooth, bevel=0.0, segments=1, mat="flat", project="box"):
    if bevel > 0.0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segments,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    bm.normal_update()
    _project_bm(bm, project, center=Vector((0, 0, 0)))
    _paint_bm(bm, color, mat)
    for f in bm.faces:
        f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = _link(bpy.data.objects.new(name, me))
    ob.location = Vector(loc)
    ob.rotation_euler = Euler([math.radians(a) for a in rot])
    ob.scale = Vector(scale)
    return ob


# ---------------------------------------------------------------- primitives
def box(name, size=(1, 1, 1), color="wood", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
        bevel=0.0, segments=1, smooth=False, mat="flat", project="box"):
    """Axis box centred on loc. bevel in metres rounds every edge (1-2 segments reads as 'toy')."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    return _finish(bm, name, color, loc, rot, scale, smooth, bevel, segments, mat, project)


def cylinder(name, radius=0.5, depth=1.0, color="wood", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
             verts=10, radius_top=None, bevel=0.0, segments=1, smooth=False, caps=True, mat="flat", project="cyl"):
    """Cylinder/cone along Z centred on loc. radius_top makes a tapered cone."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=verts, radius1=radius,
                          radius2=radius if radius_top is None else radius_top, depth=depth)
    return _finish(bm, name, color, loc, rot, scale, smooth, bevel, segments, mat, project)


def sphere(name, radius=0.5, color="pumpkin", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
           segments=10, rings=6, smooth=True, mat="flat", project="sphere"):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    return _finish(bm, name, color, loc, rot, scale, smooth, mat=mat, project=project)


def ico(name, radius=0.5, color="maple_red", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
        subdiv=2, smooth=False, mat="flat", project="sphere"):
    """Faceted blob. In Blender 5.1 subdiv 1 is the bare icosahedron (20 tris), 2 = 80, 3 = 320.
    Good for canopies, clouds, bushes."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    return _finish(bm, name, color, loc, rot, scale, smooth, mat=mat, project=project)


def torus(name, major=0.5, minor=0.1, color="rope", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
          major_seg=12, minor_seg=6, smooth=True, arc=360.0, mat="flat", project="cyl"):
    """Torus in the XY plane. arc < 360 makes an open ring (handles, arches)."""
    bm = bmesh.new()
    closed = arc >= 359.9
    rings = []
    count = major_seg if closed else major_seg + 1
    for i in range(count):
        a = math.radians(arc) * i / major_seg
        center = Vector((math.cos(a) * major, math.sin(a) * major, 0))
        ring = []
        for j in range(minor_seg):
            b = 2 * math.pi * j / minor_seg
            d = Vector((math.cos(a), math.sin(a), 0)) * math.cos(b) * minor + Vector((0, 0, math.sin(b) * minor))
            ring.append(bm.verts.new(center + d))
        rings.append(ring)
    pairs = len(rings) if closed else len(rings) - 1
    for i in range(pairs):
        r0, r1 = rings[i], rings[(i + 1) % len(rings)]
        for j in range(minor_seg):
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % minor_seg], r0[(j + 1) % minor_seg]))
    if not closed:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(bm, name, color, loc, rot, scale, smooth, mat=mat, project=project)


def tube(name, points, radius=0.05, color="vine", sides=6, smooth=True, radius_end=None, mat="flat", project="box"):
    """Swept tube through a list of points (vines, handles, ropes, tails). Caps both ends."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        side = t.cross(up).normalized()
        up2 = side.cross(t).normalized()
        r = radius if radius_end is None else radius + (radius_end - radius) * i / max(n - 1, 1)
        rings.append([bm.verts.new(p + (side * math.cos(2 * math.pi * j / sides) + up2 * math.sin(2 * math.pi * j / sides)) * r)
                      for j in range(sides)])
    for i in range(n - 1):
        for j in range(sides):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % sides], rings[i][(j + 1) % sides]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(bm, name, color, (0, 0, 0), (0, 0, 0), (1, 1, 1), smooth, mat=mat, project=project)


def polygon_prism(name, outline, height, color="wood", loc=(0, 0, 0), rot=(0, 0, 0), smooth=False, mat="flat", project="box"):
    """Extrudes a 2D outline [(x, y), ...] (counter-clockwise) up by height along Z."""
    bm = bmesh.new()
    bottom = [bm.verts.new((x, y, 0)) for x, y in outline]
    top = [bm.verts.new((x, y, height)) for x, y in outline]
    bm.faces.new(list(reversed(bottom)))
    bm.faces.new(top)
    k = len(outline)
    for i in range(k):
        bm.faces.new((bottom[i], bottom[(i + 1) % k], top[(i + 1) % k], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(bm, name, color, loc, rot, (1, 1, 1), smooth, mat=mat, project=project)


# ---------------------------------------------------------------- shaping helpers
def paint(ob, color, where=None, mat=None):
    """Repaint faces of an object. where(face_center_local: Vector, normal: Vector) -> bool selects
    faces. mat=None keeps each face's current material layer."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    _, tint = _uv_layers(bm)
    faces = [f for f in bm.faces if where is None or where(f.calc_center_median(), f.normal)]
    u, v = _uv_cell(color)
    for f in faces:
        layer = _layer(mat) if mat is not None else (int(f.loops[0][tint].uv[0]) if f.loops else 0)
        for loop in f.loops:
            loop[tint].uv = (u + layer, v)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def project(ob, mode="box", where=None):
    """Recompute material UVs (after deforms or merges). where() as in paint()."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    faces = [f for f in bm.faces if where is None or where(f.calc_center_median(), f.normal)]
    _project_bm(bm, mode, faces)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def deform(ob, fn):
    """fn(Vector local_co) -> Vector. Use for squash, taper, lumps, wobble."""
    for v in ob.data.vertices:
        v.co = fn(v.co.copy())
    ob.data.update()
    return ob


def lean(ob, degrees_x=0.0, degrees_y=0.0):
    ob.rotation_euler.x += math.radians(degrees_x)
    ob.rotation_euler.y += math.radians(degrees_y)
    return ob


def merge(objects, name, smooth=None):
    """Bakes transforms and merges objects into one mesh object at the world origin."""
    bpy.context.view_layer.update()
    bm = bmesh.new()
    for ob in objects:
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for ob in objects:
        bpy.data.objects.remove(ob, do_unlink=True)
    if smooth is not None:
        for f in bm.faces:
            f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _link(bpy.data.objects.new(name, me))


def empty(name, loc=(0, 0, 0), parent=None):
    ob = _link(bpy.data.objects.new(name, None))
    ob.location = Vector(loc)
    if parent is not None:
        set_parent(ob, parent)
    return ob


def socket(anchor, loc, parent):
    """Placement socket read by the generator (exported as a node named socket_<anchor>)."""
    return empty(f"socket_{anchor}", loc, parent)


def set_parent(child, parent, keep_world=True):
    # matrix_world is stale until the depsgraph updates; read it fresh or nested parts drift.
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    if keep_world:
        child.matrix_parent_inverse = parent.matrix_world.inverted()
        child.matrix_world = mw
    return child


def _meshes(objects):
    return [o for ob in objects for o in [ob] + list(ob.children_recursive) if o.type == "MESH"]


def tri_count(objects):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in _meshes(objects))


# ---------------------------------------------------------------- ambient occlusion
def _hemisphere(samples):
    dirs = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(samples):
        z = 1 - (i + 0.5) / samples  # cosine-ish distribution toward the normal
        z = math.sqrt(z)
        r = math.sqrt(max(0.0, 1 - z * z))
        a = golden * i
        dirs.append(Vector((math.cos(a) * r, math.sin(a) * r, z)))
    return dirs


def bake_ao(objects, samples=32, radius=0.8, strength=0.9, ground=True):
    """Per-vertex ambient occlusion from the whole asset (all parts) plus the ground plane,
    stored in the 'AO' colour attribute. Call after the final merge/parenting, before export."""
    bpy.context.view_layer.update()
    meshes = _meshes(objects)
    verts, polys = [], []
    for o in meshes:
        mw = o.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    if not polys:
        return
    bvh = BVHTree.FromPolygons(verts, polys)
    dirs = _hemisphere(samples)
    for o in meshes:
        mw = o.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        me = o.data
        attr = me.color_attributes.get("AO") or me.color_attributes.new("AO", "FLOAT_COLOR", "POINT")
        for v in me.vertices:
            p = mw @ v.co
            n = (nm @ v.normal).normalized()
            t = n.orthogonal().normalized()
            b = n.cross(t)
            occ = 0.0
            for d in dirs:
                w = t * d.x + b * d.y + n * d.z
                if ground and w.z < -1e-4 and (-p.z / w.z) <= radius and p.z >= -0.01:
                    occ += 1.0
                    continue
                hit = bvh.ray_cast(p + n * 0.006, w, radius)
                if hit[0] is not None:
                    occ += 1.0 - (hit[3] / radius) * 0.5
            ao = 1.0 - strength * occ / len(dirs)
            attr.data[v.index].color = (ao, ao, ao, 1.0)
        me.color_attributes.active_color = attr
        me.color_attributes.render_color_index = me.color_attributes.active_color_index


# ---------------------------------------------------------------- export
def _select_tree(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        for o in [ob] + list(ob.children_recursive):
            o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def export(objects, rel_path):
    """Exports objects (and their children) to <models_out>/<rel_path>.gltf. Returns the path.
    Bakes AO first if no mesh has an 'AO' attribute yet."""
    if not any(o.data.color_attributes.get("AO") for o in _meshes(objects)):
        bake_ao(objects)
    for o in _meshes(objects):
        ao = o.data.color_attributes.get("AO")
        if ao:
            o.data.color_attributes.active_color = ao
    out = MODELS / f"{rel_path}.gltf"
    out.parent.mkdir(parents=True, exist_ok=True)
    # Godot re-imports only when the .gltf text changes, but geometry lives in the .bin: stamp
    # a build id into the scene extras so every rebuild is picked up.
    import time
    bpy.context.scene[P.setting("build_stamp_key")] = f"{time.time():.3f}"
    _select_tree(objects)
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLTF_SEPARATE", use_selection=True,
                              export_yup=True, export_apply=True, export_materials="NONE",
                              export_texcoords=True, export_normals=True, export_extras=True,
                              export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True,
                              export_all_vertex_colors=False)
    return out


# ---------------------------------------------------------------- review sheet
def _palette_rgb():
    table = {}
    for r, row in enumerate(PALETTE_SPEC["rows"]):
        for c, entry in enumerate(row):
            h = entry.split(":")[1].lstrip("#")
            # Workbench shows colour attributes in linear space; convert from sRGB.
            table[(c, r)] = tuple(((int(h[i:i + 2], 16) / 255.0) ** 2.2) for i in (0, 2, 4))
    return table


def _preview_colors(meshes):
    """Writes a 'Preview' corner colour = palette tint x AO (Workbench can't decode the Tint UV)."""
    pal = _palette_rgb()
    for o in meshes:
        me = o.data
        tint = me.uv_layers.get("Tint")
        ao = me.color_attributes.get("AO")
        prev = me.color_attributes.get("Preview") or me.color_attributes.new("Preview", "FLOAT_COLOR", "CORNER")
        for poly in me.polygons:
            for li in poly.loop_indices:
                u, v = tint.data[li].uv if tint else (0.0, 0.0)
                col = int((u % 1.0) * GRID)
                row = int((1.0 - v) * GRID)
                rgb = pal.get((col, row), (1.0, 0.0, 1.0))
                a = ao.data[me.loops[li].vertex_index].color[0] if ao else 1.0
                prev.data[li].color = (rgb[0] * a, rgb[1] * a, rgb[2] * a, 1.0)
        me.color_attributes.active_color = prev


def review_sheet(objects, name, scale_figure=True):
    """Renders a 2x2 sheet (front 3/4, back 3/4, side, gameplay camera pitch) with a scale post
    as tall as the hero (scale_figure_height_m, 1.1 m dragon kid in trick-or-treat). Colours are
    palette tint x AO; the painted materials only show in the in-engine preview
    (engine/godot/review/asset_preview.ps1). Saved to <review_sheets>/<name>.png."""
    meshes = _meshes(objects)
    helpers = []

    def bounds(objs):
        bpy.context.view_layer.update()
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        for o in objs:
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
                hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
        return lo, hi

    lo, hi = bounds(meshes)
    if scale_figure:
        post = cylinder("_scale_post", 0.12, SCALE_H, color=SCALE_COLOR, loc=(hi.x + 0.4, 0, SCALE_H / 2), verts=8)
        helpers.append(post)
        meshes_all = meshes + [post]
        lo, hi = bounds(meshes_all)
    else:
        meshes_all = meshes
    _preview_colors(meshes_all)
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 0.6)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "VERTEX"
    shading.show_shadows = True
    shading.show_cavity = True
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("w") if not scene.world else scene.world
    scene.world = world
    world.color = (0.16, 0.19, 0.32)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = radius * 2.6
    cam = _link(bpy.data.objects.new("cam", cam_data))
    helpers.append(cam)
    scene.camera = cam
    views = [(-35, 20), (145, 20), (-90, 5), (-20, 35)]
    REVIEW.mkdir(parents=True, exist_ok=True)
    tiles = []
    for i, (yaw, pitch) in enumerate(views):
        d = Vector((math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
                    -math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)),
                    math.sin(math.radians(pitch))))
        cam.location = center + d * radius * 4
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        path = REVIEW / f"_{name}_{i}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        tiles.append(path)
    out = REVIEW / f"{name}.png"
    _compose(tiles, out)
    for p in tiles:
        p.unlink(missing_ok=True)
    for h in helpers:
        bpy.data.objects.remove(h, do_unlink=True)
    for o in meshes:
        prev = o.data.color_attributes.get("Preview")
        if prev:
            o.data.color_attributes.remove(prev)
        ao = o.data.color_attributes.get("AO")
        if ao:
            o.data.color_attributes.active_color = ao
    return out


def _compose(tiles, out):
    imgs = [bpy.data.images.load(str(p)) for p in tiles]
    w, h = imgs[0].size
    sheet = bpy.data.images.new("sheet", w * 2, h * 2)
    px = [0.0] * (w * 2 * h * 2 * 4)
    for idx, img in enumerate(imgs):
        src = list(img.pixels)
        ox = (idx % 2) * w
        oy = (1 - idx // 2) * h  # Blender images are bottom-up
        for y in range(h):
            row = src[y * w * 4:(y + 1) * w * 4]
            start = ((oy + y) * w * 2 + ox) * 4
            px[start:start + w * 4] = row
    sheet.pixels = px
    sheet.filepath_raw = str(out)
    sheet.file_format = "PNG"
    sheet.save()
    for img in imgs:
        bpy.data.images.remove(img)
