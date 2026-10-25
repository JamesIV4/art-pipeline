# Origin: S:\Repos\trick-or-treat\native\src\play\festival_game.cpp (preview mode: parse_cmdline --preview/--capture,
#   setup_preview, step_preview, merge_bounds) and S:\Repos\trick-or-treat\native\src\gen\asset_library.cpp
#   (apply_material_recursive) (imported 2026-10-25)
# Changes: C++ (GDExtension) translated to a standalone GDScript scene, so a game without the extension gets the same
#   four-view review sheet. Same views, framing, lights, waits and sheet layout. Differences: the scene builds its own
#   WorldEnvironment / Moon / camera / PostFX (from an Environment preset) instead of reusing the game's main scene;
#   the material override is optional (--material, the C++ always used the generator's toon material); the lawn +
#   paver ground needs explicit toon UV2 cells (--ground-uv2 / --path-uv2) because the palette / material indices
#   were C++ constants (pal::LAWN, mat::GRASS, ...); without them a neutral grid floor (floor_grid.gdshader) is used.
extends Node3D
## In-engine review sheet of one asset: 2 x 2 views, 1600 x 900 PNG.
##   top row:    night lighting (moon + warm porch light), front-left and back-right
##   bottom row: neutral studio key (moon dimmed to 0.25) for textures, front-left high and side-on low
## Run (not headless; it renders):
##   godot --path <project> --resolution 1600x900 res://addons/art_pipeline/review/asset_preview.tscn -- \
##     --preview=res://assets/models/props/pumpkin.gltf --capture=C:/out/pumpkin.png \
##     [--material=res://materials/toon.tres | none] [--env=res://...Environment.tres] \
##     [--ground-uv2=layer,u,v [--path-uv2=layer,u,v]] [--no-post]
## Prints "CAPTURED <path>" and quits; quits with code 1 when the asset cannot be loaded.

const PostFx := preload("../post_fx/post_fx.gd")
const FloorGrid := preload("../shaders/surface/floor_grid.gdshader")

# yaw, pitch (radians), studio light on
const VIEWS := [[-0.6, 0.38, false], [2.5, 0.38, false], [-0.6, 0.45, true], [-1.57, 0.12, true]]
const SHEET := Vector2i(1600, 900)
const TILE := Vector2i(800, 450)
const FOV := 56.0

var preview_path := ""
var capture_path := "user://preview.png"
var material_path := ""
var env_path := ""
var ground_uv2 := Vector3(-1, 0, 0)    # x < 0: none
var path_uv2 := Vector3(-1, 0, 0)
var use_post := true

var _root: Node3D
var _cam: Camera3D
var _moon: DirectionalLight3D
var _studio: DirectionalLight3D
var _box := AABB()
var _sheet: Image
var _view := 0
var _wait := 8


func _ready() -> void:
	env_path = (get_script() as Script).resource_path.get_base_dir().get_base_dir().path_join("presets/env_night_storybook.tres")
	_parse_args()
	if preview_path.is_empty():
		push_error("asset_preview: pass --preview=res://...gltf")
		get_tree().quit(1)
		return
	_setup()


func _parse_args() -> void:
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--preview="):
			preview_path = a.substr(10)
		elif a.begins_with("--capture="):
			capture_path = a.substr(10)
		elif a.begins_with("--material="):
			material_path = a.substr(11)
		elif a.begins_with("--env="):
			env_path = a.substr(6)
		elif a.begins_with("--ground-uv2="):
			ground_uv2 = _vec3(a.substr(13))
		elif a.begins_with("--path-uv2="):
			path_uv2 = _vec3(a.substr(11))
		elif a == "--no-post":
			use_post = false


static func _vec3(s: String) -> Vector3:
	var p := s.split(",")
	if p.size() != 3:
		push_error("asset_preview: expected layer,u,v, got " + s)
		return Vector3(-1, 0, 0)
	return Vector3(p[0].to_float(), p[1].to_float(), p[2].to_float())


