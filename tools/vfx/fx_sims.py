# Origin: S:/Repos/OpenXcom-Extended-3D/art/source/vfx/fx_sims.py (imported 2026-10-25)
# Changed: header only (paths are CLI arguments)
# VFX flipbook sims (Mantaflow) and EEVEE renders for the battlescape effects.
# Usage: blender --background --factory-startup --threads 2 --python fx_sims.py -- <sim> <out_dir> [bake|render|all]
# Sims: fireball (explosion: fire + smoke burst), smoke (smoke puff), fire (continuous flames, loop source),
#       scorch (ground-hugging burst seen from above: scorch decal source),
#       jet (2026-10-13: a pressurised fire jet out of a narrow vent, the blown-open tank's crater: loop source).
# Moved into the repo from the VFX worker's sandbox on 2026-10-13 (oxp/fx/textures/provenance.json).
# Passes: E = emission over black (fire colour), R / T / L = smoke lit by a sun from the camera's right / top / left,
#         A = alpha comes with every pass (film transparent).
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SIM = argv[0]
OUT = argv[1]
MODE = argv[2] if len(argv) > 2 else "all"

CFG = {
    #           domain size (x, y, z), domain centre z, res, noise, frames, emit frames, render frames
    "fireball": dict(size=(3.4, 3.4, 3.6), cz=1.5, res=84, noise=2, frames=70, emit=(1, 5), render=(2, 65), px=512, elev=25.0, ortho=3.3, ts=0.5),
    "smoke":    dict(size=(4.2, 4.2, 4.2), cz=1.7, res=72, noise=2, frames=90, emit=(1, 8), render=(6, 69), px=512, elev=25.0, ortho=4.0, ts=0.6),
    "fire":     dict(size=(2.4, 2.4, 4.0), cz=1.7, res=88, noise=2, frames=150, emit=(1, 150), render=(54, 133), px=512, elev=20.0, ortho=3.4, ts=1.0),
    "scorch":   dict(size=(6.0, 6.0, 1.6), cz=0.6, res=96, noise=2, frames=22, emit=(1, 3), render=(8, 20), px=1024, elev=90.0, ortho=4.2, ts=1.0),
    "jet":      dict(size=(2.2, 2.2, 6.0), cz=2.9, res=110, noise=2, frames=150, emit=(1, 150), render=(54, 133), px=512, elev=20.0, ortho=5.6, ts=1.0),
}[SIM]
if os.environ.get("FX_QUICK"):
    CFG.update(res=int(os.environ.get("FX_QUICK_RES", "32")), noise=1, frames=int(os.environ.get("FX_QUICK_FRAMES", "12")), px=128)
    CFG.update(render=(CFG["frames"] - 2, CFG["frames"] - 1))

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

scene.frame_start = 1
scene.frame_end = CFG["frames"]
scene.render.fps = 24

# --- domain -----------------------------------------------------------------------------
sx, sy, sz = CFG["size"]
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, CFG["cz"]))
domain = bpy.context.object
domain.name = "Domain"
domain.scale = (sx, sy, sz)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
mod = domain.modifiers.new("Fluid", 'FLUID')
mod.fluid_type = 'DOMAIN'
ds = mod.domain_settings
ds.domain_type = 'GAS'
ds.resolution_max = CFG["res"]
ds.use_noise = CFG["noise"] > 1
if ds.use_noise:
    ds.noise_scale = CFG["noise"]
    ds.noise_strength = 1.4
ds.cache_directory = os.path.join(OUT, "cache")
ds.cache_type = 'ALL'
ds.time_scale = CFG["ts"]
ds.cache_frame_start = 1
ds.cache_frame_end = CFG["frames"]
ds.use_collision_border_top = False
ds.use_collision_border_front = False
ds.use_collision_border_back = False
ds.use_collision_border_left = False
ds.use_collision_border_right = False
ds.use_collision_border_bottom = True

