"""Origin: S:/Repos/trick-or-treat/art/tools/make_vfx.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. Frames/out dirs are vfx_frames / vfx_out.

Designs and renders the game's particle effect art in Blender (headless).

Sprites are modelled as geometry with node-built emission/alpha shaders and rendered with EEVEE
on a transparent film through an orthographic camera:
  sparkle      four-point twinkle star with a soft core (pickups, magic)
  glow         soft round light
  ring         thin glowing ring dotted with tiny stars (pickup / blast shockwave)
  smoke_4x4    cartoon puff of faceted blobs swelling and dissolving (poofs, dust)  16 frames
  (flame_4x4 comes from make_fire.py: a procedural turbulent flame; the old teardrop read as a raindrop)
  swirl_4x4    magic spiral ribbon unwinding and fading (candy pickup)               16 frames
Frames land in vfx_frames (art/vfx/_frames); assemble_vfx.py packs them into vfx_out (game/assets/vfx/).
Little 3D particle meshes (chunky star, heart, candy corn, confetti) are exported as JSON
triangle lists with vertex colours for the game to instance.

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background --factory-startup --python <pipeline>/tools/vfx/make_vfx.py   (cwd = game root)
  python <pipeline>/tools/vfx/assemble_vfx.py
"""
import json
import math
import os
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline_paths as P  # noqa: E402
ROOT = str(P.GAME_ROOT)
FRAMES = str(P.path("vfx_frames"))
OUT = str(P.path("vfx_out"))
SIZE = 256


# ---------------------------------------------------------------- scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.film_transparent = True
    scene.render.resolution_x = SIZE
    scene.render.resolution_y = SIZE
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 2.2
    cam = bpy.data.objects.new("Cam", cam_data)
    cam.location = (0, 0, 10)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def emission_material(name, color_node_builder, alpha_builder):
    """Emission + transparency. Builders receive (nodes, links) and return an output socket."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    try:
        mat.surface_render_method = "BLENDED"
    except AttributeError:
        mat.blend_method = "BLEND"
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    for n in list(nodes):
        nodes.remove(n)
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(color_node_builder(nodes, links), emit.inputs["Color"])
    links.new(alpha_builder(nodes, links), mix.inputs["Fac"])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emit.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def radial(nodes, links, stops):
    """Colour ramp over distance from the object origin: stops are (distance 0..1, colour).
    (Blender's spherical gradient is 1 at the centre, so the stops are mirrored onto it.)"""
    stops = sorted([(1.0 - pos, col) for pos, col in stops])
    coord = nodes.new("ShaderNodeTexCoord")
    grad = nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    links.new(coord.outputs["Object"], grad.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = stops[0][1]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos)
        e.color = col
    links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    return ramp


def value(nodes, v):
    n = nodes.new("ShaderNodeValue")
    n.outputs[0].default_value = v
    return n.outputs[0]


def rgb(nodes, c):
    n = nodes.new("ShaderNodeRGB")
    n.outputs[0].default_value = (c[0], c[1], c[2], 1.0)
    return n.outputs[0]


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def fan_mesh(name, outline, z=0.0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    c = bm.verts.new((0, 0, z))
    ring = [bm.verts.new((x, y, z)) for x, y in outline]
    for i in range(len(ring)):
        bm.faces.new((c, ring[i], ring[(i + 1) % len(ring)]))
    bm.to_mesh(me)
    bm.free()
    return bpy.data.objects.new(name, me)


def star_outline(points, outer, inner, rot=0.0):
    pts = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = rot + i * math.pi / points
        pts.append((math.cos(a) * r, math.sin(a) * r))
    return pts


# ---------------------------------------------------------------- single sprites
def sparkle():
    reset_scene()
    white = lambda n, l: rgb(n, (1, 1, 1))
    def star_alpha(n, l):
        ramp = radial(n, l, [(0.0, (1, 1, 1, 1)), (0.55, (0.85, 0.85, 0.85, 1)), (1.0, (0.0, 0, 0, 1))])
        return ramp.outputs["Color"]
    mat = emission_material("Sparkle", white, star_alpha)
    big = link(fan_mesh("Big", star_outline(4, 1.0, 0.09, math.pi / 2)))
    small = link(fan_mesh("Small", star_outline(4, 0.48, 0.07, math.pi / 4), z=0.01))
    for o in (big, small):
        o.data.materials.append(mat)
    def halo_alpha(n, l):
        ramp = radial(n, l, [(0.0, (0.75, 0.75, 0.75, 1)), (0.25, (0.3, 0.3, 0.3, 1)), (0.5, (0, 0, 0, 1))])
        return ramp.outputs["Color"]
    halo_mat = emission_material("Halo", white, halo_alpha)
    halo = link(fan_mesh("Halo", [(math.cos(a) * 1.0, math.sin(a) * 1.0) for a in [i * math.tau / 48 for i in range(48)]], z=-0.01))
    halo.data.materials.append(halo_mat)
    render(os.path.join(FRAMES, "sparkle.png"))


def glow():
    reset_scene()
    def alpha(n, l):
        ramp = radial(n, l, [(0.0, (1, 1, 1, 1)), (0.35, (0.55, 0.55, 0.55, 1)), (0.75, (0.12, 0.12, 0.12, 1)), (1.0, (0, 0, 0, 1))])
        return ramp.outputs["Color"]
    mat = emission_material("Glow", lambda n, l: rgb(n, (1, 1, 1)), alpha)
    disc = link(fan_mesh("Disc", [(math.cos(a), math.sin(a)) for a in [i * math.tau / 64 for i in range(64)]]))
    disc.data.materials.append(mat)
    render(os.path.join(FRAMES, "glow.png"))


def ring():
    reset_scene()
    # A thin annulus with soft edges (alpha peaks mid-band) and tiny stars set into it.
    me = bpy.data.meshes.new("Ring")
    bm = bmesh.new()
    seg, r0, r1 = 96, 0.78, 0.98
    rows = [0.0, 0.5, 1.0]
    verts = [[bm.verts.new((math.cos(i * math.tau / seg) * (r0 + (r1 - r0) * t), math.sin(i * math.tau / seg) * (r0 + (r1 - r0) * t), 0)) for t in rows]
             for i in range(seg)]
    for i in range(seg):
        a, b = verts[i], verts[(i + 1) % seg]
        for k in range(2):
            bm.faces.new((a[k], b[k], b[k + 1], a[k + 1]))
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new("Ring", me))
    def band_alpha(n, l):
        ramp = radial(n, l, [(0.0, (0, 0, 0, 1)), (0.78, (0, 0, 0, 1)), (0.88, (1, 1, 1, 1)), (0.98, (0, 0, 0, 1))])
        return ramp.outputs["Color"]
    obj.data.materials.append(emission_material("Band", lambda n, l: rgb(n, (1, 1, 1)), band_alpha))
    star_mat = emission_material("Stars", lambda n, l: rgb(n, (1, 1, 1)), lambda n, l: value(n, 1.0))
    for i in range(10):
        a = i * math.tau / 10 + 0.15
        s = link(fan_mesh(f"S{i}", star_outline(4, 0.07 if i % 2 else 0.1, 0.015, a), z=0.01))
        s.location = (math.cos(a) * 0.88, math.sin(a) * 0.88, 0)
        s.data.materials.append(star_mat)
    render(os.path.join(FRAMES, "ring.png"))


# ---------------------------------------------------------------- flipbooks
def smoke():
    """Cartoon poof: faceted blobs that swell, drift up and dissolve, lit from above."""
    rng = random.Random(7)
    blobs = [((rng.uniform(-0.35, 0.35), rng.uniform(-0.3, 0.25), rng.uniform(-0.1, 0.1)), rng.uniform(0.28, 0.45), rng.uniform(0.5, 1.0))
             for _ in range(7)]
    for f in range(16):
        reset_scene()
        t = f / 15.0
        scene = bpy.context.scene
        scene.camera.data.ortho_scale = 2.4

        def color(n, l):
            geo = n.new("ShaderNodeNewGeometry")
            sep = n.new("ShaderNodeSeparateXYZ")
            l.new(geo.outputs["Normal"], sep.inputs[0])
            ramp = n.new("ShaderNodeValToRGB")
            cr = ramp.color_ramp
            cr.elements[0].position = 0.0
            cr.elements[0].color = (0.62, 0.6, 0.85, 1)
            cr.elements[1].position = 0.75
            cr.elements[1].color = (1.0, 1.0, 1.0, 1)
            # Top light: map normal.y (screen up) from [-1, 1] to [0, 1].
            mul = n.new("ShaderNodeMath")
            mul.operation = "MULTIPLY_ADD"
            mul.inputs[1].default_value = 0.5
            mul.inputs[2].default_value = 0.5
            l.new(sep.outputs["Y"], mul.inputs[0])
            l.new(mul.outputs[0], ramp.inputs["Fac"])
            return ramp.outputs["Color"]

        fade = max(0.0, 1.0 - max(0.0, t - 0.35) / 0.65)
        mat = emission_material(f"Smoke{f}", color, lambda n, l: value(n, fade))
        for i, (p, r, life) in enumerate(blobs):
            grow = min(1.0, 0.35 + t * 1.6) * (1.0 - max(0.0, t - life) * 2.0)
            if grow <= 0.02:
                continue
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r * grow, location=(p[0] * (0.7 + t * 0.6), p[1] * (0.7 + t * 0.6) + t * 0.35, p[2]))
            o = bpy.context.active_object
            o.data.materials.append(mat)
            for poly in o.data.polygons:
                poly.use_smooth = False
        render(os.path.join(FRAMES, f"smoke_{f:02d}.png"))


