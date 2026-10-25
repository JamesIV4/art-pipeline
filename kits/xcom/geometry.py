# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/geometry.py (imported 2026-10-25)
# Changed: imports xcom_kit_paths first so materials.py resolves from art-pipeline/tools/textures
"""Economical smooth modeling helpers. All authoring parts are joined for export."""
import math
import random
import bpy
from mathutils import Vector
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import xcom_kit_paths  # noqa: E402,F401  (puts art-pipeline/tools/textures on sys.path for materials.py)
from materials import material  # noqa: E402


def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def finish(obj, name, mat, smooth=False, bone=None):
    obj.name = name
    obj.data.materials.clear()
    obj.data.materials.append(material(mat))
    if bone:
        obj["bone"] = bone
    active(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for face in obj.data.polygons:
        face.use_smooth = smooth
    return obj


def box(name, pos, size, mat, bevel=.015, bone=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = bpy.context.object
    obj.scale = size
    finish(obj, name, mat, False, bone)
    if bevel:
        mod = obj.modifiers.new("Manufactured edge radius", "BEVEL")
        mod.width = min(bevel, min(size)*.24)
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for face in obj.data.polygons:
            face.use_smooth = True
        normal = obj.modifiers.new("Flat panels, smooth bevels", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
        bpy.ops.object.modifier_apply(modifier=normal.name)
    return obj


def ellipsoid(name, pos, scale, mat, bone=None, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=pos)
    obj = bpy.context.object
    obj.scale = scale
    return finish(obj, name, mat, True, bone)


def cylinder(name, a, b, radius, mat, radius2=None, sides=20, bone=None):
    a, b = Vector(a), Vector(b)
    delta = b-a
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=radius,
        radius2=radius if radius2 is None else radius2, depth=delta.length, location=(a+b)/2)
    obj = bpy.context.object
    obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
    return finish(obj, name, mat, True, bone)


def mesh(name, vertices, faces, mat, smooth=False, uvs=None, bone=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    finish(obj, name, mat, smooth, bone)
    if uvs:
        layer = data.uv_layers.new(name="UVMap")
        for face in data.polygons:
            for loop in face.loop_indices:
                layer.data[loop].uv = uvs[data.loops[loop].vertex_index]
        obj["authored_uv"] = True
    return obj


def tube(name, points, radii, mat, sides=14, bone=None):
    points = [Vector(p) for p in points]
    vertices, faces = [], []
    for i, point in enumerate(points):
        tangent = points[min(i+1, len(points)-1)]-points[max(i-1, 0)]
        tangent.normalize()
        up = Vector((0, 0, 1)) if abs(tangent.z) < .85 else Vector((0, 1, 0))
        right = tangent.cross(up).normalized()
        other = tangent.cross(right).normalized()
        radius = radii[i] if isinstance(radii, (list, tuple)) else radii
        for j in range(sides):
            angle = math.tau*j/sides
            vertices.append(tuple(point + radius*(math.cos(angle)*right+math.sin(angle)*other)))
    for i in range(len(points)-1):
        for j in range(sides):
            a = i*sides+j
            b = i*sides+(j+1) % sides
            faces.append((a, b, b+sides, a+sides))
    faces.extend((tuple(reversed(range(sides))), tuple(range((len(points)-1)*sides, len(points)*sides))))
    return mesh(name, vertices, faces, mat, True, bone=bone)


def lathe(name, profile, mat, pos=(0, 0, 0), sides=32, bone=None):
    vertices = [(pos[0]+r*math.cos(j*math.tau/sides), pos[1]+r*math.sin(j*math.tau/sides), pos[2]+z)
                for r, z in profile for j in range(sides)]
    faces = []
    for i in range(len(profile)-1):
        for j in range(sides):
            a, b = i*sides+j, i*sides+(j+1) % sides
            faces.append((a, b, b+sides, a+sides))
    faces.extend((tuple(reversed(range(sides))), tuple(range((len(profile)-1)*sides, len(profile)*sides))))
    return mesh(name, vertices, faces, mat, True, bone=bone)


def card(name, center, width, height, mat, angle=0, tilt=0):
    center = Vector(center)
    right = Vector((math.cos(angle), math.sin(angle), 0))*width/2
    up = Vector((-math.sin(angle)*math.sin(tilt), math.cos(angle)*math.sin(tilt), math.cos(tilt)))*height/2
    return mesh(name, [tuple(center-right-up), tuple(center+right-up), tuple(center+right+up), tuple(center-right+up)],
                [(0, 1, 2, 3)], mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def join(parts, name):
    parts = [p for p in parts if p and p.name in bpy.data.objects]
    active(parts[0])
    for p in parts:
        p.select_set(True)
        # Establish physical-scale UVs before joining. Applying transforms here
        # prevents model origins/pivots from modifying world-space UV projection.
        if not p.get("authored_uv"):
            project_uv(p)
    if len(parts) > 1:
        bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    # Join can retain duplicate slots: remap to unique materials explicitly.
    original = list(obj.data.materials)
    unique = list(dict.fromkeys(original))
    indices = [unique.index(original[f.material_index]) for f in obj.data.polygons]
    obj.data.materials.clear()
    for mat in unique:
        obj.data.materials.append(mat)
    for face, index in zip(obj.data.polygons, indices):
        face.material_index = index
    return obj


def project_uv(obj):
    data = obj.data
    layer = data.uv_layers.active or data.uv_layers.new(name="UVMap")
    for face in data.polygons:
        n = obj.matrix_world.to_3x3() @ face.normal
        axis = max(range(3), key=lambda i: abs(n[i]))
        axes = ((1, 2), (0, 2), (0, 1))[axis]
        for loop in face.loop_indices:
            v = obj.matrix_world @ data.vertices[data.loops[loop].vertex_index].co
            layer.data[loop].uv = (v[axes[0]]*.5, v[axes[1]]*.5)


def object_parts():
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.get("review_only")]


def stone(name, center, scale, mat="rock", seed=0):
    rng = random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=center)
    obj = bpy.context.object
    for v in obj.data.vertices:
        v.co *= rng.uniform(.83, 1.17)
    obj.scale = scale
    finish(obj, name, mat, True)
    mod = obj.modifiers.new("Weather-rounded silhouette", "BEVEL")
    mod.width = .02
    mod.segments = 1
    active(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj
