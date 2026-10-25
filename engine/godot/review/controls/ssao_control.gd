# Origin: S:\Repos\OpenXcom-Extended-3D\art\tools\ssao_control.gd (imported 2026-10-25)
# Changes: the scene under test comes from --control-scene=res://... (default: application/run/main_scene) instead of the hard-coded res://tactical_level_viewer.tscn (_control_scene() added at the end). Control logic and the TACTICAL_* stdout lines (checked by CaptureGodotReview.ps1) unchanged.
# Single-variable process-local diagnostic; never a production/art workaround.
extends SceneTree

func _initialize() -> void:
	var packed: PackedScene = load(_control_scene())
	var scene: Node = packed.instantiate()
	root.add_child(scene)
	current_scene = scene
	call_deferred("_apply_control", scene)

func _find(node: Node, environments: Array, lights: Array) -> void:
	if node is WorldEnvironment:
		environments.append(node)
	if node is DirectionalLight3D:
		lights.append(node)
	for child in node.get_children():
		_find(child, environments, lights)

func _apply_control(scene: Node) -> void:
	var environments: Array = []
	var lights: Array = []
	_find(scene, environments, lights)
	assert(environments.size() == 1 and lights.size() == 1)
	var environment: Environment = environments[0].environment
	var sun: DirectionalLight3D = lights[0]
	var energy := sun.light_energy
	var transform := sun.global_transform
	var shadows := sun.shadow_enabled
	var ambient := environment.ambient_light_energy
	var tone := environment.tonemap_mode
	var prior := environment.ssao_enabled
	assert(prior and shadows, "Use the unchanged normal viewer baseline")
	environment.ssao_enabled = false
	assert(not environment.ssao_enabled and sun.shadow_enabled == shadows)
	assert(sun.light_energy == energy and sun.global_transform == transform)
	assert(environment.ambient_light_energy == ambient and environment.tonemap_mode == tone)
	print("TACTICAL_SSAO_CONTROL prior_enabled=", prior, " enabled=", environment.ssao_enabled,
		" shadow_enabled=", sun.shadow_enabled, " energy_transform_ambient_tone_unchanged=true",
		" original_radius=", environment.ssao_radius, " original_intensity=", environment.ssao_intensity)

## The scene under test (art-pipeline port): --control-scene=res://... among the user args, else the project's main scene.
func _control_scene() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--control-scene="):
			return argument.trim_prefix("--control-scene=")
	return str(ProjectSettings.get_setting("application/run/main_scene", ""))