def flame():
    """Teardrop flame flickering through 16 frames: yellow core, orange body, red tips."""
    rng = random.Random(11)
    for f in range(16):
        reset_scene()
        ph = f / 16.0 * math.tau

        def body(scale, sway, colors, name, z):
            me = bpy.data.meshes.new(name)
            bm = bmesh.new()
            # Outline of a teardrop with a wobbling tip.
            pts = []
            for i in range(40):
                a = i / 40 * math.tau
                y = -math.cos(a)
                w = math.sin(a) * (0.55 * (1 - (y + 1) / 2) ** 0.8 + 0.08)
                tip = max(0.0, y) ** 2
                # Licking tip: a travelling wave up the flame, stronger toward the top.
                x = w + math.sin(ph * 2 + y * 3.5) * 0.22 * tip + sway * tip
                stretch = 1.0 + 0.12 * math.sin(ph * 3 + 1.3)
                pts.append((x * scale * (1.08 - 0.08 * stretch), (y * 0.95 * stretch + 0.05) * scale))
            c = bm.verts.new((sway * 0.2 * scale, -0.25 * scale, z))
            ring = [bm.verts.new((x, y, z)) for x, y in pts]
            for i in range(len(ring)):
                bm.faces.new((c, ring[i], ring[(i + 1) % len(ring)]))
            bm.to_mesh(me)
            bm.free()
            obj = link(bpy.data.objects.new(name, me))

            def col(n, l):
                coord = n.new("ShaderNodeTexCoord")
                sep = n.new("ShaderNodeSeparateXYZ")
                l.new(coord.outputs["Object"], sep.inputs[0])
                ramp = n.new("ShaderNodeValToRGB")
                cr = ramp.color_ramp
                cr.elements[0].position = 0.0
                cr.elements[0].color = colors[0]
                cr.elements[1].position = 1.0
                cr.elements[1].color = colors[1]
                mid = cr.elements.new(0.5)
                mid.color = colors[2]
                mul = n.new("ShaderNodeMath")
                mul.operation = "MULTIPLY_ADD"
                mul.inputs[1].default_value = 0.5 / scale
                mul.inputs[2].default_value = 0.4
                l.new(sep.outputs["Y"], mul.inputs[0])
                l.new(mul.outputs[0], ramp.inputs["Fac"])
                return ramp.outputs["Color"]

            def alpha(n, l):
                coord = n.new("ShaderNodeTexCoord")
                sep = n.new("ShaderNodeSeparateXYZ")
                l.new(coord.outputs["Object"], sep.inputs[0])
                m = n.new("ShaderNodeMapRange")
                m.inputs["From Min"].default_value = 0.4 * scale
                m.inputs["From Max"].default_value = 1.0 * scale
                m.inputs["To Min"].default_value = 1.0
                m.inputs["To Max"].default_value = 0.0
                l.new(sep.outputs["Y"], m.inputs["Value"])
                return m.outputs["Result"]

            obj.data.materials.append(emission_material(name, col, alpha))

        sway = math.sin(ph * 2 + 0.7) * 0.16 + rng.uniform(-0.05, 0.05)
        body(1.0, sway, [(1.0, 0.55, 0.12, 1), (0.85, 0.12, 0.05, 1), (1.0, 0.32, 0.06, 1)], "Outer", 0.0)
        body(0.6, sway * 0.6, [(1.0, 0.98, 0.7, 1), (1.0, 0.6, 0.12, 1), (1.0, 0.85, 0.35, 1)], "Inner", 0.01)
        render(os.path.join(FRAMES, f"flame_{f:02d}.png"))


