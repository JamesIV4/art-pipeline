# Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/export_health.py (imported 2026-10-25)
# Changed: geometry.py is imported from art-pipeline/kits/xcom
"""Static export health: remove collapsed bevel triangles and repair UV bases.

These numerical fixes are not artistic acceptance. Changed exports must get new
render evidence and geometry/UV/tangent validation before manual approval.
"""
import bpy
import bmesh
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "kits" / "xcom"))  # geometry.py
from geometry import active  # noqa: E402


def prepare_static_mesh(model):
    active(model)
    triangulate = model.modifiers.new("Explicit export triangles", "TRIANGULATE")
    triangulate.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    bm = bmesh.new()
    bm.from_mesh(model.data)
    before = len(bm.faces)
    # Some clipped/beveled faces retain coincident endpoints or collinear
    # cap points. Dissolve their zero-length geometry, retaining real faces.
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=list(bm.edges))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(model.data)
    bm.free()
    model.data.update()
    uv = model.data.uv_layers.active
    assert uv, "Missing UV layer"
    repaired = 0
    for face in model.data.polygons:
        assert len(face.loop_indices) == 3
        assert face.area > 1e-12, "Collapsed face remained after bevel cleanup"
        loops = list(face.loop_indices)
        coords = [uv.data[loop].uv.copy() for loop in loops]
        a, b, c = coords
        determinant = (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
        if abs(determinant) > 1e-13:
            continue
        # Nonplanar torn caps can triangulate into a plane different from the
        # original ngon's projection. Choose this triangle's stable plane and
        # stay near its authored image crop rather than replacing the material.
        normal_axis = max(range(3), key=lambda axis: abs(face.normal[axis]))
        axes = [axis for axis in range(3) if axis != normal_axis]
        points = [model.data.vertices[model.data.loops[loop].vertex_index].co for loop in loops]
        projected = [(point[axes[0]], point[axes[1]]) for point in points]
        low = [min(point[axis] for point in projected) for axis in range(2)]
        span = [max(point[axis] for point in projected)-low[axis] for axis in range(2)]
        assert all(value > 1e-10 for value in span), "No stable triangle projection"
        center = [sum(point[axis] for point in coords)/3 for axis in range(2)]
        old_span = [max(point[axis] for point in coords)-min(point[axis] for point in coords) for axis in range(2)]
        extent = [max(old_span[axis], .002) for axis in range(2)]
        for loop, point in zip(loops, projected):
            uv.data[loop].uv = tuple(center[axis]+((point[axis]-low[axis])/span[axis]-.5)*extent[axis] for axis in range(2))
        repaired += 1
    active(model)
    weighted = model.modifiers.new("Cleaned broad-face normals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    model["export_uv_projection_repairs"] = repaired
    model["export_face_cleanup_delta"] = before-len(model.data.polygons)
    return {"uv_projection_repairs": repaired, "face_cleanup_delta": before-len(model.data.polygons)}
