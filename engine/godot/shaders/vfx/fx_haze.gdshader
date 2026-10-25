// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_haze.gdshader (imported 2026-10-25)
// Changes: the #include now uses the relative path "fx_common.gdshaderinc" (was res://oxp/fx/shaders/fx_common.gdshaderinc); code otherwise unchanged.
// Heat haze over burning tiles: upright camera-facing quads (one per burning tile, MultiMesh) that ripple the
// image behind them with rising noise. Instance as fx_tile_fire (origin on the floor, x = width, y = height);
// COLOR.a = strength.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, skip_vertex_transform;

#include "fx_common.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_linear, repeat_disable;
uniform sampler2D noise_tex : filter_linear_mipmap, repeat_enable;
uniform float strength = 0.004;
uniform float max_level_y = 1000.0;

varying float v_strength;
varying float v_seed;

void vertex() {
	vec3 base = MODEL_MATRIX[3].xyz;
	v_strength = COLOR.a * step(base.y, max_level_y);
	v_seed = INSTANCE_CUSTOM.x;
	float w = length(MODEL_MATRIX[0].xyz);
	float h = length(MODEL_MATRIX[1].xyz);
	vec3 cam_right = INV_VIEW_MATRIX[0].xyz;
	vec3 right = normalize(vec3(cam_right.x, 0.0, cam_right.z) + vec3(1e-4, 0.0, 0.0));
	vec3 world = base + right * VERTEX.x * w + vec3(0.0, (VERTEX.y + 0.5) * h, 0.0);
	world = mix(base, world, step(0.002, v_strength));
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	vec2 n = texture(noise_tex, UV * vec2(1.0, 1.6) + vec2(v_seed, -fx_time * 0.55)).rg - 0.5;
	float mask = sin(UV.x * 3.14159) * smoothstep(1.0, 0.55, UV.y) * smoothstep(0.0, 0.5, UV.y);
	vec2 off = n * strength * mask * v_strength;
	ALBEDO = textureLod(screen_tex, SCREEN_UV + off, 0.0).rgb;
	ALPHA = clamp(mask * v_strength * 4.0, 0.0, 1.0);
}