def swirl():
    """Magic spiral: a ribbon that unwinds outward, turning, then fades from its tail."""
    for f in range(16):
        reset_scene()
        t = f / 15.0
        me = bpy.data.meshes.new("Swirl")
        bm = bmesh.new()
        n = 90
        turn = t * 1.4
        rows = []
        for i in range(n):
            u = i / (n - 1)
            if u > 0.25 + t * 0.9:
                break
            a = u * math.tau * 1.35 + turn
            r = 0.08 + u * (0.55 + t * 0.35)
            w = 0.05 + 0.07 * math.sin(u * math.pi)
            p = Vector((math.cos(a) * r, math.sin(a) * r, 0))
            d = Vector((-math.sin(a), math.cos(a), 0)).cross(Vector((0, 0, 1))).normalized()
            rows.append((bm.verts.new(p + d * w), bm.verts.new(p - d * w), u))
        for i in range(len(rows) - 1):
            bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
        uv_layer = bm.loops.layers.uv.new()
        for face in bm.faces:
            for loop in face.loops:
                for a, b, u in rows:
                    if loop.vert in (a, b):
                        loop[uv_layer].uv = (u, 0.0)
        bm.to_mesh(me)
        bm.free()
        obj = link(bpy.data.objects.new("Swirl", me))
        tail = max(0.0, t - 0.4) / 0.6

        def alpha(nodes, links):
            uv = nodes.new("ShaderNodeUVMap")
            sep = nodes.new("ShaderNodeSeparateXYZ")
            links.new(uv.outputs[0], sep.inputs[0])
            m = nodes.new("ShaderNodeMapRange")
            m.inputs["From Min"].default_value = tail
            m.inputs["From Max"].default_value = min(1.0, tail + 0.35)
            m.inputs["To Min"].default_value = 0.0
            m.inputs["To Max"].default_value = 1.0
            links.new(sep.outputs["X"], m.inputs["Value"])
            return m.outputs["Result"]

        obj.data.materials.append(emission_material("Swirl", lambda nodes, links: rgb(nodes, (1, 1, 1)), alpha))
        for k in range(3):
            if t * 3 > k:
                a = k * 2.1 + turn
                r = 0.3 + t * 0.6
                s = link(fan_mesh(f"T{k}", star_outline(4, 0.09 * (1 - tail), 0.02), z=0.01))
                s.location = (math.cos(a) * r, math.sin(a) * r, 0)
                s.data.materials.append(emission_material("Twinkle", lambda nodes, links: rgb(nodes, (1, 1, 1)), lambda nodes, links: value(nodes, 1.0 - tail)))
        render(os.path.join(FRAMES, f"swirl_{f:02d}.png"))


