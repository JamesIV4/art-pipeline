// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_smoke.gdshader (imported 2026-10-25)
// Changes: the #include now uses the relative path "fx_common.gdshaderinc" (was res://oxp/fx/shaders/fx_common.gdshaderinc); code otherwise unchanged.
// Lit smoke / dust / gas sprite for GPUParticles3D draw passes (a 1 m QuadMesh). The flipbook is a volumetric
// light map rendered from a Mantaflow smoke simulation (fx_common.gdshaderinc). Particle COLOR = albedo tint and
// opacity over life (the process material's colour ramp); INSTANCE_CUSTOM.x = sprite turn, .z = flipbook phase.
shader_type spatial;
render_mode unshaded, blend_premul_alpha, depth_draw_never, cull_disabled, shadows_disabled, skip_vertex_transform;

#include "fx_common.gdshaderinc"

uniform sampler2D lightmap : hint_default_transparent, filter_linear_mipmap, repeat_disable;
uniform float frames_x = 8.0;
uniform float frames_y = 8.0;
uniform float frame_start = 0.0;
uniform float frame_end = 63.0;
uniform vec3 albedo = vec3(0.62, 0.61, 0.60);
uniform float opacity = 1.0;
uniform vec3 inner_glow = vec3(0.0);   // emissive glow of fresh, hot smoke (multiplied by COLOR glow below)
uniform float warm_bias = 0.0;          // hot smoke: a warm tint early in life (the blast column)
uniform float erode = 0.0;             // wisps: noise erosion of the silhouette, growing over life (dust, smoke, gas)
uniform sampler2D noise_tex : filter_linear_mipmap, repeat_enable;

varying float v_rot;
varying float v_phase;
varying vec2 v_seed;

void vertex() {
	float size = length(MODEL_MATRIX[0].xyz);
	v_rot = INSTANCE_CUSTOM.x;
	v_phase = clamp(INSTANCE_CUSTOM.z, 0.0, 1.0);
	v_seed = MODEL_MATRIX[3].xz * 0.37;
	vec3 world = fx_billboard(MODEL_MATRIX[3].xyz, VERTEX.xy, v_rot, size, INV_VIEW_MATRIX);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	float vd;
	float soft = fx_soft_void(SCREEN_UV, VERTEX, INV_PROJECTION_MATRIX, INV_VIEW_MATRIX, PROJECTION_MATRIX, void_floor_y, vd);
	vec2 uv = UV;
	float breakup = 1.0;
	if (erode > 0.0) {
		float nx = texture(noise_tex, UV * 0.8 + v_seed + vec2(0.0, -fx_time * 0.03)).r - 0.5;
		float ny = texture(noise_tex, UV * 0.8 + v_seed.yx + vec2(0.37, 0.61 - fx_time * 0.025)).r - 0.5;
		uv += vec2(nx, ny) * erode * (0.08 + 0.1 * v_phase);
		float n = texture(noise_tex, UV * 1.6 + v_seed * 1.7 + vec2(0.0, -fx_time * 0.05)).r;
		float e = 0.1 + 0.4 * v_phase;
		breakup = mix(1.0, smoothstep(e - 0.15, e + 0.35, n) * 1.3, erode);
	}
	vec4 lm = fx_flipbook_bias(lightmap, uv, mix(frame_start, frame_end, v_phase), frames_x, frames_y, void_blur * vd + erode);
	vec3 col = albedo * COLOR.rgb * fx_smoke_light(lm, fx_sprite_light(v_rot));
	col *= mix(vec3(1.0), vec3(1.2, 1.02, 0.82), warm_bias * (1.0 - v_phase) * (1.0 - v_phase));
	col += inner_glow * pow(1.0 - v_phase, 10.0) * lm.a;
	float a = clamp(lm.a * breakup * COLOR.a * opacity, 0.0, 1.0) * soft * mix(1.0, void_smoke, vd);
	ALBEDO = col * a;
	ALPHA = a;
}
