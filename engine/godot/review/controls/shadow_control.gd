# Origin: S:\Repos\OpenXcom-Extended-3D\art\tools\shadow_control.gd (imported 2026-10-25)
# Changes: the scene under test comes from --control-scene=res://... (default: application/run/main_scene) instead of the hard-coded res://tactical_level_viewer.tscn (_control_scene() added at the end). Control logic and the TACTICAL_* stdout lines (checked by CaptureGodotReview.ps1) unchanged.
# Test-only launcher. Production scene/rendering remains the unchanged C++ viewer.
extends SceneTree

func _initialize() -> void:
	var packed: PackedScene = load(_control_scene())
	var scene: Node = packed.instantiate()
	root.add_child(scene)
	current_scene = scene
	call_deferred("_apply_control", scene)

func _find_lights(node: Node, found: Array) -> void:
	if node is DirectionalLight3D:
		found.append(node)
	for child in node.get_children():
		_find_lights(child, found)

func _apply_control(scene: Node) -> void:
	var lights: Array = []
	_find_lights(scene, lights)
	assert(lights.size() == 1, "Expected exactly the native viewer's one directional light")
	var sun: DirectionalLight3D = lights[0]
	var original_enabled: bool = sun.shadow_enabled
	var original_energy: float = sun.light_energy
	var original_transform: Transform3D = sun.global_transform
	var mode := "off"
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--shadow-control="):
			mode = argument.trim_prefix("--shadow-control=")
	assert(mode == "off", "This diagnostic only disables the directional shadow in this process")
	sun.shadow_enabled = false
	assert(not sun.shadow_enabled and sun.light_energy == original_energy and sun.global_transform == original_transform)
	print("TACTICAL_SHADOW_CONTROL lights=1 prior_enabled=", original_enabled,
		" enabled=", sun.shadow_enabled, " energy_unchanged=true transform_unchanged=true",
		" bias=", sun.shadow_bias, " normal_bias=", sun.shadow_normal_bias)

## The scene under test (art-pipeline port): --control-scene=res://... among the user args, else the project's main scene.
func _control_scene() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--control-scene="):
			return argument.trim_prefix("--control-scene=")
	return str(ProjectSettings.get_setting("application/run/main_scene", ""))