# --- flow -------------------------------------------------------------------------------
if SIM == "fireball":
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.45, location=(0, 0, 0.75))
elif SIM == "smoke":
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.55, location=(0, 0, 0.9))
elif SIM == "fire":
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.55, depth=0.08, location=(0, 0, 0.0))
elif SIM == "jet":
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.2, depth=0.1, location=(0, 0, 0.05))
else:  # scorch
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.45, location=(0, 0, 0.12))
    bpy.context.object.scale = (1.0, 1.0, 0.35)
flow = bpy.context.object
flow.name = "Flow"
fm = flow.modifiers.new("Fluid", 'FLUID')
fm.fluid_type = 'FLOW'
fs = fm.flow_settings
fs.flow_behavior = 'INFLOW'
fs.flow_source = 'MESH'
fs.subframes = 2
fs.surface_distance = {"fire": 0.25, "jet": 0.1}.get(SIM, 0.6)
fs.use_initial_velocity = True

if SIM == "fireball":
    fs.flow_type = 'BOTH'
    fs.fuel_amount = 3.2
    fs.temperature = 3.5
    fs.density = 1.0
    fs.smoke_color = (0.10, 0.09, 0.085)
    fs.velocity_normal = 9.0
    fs.velocity_random = 3.0
    fs.velocity_coord = (0, 0, 0.8)
    ds.vorticity = 0.5
    ds.alpha = 0.05
    ds.beta = 1.3
    ds.burning_rate = 0.65
    ds.flame_smoke = 1.4
    ds.flame_vorticity = 0.9
    ds.flame_ignition = 1.25
    ds.flame_max_temp = 3.0
    ds.flame_smoke_color = (0.12, 0.11, 0.10)
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 70
    ds.use_dissolve_smoke_log = True
elif SIM == "smoke":
    fs.flow_type = 'SMOKE'
    fs.temperature = 0.9
    fs.density = 1.4
    fs.smoke_color = (0.8, 0.8, 0.8)
    fs.velocity_normal = 3.2
    fs.velocity_random = 0.8
    fs.velocity_coord = (0, 0, 0.6)
    ds.vorticity = 0.45
    ds.alpha = 0.0
    ds.beta = 0.55
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 110
    ds.use_dissolve_smoke_log = True
elif SIM == "fire":
    fs.flow_type = 'BOTH'
    fs.fuel_amount = 1.7
    fs.temperature = 1.4
    fs.density = 0.15
    fs.smoke_color = (0.10, 0.09, 0.085)
    fs.velocity_normal = 0.2
    fs.velocity_random = 1.0
    fs.velocity_coord = (0, 0, 2.6)
    ds.vorticity = 1.0
    ds.alpha = 0.0
    ds.beta = 4.0
    ds.burning_rate = 0.32
    ds.flame_smoke = 0.25
    ds.flame_vorticity = 2.6
    ds.flame_ignition = 1.1
    ds.flame_max_temp = 1.8
    ftex = bpy.data.textures.new("Flicker", 'CLOUDS')
    ftex.noise_scale = 0.3
    fs.use_texture = True
    fs.noise_texture = ftex
    fs.texture_map_type = 'AUTO'
    fs.texture_size = 1.0
    fs.texture_offset = 0.0
    fs.keyframe_insert("texture_offset", frame=1)
    fs.texture_offset = 6.0
    fs.keyframe_insert("texture_offset", frame=150)
    ds.flame_smoke_color = (0.12, 0.11, 0.10)
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 20
    ds.use_dissolve_smoke_log = True
