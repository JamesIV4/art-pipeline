# Origin: S:\Repos\trick-or-treat\game\scripts\post_fx.gd (imported 2026-10-25)
# Changes: preloads are relative to this folder (were res://scripts/contact_fx.gd, res://shaders/post_fx.gdshader);
#   the constants became @export vars with the same defaults; the WorldEnvironment / sun lookups are NodePaths
#   (defaults ../WorldEnvironment and ../Moon, i.e. the original get_parent().get_node_or_null(...) names);
#   optional film grain (film_grain > 0) switches to post_fx_grain.gdshader (the XCOM original) and animates
#   grain_time as XCOM's render_panel.gd did. With the defaults the behaviour is the trick-or-treat original.
extends Node
## Post-processing ported from the OpenXcom-Extended-3D battlescape's shipped render preset
## ("Latest 2", oxp/debug/shipped_render_defaults.gd): the depth-only small-radius AO compositor pass
## (contact_fx.gd) and the sharpen + vignette post shader (no film grain). The environment values
## (Filmic tonemap, glow levels, SSAO, SSIL) live in main.tscn; quality settings in project.godot.
## (art-pipeline: the environment values live in presets/env_*.tres, quality settings in
## presets/project_settings_rendering.md.)

const ContactFx := preload("contact_fx.gd")
const PostShader := preload("post_fx.gdshader")
const GrainShader := preload("post_fx_grain.gdshader")

@export var environment_path: NodePath = ^"../WorldEnvironment"
@export var sun_path: NodePath = ^"../Moon"
@export var sharpen := 0.27
@export var vignette := 0.5
@export var vignette_radius := 1.0
@export var vignette_soft := 0.45
@export var vignette_color := Color(0, 0, 0)
@export var depth_ao := true
@export var depth_ao_radius := 0.46
@export var depth_ao_intensity := 0.77
@export var depth_ao_half_res := false
@export var contact_shadows := false
## XCOM shipped grain: 0.015 at size 1.6 px (trick-or-treat: 0 = no grain, plain post_fx.gdshader).
@export var film_grain := 0.0
@export var grain_size := 1.6
## Canvas layer of the post rect: above the 3D view (layer 0 draws over it), under a HUD on layer >= 1.
@export var canvas_layer := 0
## SSAO quality Ultra at full resolution (RenderingServer side, no Environment property for it).
@export var ssao_ultra_full_res := true

var contact_fx: CompositorEffect
var post_material: ShaderMaterial
var _sun: DirectionalLight3D
var _grain_t := 0.0


func _ready() -> void:
	var env := get_node_or_null(environment_path) as WorldEnvironment
	_sun = get_node_or_null(sun_path) as DirectionalLight3D
	if env and RenderingServer.get_current_rendering_method() == "forward_plus" and (depth_ao or contact_shadows):
		contact_fx = ContactFx.new()
		contact_fx.set("ao_on", depth_ao)
		contact_fx.set("ao_radius", depth_ao_radius)
		contact_fx.set("ao_intensity", depth_ao_intensity)
		contact_fx.set("cs_on", contact_shadows)
		contact_fx.set("half_res", depth_ao_half_res)
		var comp := Compositor.new()
		comp.compositor_effects = [contact_fx]
		env.compositor = comp
	# Above the 3D view, under the HUD (layer 1).
	var layer := CanvasLayer.new()
	layer.layer = canvas_layer
	add_child(layer)
	var rect := ColorRect.new()
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = GrainShader if film_grain > 0.0 else PostShader
	mat.set_shader_parameter("sharpen", sharpen)
	mat.set_shader_parameter("vignette_strength", vignette)
	mat.set_shader_parameter("vignette_radius", vignette_radius)
	mat.set_shader_parameter("vignette_softness", vignette_soft)
	mat.set_shader_parameter("vignette_color", vignette_color)
	if film_grain > 0.0:
		mat.set_shader_parameter("grain_amount", film_grain)
		mat.set_shader_parameter("grain_size", grain_size)
	rect.material = mat
	post_material = mat
	layer.add_child(rect)
	# Quality settings from the preset that are server-side (SSAO Ultra at full resolution).
	if ssao_ultra_full_res:
		RenderingServer.environment_set_ssao_quality(RenderingServer.ENV_SSAO_QUALITY_ULTRA, false,
			float(ProjectSettings.get_setting("rendering/environment/ssao/adaptive_target", 0.5)),
			int(ProjectSettings.get_setting("rendering/environment/ssao/blur_passes", 2)),
			float(ProjectSettings.get_setting("rendering/environment/ssao/fadeout_from", 50.0)),
			float(ProjectSettings.get_setting("rendering/environment/ssao/fadeout_to", 300.0)))


func _process(delta: float) -> void:
	if contact_fx and _sun:
		contact_fx.set("sun_dir", _sun.global_transform.basis.z)
	if film_grain > 0.0 and post_material:
		_grain_t += delta
		post_material.set_shader_parameter("grain_time", fmod(_grain_t, 100.0))
