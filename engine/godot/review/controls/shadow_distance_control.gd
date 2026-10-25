# Origin: S:\Repos\OpenXcom-Extended-3D\art\tools\shadow_distance_control.gd (imported 2026-10-25)
# Changes: the scene under test comes from --control-scene=res://... (default: application/run/main_scene) instead of the hard-coded res://tactical_level_viewer.tscn (_control_scene() added at the end). Control logic and the TACTICAL_* stdout lines (checked by CaptureGodotReview.ps1) unchanged.
# Diagnostic-only shadow range test; original geometry/material/light energy stay.
extends SceneTree

func _initialize() -> void:
	var packed: PackedScene = load(_control_scene())
	var scene: Node = packed.instantiate()
	root.add_child(scene)
	current_scene = scene
	call_deferred("_control", scene)

func _find(node: Node, lights: Array) -> void:
	if node is DirectionalLight3D:
		lights.append(node)
	for child in node.get_children():
		_find(child, lights)

func _control(scene: Node) -> void:
	var lights: Array = []
	_find(scene, lights)
	assert(lights.size() == 1)
	var sun: DirectionalLight3D = lights[0]
	var prior: float = sun.directional_shadow_max_distance
	var energy: float = sun.light_energy
	var transform: Transform3D = sun.global_transform
	var bias: float = sun.shadow_bias
	var normal_bias: float = sun.shadow_normal_bias
	sun.directional_shadow_max_distance = 24.0
	assert(sun.shadow_enabled and sun.light_energy == energy and sun.global_transform == transform)
	assert(sun.shadow_bias == bias and sun.shadow_normal_bias == normal_bias)
	print("TACTICAL_SHADOW_DISTANCE_CONTROL prior=", prior, " distance=24.0 shadows_enabled=true energy_transform_bias_unchanged=true")

## The scene under test (art-pipeline port): --control-scene=res://... among the user args, else the project's main scene.
func _control_scene() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--control-scene="):
			return argument.trim_prefix("--control-scene=")
	return str(ProjectSettings.get_setting("application/run/main_scene", ""))