elif SIM == "jet":
    # fuel driven out of a narrow vent at speed: a tight, roaring core that breaks into turbulent tongues higher up
    fs.flow_type = 'BOTH'
    fs.fuel_amount = 3.6
    fs.temperature = 2.2
    fs.density = 0.35
    fs.smoke_color = (0.08, 0.07, 0.065)
    fs.velocity_normal = 0.0
    fs.velocity_random = 0.6
    fs.velocity_coord = (0, 0, 17.0)
    ds.vorticity = 0.4
    ds.alpha = 0.0
    ds.beta = 2.5
    ds.burning_rate = 0.2
    ds.flame_smoke = 0.7
    ds.flame_vorticity = 1.5
    ds.flame_ignition = 1.1
    ds.flame_max_temp = 2.4
    ftex = bpy.data.textures.new("Pulse", 'CLOUDS')
    ftex.noise_scale = 0.18
    fs.use_texture = True
    fs.noise_texture = ftex
    fs.texture_map_type = 'AUTO'
    fs.texture_size = 1.0
    fs.texture_offset = 0.0
    fs.keyframe_insert("texture_offset", frame=1)
    fs.texture_offset = 9.0
    fs.keyframe_insert("texture_offset", frame=150)
    ds.flame_smoke_color = (0.10, 0.09, 0.085)
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 18
    ds.use_dissolve_smoke_log = True
    # the vent's initial velocity alone is lost within a few cells (it burned as a bonfire, 2026-10-13): an upward wind
    # field drives the whole column, its noise breaking the jet into tongues; slower burning carries the fuel high
    ds.burning_rate = float(os.environ.get("FX_JET_BURN", "0.12"))
    bpy.ops.object.effector_add(type='WIND', location=(0, 0, -0.05))
    wind = bpy.context.object
    wind.name = "JetWind"
    wind.field.strength = float(os.environ.get("FX_JET_WIND", "9.0"))
    wind.field.noise = 1.6
    wind.field.seed = 7
else:  # scorch: a flat burst along the ground
    fs.flow_type = 'SMOKE'
    fs.temperature = 0.0
    fs.density = 2.0
    fs.velocity_normal = 14.0
    fs.velocity_random = 4.0
    ds.vorticity = 1.4
    ds.alpha = 0.0
    ds.beta = 0.0

# emission window: the flow sits inside the domain only during its emit frames
e0, e1 = CFG["emit"]
inside = flow.location.copy()
flow.keyframe_insert("location", frame=e0)
if e1 < CFG["frames"]:
    flow.location = inside
    flow.keyframe_insert("location", frame=e1)
    flow.location = inside + Vector((0, 0, -50.0))
    flow.keyframe_insert("location", frame=e1 + 1)
    for fc in flow.animation_data.action.fcurves if hasattr(flow.animation_data.action, "fcurves") else []:
        for k in fc.keyframe_points:
            k.interpolation = 'CONSTANT'
    try:
        for layer in flow.animation_data.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        for k in fc.keyframe_points:
                            k.interpolation = 'CONSTANT'
    except Exception:
        pass
fs.velocity_factor = 0.0 if hasattr(fs, "velocity_factor") else 0
flow.hide_render = True


def constant_keys(ob):
    try:
        for layer in ob.animation_data.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        for k in fc.keyframe_points:
                            k.interpolation = 'CONSTANT'
    except Exception:
        for fc in getattr(ob.animation_data.action, "fcurves", []):
            for k in fc.keyframe_points:
                k.interpolation = 'CONSTANT'