# ---------------------------------------------------------------- particle meshes
def mesh_to_tris(obj, color_fn):
    obj.data.calc_loop_triangles()
    out = {"v": [], "n": [], "c": []}
    for tri in obj.data.loop_triangles:
        n = tri.normal
        for vi in tri.vertices:
            p = obj.data.vertices[vi].co
            c = color_fn(p)
            # Blender Z-up to Godot Y-up.
            out["v"] += [round(p.x, 4), round(p.z, 4), round(-p.y, 4)]
            out["n"] += [round(n.x, 4), round(n.z, 4), round(-n.y, 4)]
            out["c"] += [round(c[0], 3), round(c[1], 3), round(c[2], 3)]
    return out


def particle_meshes():
    reset_scene()
    meshes = {}
    # Chunky five-point star with bevelled edges.
    star = fan_mesh("Star", star_outline(5, 1.0, 0.45, math.pi / 2))
    link(star)
    bpy.context.view_layer.objects.active = star
    star.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 0.32)})
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bevel(offset=0.06, segments=1)
    bpy.ops.object.mode_set(mode="OBJECT")
    star.location = (0, 0, -0.16)
    bpy.ops.object.transform_apply(location=True)
    star.scale = (0.12, 0.12, 0.12)
    bpy.ops.object.transform_apply(scale=True)
    meshes["star"] = mesh_to_tris(star, lambda p: (1, 1, 1))
    # Puffy heart: two lobes and a point, extruded.
    heart_pts = []
    for i in range(36):
        tt = i / 36 * math.tau
        x = 16 * math.sin(tt) ** 3
        y = 13 * math.cos(tt) - 5 * math.cos(2 * tt) - 2 * math.cos(3 * tt) - math.cos(4 * tt)
        heart_pts.append((x / 17.0, y / 17.0 + 0.1))
    heart = link(fan_mesh("Heart", heart_pts))
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = heart
    heart.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 0.3)})
    bpy.ops.object.mode_set(mode="OBJECT")
    heart.location = (0, 0, -0.15)
    bpy.ops.object.transform_apply(location=True)
    heart.scale = (0.1, 0.1, 0.1)
    bpy.ops.object.transform_apply(scale=True)
    meshes["heart"] = mesh_to_tris(heart, lambda p: (1, 1, 1))
    # Candy corn: a cone in three bands (white tip, orange middle, yellow base).
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.07, radius2=0.012, depth=0.16, location=(0, 0, 0))
    corn = bpy.context.active_object

    def corn_color(p):
        if p.z > 0.035:
            return (1.0, 0.97, 0.9)
        if p.z > -0.025:
            return (1.0, 0.5, 0.12)
        return (1.0, 0.85, 0.2)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.loopcut_slide(MESH_OT_loopcut={"number_cuts": 2, "edge_index": 1})
    bpy.ops.object.mode_set(mode="OBJECT")
    meshes["corn"] = mesh_to_tris(corn, corn_color)
    # Confetti: a small curled square.
    me = bpy.data.meshes.new("Confetti")
    bm = bmesh.new()
    vs = []
    for i in range(4):
        u = i / 3
        vs.append((bm.verts.new((-0.05, -0.05 + u * 0.1, math.sin(u * math.pi) * 0.02)), bm.verts.new((0.05, -0.05 + u * 0.1, math.sin(u * math.pi) * 0.02))))
    for i in range(3):
        bm.faces.new((vs[i][0], vs[i][1], vs[i + 1][1], vs[i + 1][0]))  # drawn double-sided in game
    bm.to_mesh(me)
    bm.free()
    conf = link(bpy.data.objects.new("Confetti", me))
    meshes["confetti"] = mesh_to_tris(conf, lambda p: (1, 1, 1))
    with open(os.path.join(OUT, "particle_meshes.json"), "w") as f:
        json.dump(meshes, f)


def main():
    import sys
    os.makedirs(FRAMES, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    if "--meshes-only" in sys.argv:
        particle_meshes()
        print("VFX_DONE")
        return
    sparkle()
    glow()
    ring()
    smoke()
    swirl()
    particle_meshes()
    print("VFX_DONE")


main()