func _setup() -> void:
	# The toon shader's camera-to-player occluder cutout stays off in previews.
	if &"cutout_radius" in RenderingServer.global_shader_parameter_get_list():
		RenderingServer.global_shader_parameter_set(&"cutout_radius", 0.0)
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	var env := load(env_path) as Environment
	we.environment = (env.duplicate() as Environment) if env else Environment.new()   # duplicate: PostFX attaches a compositor
	add_child(we)                                                    # no camera attributes: no toy-lens blur on close-ups
	_moon = DirectionalLight3D.new()
	_moon.name = "Moon"
	_moon.light_color = Color(0.6, 0.7, 1.0)
	_moon.light_energy = 0.62
	_moon.light_volumetric_fog_energy = 0.6
	_moon.shadow_enabled = true
	_moon.shadow_opacity = 0.78
	_moon.shadow_bias = 0.05
	_moon.shadow_blur = 1.5
	_moon.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	_moon.directional_shadow_max_distance = 70.0
	add_child(_moon)
	_moon.global_transform = Transform3D(Basis.looking_at(Vector3(-0.3, -0.75, -0.6).normalized(), Vector3.UP), Vector3.ZERO)
	_cam = Camera3D.new()
	_cam.fov = FOV
	_cam.near = 0.1
	_cam.far = 400.0
	add_child(_cam)
	_cam.make_current()
	if use_post:
		var post := Node.new()
		post.name = "PostFX"
		post.set_script(PostFx)
		add_child(post)

	_root = Node3D.new()
	_root.name = "Preview"
	add_child(_root)
	var override: Material = null
	if not material_path.is_empty() and material_path != "none":
		override = load(material_path) as Material
		if override == null:
			push_warning("asset_preview: cannot load material " + material_path + "; keeping the model's own")
	_root.add_child(_ground(override))
	var scene := load(preview_path) as PackedScene
	if scene == null:
		push_error("Preview: cannot load " + preview_path)
		get_tree().quit(1)
		return
	var asset := scene.instantiate() as Node3D
	if override:
		_apply_material_recursive(asset, override)
	_root.add_child(asset)
	var first := true
	for mi in _meshes(asset):
		var b: AABB = mi.global_transform * mi.get_aabb()
		_box = b if first else _box.merge(b)
		first = false
	# Floating assets (candy, clouds, hanging lanterns) have their origin at the centre or top:
	# lift them so they sit just above the lawn.
	if _box.position.y < -0.01:
		var lift := -_box.position.y + 0.25
		asset.position = Vector3(0, lift, 0)
		_box.position.y += lift
	# A warm porch-style light for the night views; a neutral studio key for texture checks.
	var warm := OmniLight3D.new()
	warm.light_color = Color(1.0, 0.58, 0.26)
	warm.light_energy = 1.6
	warm.omni_range = 6.0 + _box.size.length()
	_root.add_child(warm)
	warm.position = _box.get_center() + Vector3(-1.5, _box.size.y * 0.6 + 1.0, 2.0 + _box.size.z)
	_studio = DirectionalLight3D.new()
	_studio.light_color = Color(1.0, 0.97, 0.92)
	_studio.light_energy = 0.0
	_studio.shadow_enabled = true
	_root.add_child(_studio)
	_studio.global_transform = Transform3D(Basis.looking_at(Vector3(0.4, -0.8, -0.5).normalized(), Vector3.UP), Vector3.ZERO)
	_sheet = Image.create(SHEET.x, SHEET.y, false, Image.FORMAT_RGBA8)
	_view = 0
	_wait = 8


## Lawn plot (14 x 14 m) with a paver path, in the toon UV2 encoding (UV = metres, UV2 = layer + cell u, cell v,
## COLOR.r = AO 1), so materials are judged against the real ground; or a neutral grid floor.
func _ground(toon: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = "Ground"
	if toon and ground_uv2.x >= 0.0:
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		_quad(st, Rect2(-7, -7, 14, 14), 0.0, ground_uv2)
		if path_uv2.x >= 0.0:
			_quad(st, Rect2(-0.8, 2.2, 1.6, 4.8), 0.01, path_uv2)
		st.generate_tangents()
		mi.mesh = st.commit()
		mi.material_override = toon
	else:
		var plane := PlaneMesh.new()
		plane.size = Vector2(14, 14)
		mi.mesh = plane
		var grid := ShaderMaterial.new()
		grid.shader = FloorGrid
		mi.material_override = grid
	return mi


static func _quad(st: SurfaceTool, r: Rect2, y: float, cell: Vector3) -> void:
	var p := [Vector3(r.position.x, y, r.position.y), Vector3(r.end.x, y, r.position.y),
		Vector3(r.end.x, y, r.end.y), Vector3(r.position.x, y, r.end.y)]
	for i in [0, 1, 2, 0, 2, 3]:   # clockwise seen from above = front face in Godot
		var v: Vector3 = p[i]
		st.set_normal(Vector3.UP)
		st.set_color(Color.WHITE)
		st.set_uv(Vector2(v.x, v.z))
		st.set_uv2(Vector2(cell.x + cell.y, cell.z))
		st.add_vertex(v)


static func _apply_material_recursive(node: Node, mat: Material) -> void:
	if node is MeshInstance3D:
		(node as MeshInstance3D).material_override = mat
	for c in node.get_children():
		_apply_material_recursive(c, mat)


static func _meshes(node: Node) -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	_collect_meshes(node, out)
	return out


static func _collect_meshes(node: Node, out: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D:
		out.append(node as MeshInstance3D)
	for c in node.get_children():
		_collect_meshes(c, out)


func _process(_delta: float) -> void:
	if _sheet == null or _view >= VIEWS.size():
		return
	var v: Array = VIEWS[_view]
	var c := _box.get_center()
	var radius := maxf(_box.size.length() * 0.5, 0.5)
	var dist := radius / tan(deg_to_rad(_cam.fov * 0.5)) * 1.25
	var dir := Vector3(sin(v[0]) * cos(v[1]), sin(v[1]), cos(v[0]) * cos(v[1]))
	_cam.global_position = c + dir * dist
	_cam.look_at(c, Vector3.UP)
	_studio.light_energy = 1.3 if v[2] else 0.0
	_moon.light_energy = 0.25 if v[2] else 0.62
	_wait -= 1
	if _wait > 0:
		return
	var shot := get_viewport().get_texture().get_image()
	shot.convert(Image.FORMAT_RGBA8)
	shot.resize(TILE.x, TILE.y, Image.INTERPOLATE_LANCZOS)
	_sheet.blit_rect(shot, Rect2i(Vector2i.ZERO, TILE), Vector2i((_view % 2) * TILE.x, (_view / 2) * TILE.y))
	_view += 1
	_wait = 6
	if _view == VIEWS.size():
		var err := _sheet.save_png(capture_path)
		if err != OK:
			push_error("asset_preview: cannot write " + capture_path)
			get_tree().quit(1)
			return
		print("CAPTURED ", capture_path)
		get_tree().quit()