# fireball / smoke: irregular lobes around the core, each blowing out its own way (a sphere alone makes a ball)
if SIM in ("fireball", "smoke") and os.environ.get("FX_LOBES", "1") == "1":
    import random
    random.seed(7 if SIM == "fireball" else 11)
    tex = bpy.data.textures.new("Lumps", 'CLOUDS')
    tex.noise_scale = 0.25
    disp = flow.modifiers.new("Lumps", 'DISPLACE')
    disp.texture = tex
    disp.strength = 0.22
    flow.modifiers.move(len(flow.modifiers) - 1, 0)
    lobes = 7 if SIM == "fireball" else 5
    for i in range(lobes):
        d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.2, 1.0))).normalized()
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=random.uniform(0.16, 0.28),
                                              location=inside + d * random.uniform(0.25, 0.45))
        lob = bpy.context.object
        lm_ = lob.modifiers.new("Fluid", 'FLUID')
        lm_.fluid_type = 'FLOW'
        ls = lm_.flow_settings
        for k in ("flow_type", "flow_behavior", "flow_source", "subframes", "surface_distance", "fuel_amount",
                  "temperature", "density", "smoke_color", "velocity_random"):
            setattr(ls, k, getattr(fs, k))
        ls.use_initial_velocity = True
        ls.velocity_normal = random.uniform(2.0, 4.0)
        ls.velocity_coord = d * random.uniform(4.0, 9.0) * (1.0 if SIM == "fireball" else 0.45)
        if hasattr(ls, "velocity_factor"):
            ls.velocity_factor = 0.0
        here = lob.location.copy()
        lob.keyframe_insert("location", frame=e0)
        lob.location = here
        lob.keyframe_insert("location", frame=max(e0, e1 - random.randint(0, 2)))
        lob.location = here + Vector((0, 0, -50.0))
        lob.keyframe_insert("location", frame=e1 + 1)
        constant_keys(lob)
        lob.hide_render = True
    if SIM == "fireball":
        ds.vorticity = 0.75
        ds.flame_vorticity = 1.4
        if ds.use_noise:
            ds.noise_strength = 2.2


def bake():
    with bpy.context.temp_override(scene=scene, active_object=domain, object=domain, selected_objects=[domain]):
        bpy.ops.fluid.bake_all()


# --- material ---------------------------------------------------------------------------
def volume_material(emissive: bool, smoke_albedo):
    mat = bpy.data.materials.new("Vol_%s" % ("E" if emissive else "L"))
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    nt.links.new(pv.outputs[0], out.inputs['Volume'])
    dens = float(os.environ.get("FX_DENSITY", {"fireball": 9.0, "smoke": 4.0, "fire": 3.0, "scorch": 1.2, "jet": 3.0}[SIM]))
    pv.inputs['Density'].default_value = dens
    pv.inputs['Color'].default_value = (*smoke_albedo, 1.0)
    if 'Anisotropy' in pv.inputs:
        pv.inputs['Anisotropy'].default_value = 0.25
    if emissive:
        attr = nt.nodes.new('ShaderNodeAttribute')
        attr.attribute_name = 'flame'
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        cr = ramp.color_ramp
        cr.elements[0].position = 0.0
        cr.elements[0].color = (0, 0, 0, 1)
        cr.elements[1].position = 1.0
        cr.elements[1].color = (1.0, 0.95, 0.80, 1) if SIM == "fireball" else (1.0, 0.86, 0.55, 1)
        stops = ((0.12, (0.35, 0.03, 0.0, 1)), (0.35, (1.0, 0.25, 0.02, 1)), (0.65, (1.0, 0.62, 0.15, 1))) if SIM == "fireball" else \
            ((0.08, (0.30, 0.02, 0.0, 1)), (0.3, (0.9, 0.18, 0.01, 1)), (0.6, (1.0, 0.45, 0.06, 1)), (0.85, (1.0, 0.68, 0.22, 1)))
        for pos, col in stops:
            el = cr.elements.new(pos)
            el.color = col
        nt.links.new(attr.outputs['Fac'], ramp.inputs['Fac'])
        nt.links.new(ramp.outputs['Color'], pv.inputs['Emission Color'])
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = 9.0 if SIM == "fireball" else 4.5
        nt.links.new(attr.outputs['Fac'], mul.inputs[0])
        nt.links.new(mul.outputs[0], pv.inputs['Emission Strength'])
        if 'Blackbody Intensity' in pv.inputs:
            pv.inputs['Blackbody Intensity'].default_value = 0.0
    else:
        pv.inputs['Emission Strength'].default_value = 0.0
        if 'Blackbody Intensity' in pv.inputs:
            pv.inputs['Blackbody Intensity'].default_value = 0.0
        # lighting passes store light only: a neutral albedo, not the sim's smoke colour attribute
        if 'Color Attribute' in pv.inputs:
            pv.inputs['Color Attribute'].default_value = ""
        elif hasattr(pv, "color_attribute"):
            pv.color_attribute = ""
    return mat


