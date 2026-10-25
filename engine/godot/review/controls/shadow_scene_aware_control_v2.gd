# Origin: S:\Repos\OpenXcom-Extended-3D\art\tools\shadow_scene_aware_control_v2.gd (imported 2026-10-25)
# Changes: the scene under test comes from --control-scene=res://... (default: application/run/main_scene) instead of the hard-coded res://tactical_level_viewer.tscn (_control_scene() added at the end). Control logic and the TACTICAL_* stdout lines (checked by CaptureGodotReview.ps1) unchanged.
# Diagnostic only. Includes actual aggregate bounds of native MultiMesh batches.
extends SceneTree

var lights: Array = []
var cameras: Array = []
var geometry: Array = []

func _initialize() -> void:
	var packed: PackedScene = load(_control_scene())
	var scene: Node = packed.instantiate()
	root.add_child(scene)
	current_scene = scene
	call_deferred("_control", scene)

func _find(node: Node) -> void:
	if node is DirectionalLight3D:
		lights.append(node)
	if node is Camera3D:
		cameras.append(node)
	if node is MeshInstance3D and node.mesh:
		geometry.append(node)
	if node is MultiMeshInstance3D and node.multimesh and node.multimesh.mesh:
		geometry.append(node)
	for child in node.get_children():
		_find(child)

func _control(scene: Node) -> void:
	_find(scene)
	assert(lights.size() == 1 and cameras.size() == 1 and geometry.size() > 0)
	var sun: DirectionalLight3D = lights[0]
	var camera: Camera3D = cameras[0]
	var inverse: Transform3D = camera.global_transform.affine_inverse()
	var maximum_depth: float = 0.0
	var batches: int = 0
	var instances: int = 0
	for node: Node3D in geometry:
		var bounds: AABB
		if node is MultiMeshInstance3D:
			bounds = node.multimesh.get_aabb()
			batches += 1
			instances += node.multimesh.instance_count
		else:
			bounds = node.mesh.get_aabb()
		for corner in range(8):
			var point: Vector3 = inverse * (node.global_transform * bounds.get_endpoint(corner))
			maximum_depth = maxf(maximum_depth, -point.z)
	var energy: float = sun.light_energy
	var transform: Transform3D = sun.global_transform
	var bias: float = sun.shadow_bias
	var normal_bias: float = sun.shadow_normal_bias
	var fade: float = sun.directional_shadow_fade_start
	var mode: int = sun.directional_shadow_mode
	assert(fade > 0.0 and fade <= 1.0)
	var coverage: float = minf(camera.far, maxf(24.0, (maximum_depth + 2.0) / fade))
	assert(coverage * fade >= maximum_depth + 1.999)
	sun.directional_shadow_max_distance = coverage
	assert(sun.shadow_enabled and sun.light_energy == energy and sun.global_transform == transform)
	assert(sun.shadow_bias == bias and sun.shadow_normal_bias == normal_bias)
	assert(sun.directional_shadow_fade_start == fade and sun.directional_shadow_mode == mode)
	print("TACTICAL_SHADOW_SCENE_CONTROL meshes=", geometry.size(), " batches=", batches,
		" batch_instances=", instances, " max_camera_depth=", maximum_depth,
		" distance=", coverage, " unfaded_depth=", coverage * fade,
		" full_actual_bounds_covered=true shadows_enabled=true energy_transform_bias_fade_mode_unchanged=true")

## The scene under test (art-pipeline port): --control-scene=res://... among the user args, else the project's main scene.
func _control_scene() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--control-scene="):
			return argument.trim_prefix("--control-scene=")
	return str(ProjectSettings.get_setting("application/run/main_scene", ""))