# --- camera, lights, render settings -------------------------------------------------------
elev = math.radians(CFG["elev"])
target = Vector((0, 0, CFG["cz"] if SIM != "scorch" else 0.0))
if SIM == "fire":
    target = Vector((0, 0, 1.45))
if SIM == "jet":
    target = Vector((0, 0, 2.7))
if SIM == "fireball":
    target = Vector((0, 0, 1.35))
cam_data = bpy.data.cameras.new("Cam")
cam_data.type = 'ORTHO'
cam_data.ortho_scale = CFG["ortho"]
cam_data.clip_start = 0.1
cam_data.clip_end = 100.0
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
dist = 30.0
if SIM == "scorch":
    cam.location = target + Vector((0, 0, dist))
    cam.rotation_euler = (0, 0, 0)
else:
    cam.location = target + Vector((0, -math.cos(elev), math.sin(elev))) * dist
    cam.rotation_euler = (math.radians(90) - elev, 0, 0)
scene.camera = cam
bpy.context.view_layer.update()
cam_right = (cam.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
cam_up = (cam.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()

sun_data = bpy.data.lights.new("Sun", 'SUN')
sun_data.energy = 4.0
sun_data.angle = math.radians(2.0)
if hasattr(sun_data, "volume_factor"):
    sun_data.volume_factor = 1.0
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)

world = bpy.data.worlds.new("W")
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0, 0, 0, 1)
    bg.inputs[1].default_value = 0.0
scene.world = world

r = scene.render
r.engine = 'BLENDER_EEVEE'
r.resolution_x = CFG["px"]
r.resolution_y = CFG["px"]
r.resolution_percentage = 100
r.film_transparent = True
r.image_settings.file_format = 'PNG'
r.image_settings.color_mode = 'RGBA'
r.image_settings.color_depth = '16'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0
scene.display_settings.display_device = 'sRGB'
ee = scene.eevee
for k, v in (("taa_render_samples", 24), ("volumetric_tile_size", '2'), ("volumetric_samples", 96),
             ("volumetric_sample_distribution", 0.6), ("use_volumetric_shadows", True), ("volumetric_shadow_samples", 24),
             ("volumetric_start", 5.0), ("volumetric_end", 60.0), ("use_volume_custom_range", True),
             ("volumetric_ray_depth", 8), ("use_shadows", True)):
    if hasattr(ee, k):
        try:
            setattr(ee, k, v)
        except Exception as ex:
            print("eevee setting", k, ex)


def aim_sun(direction: Vector):
    # a sun lamp shines along its local -Z: point -Z away from `direction` (the side the light comes from)
    sun.rotation_euler = direction.normalized().to_track_quat('Z', 'Y').to_euler()


def render_pass(name: str, f0: int, f1: int):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        r.filepath = os.path.join(d, "%04d.png" % f)
        bpy.ops.render.render(write_still=True)


if MODE in ("bake", "all"):
    bake()
    print("BAKED", SIM)

if MODE in ("render", "all"):
    f0, f1 = CFG["render"]
    if SIM in ("fireball", "fire", "jet"):
        domain.data.materials.clear()
        domain.data.materials.append(volume_material(True, (0.05, 0.045, 0.04)))
        sun.hide_render = True
        render_pass("E", f0, f1)
        sun.hide_render = False
    if SIM in ("fireball", "smoke"):
        domain.data.materials.clear()
        domain.data.materials.append(volume_material(False, (0.92, 0.92, 0.92)))
        for name, d in (("R", cam_right), ("T", cam_up), ("L", -cam_right)):
            aim_sun(d)
            render_pass(name, f0, f1)
    if SIM == "scorch":
        domain.data.materials.clear()
        domain.data.materials.append(volume_material(False, (0.0, 0.0, 0.0)))
        sun.hide_render = True
        render_pass("A", f0, f1)
    print("RENDERED", SIM)

