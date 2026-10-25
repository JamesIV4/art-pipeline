// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_glow.gdshader (imported 2026-10-25)
// Changes: the #include now uses the relative path "fx_common.gdshaderinc" (was res://oxp/fx/shaders/fx_common.gdshaderinc); code otherwise unchanged.
// Additive HDR glow sprite for GPUParticles3D (flash cores, embers, energy-weapon flashes). The shape is computed
// (a soft core with a wide halo), so there is no texture. COLOR = colour and fade (colour ramp), energy = HDR scale.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, skip_vertex_transform;

#include "fx_common.gdshaderinc"

uniform float energy = 6.0;
uniform float core = 18.0;     // core sharpness
uniform float halo = 0.35;     // halo share

void vertex() {
	float size = length(MODEL_MATRIX[0].xyz);
	vec3 world = fx_billboard(MODEL_MATRIX[3].xyz, VERTEX.xy, INSTANCE_CUSTOM.x, size, INV_VIEW_MATRIX);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	float r2 = dot(UV - 0.5, UV - 0.5) * 4.0;
	float shape = exp(-r2 * core) + halo * exp(-r2 * 3.5) * (1.0 - r2);
	shape = max(shape, 0.0);
	float vd;
	float soft = fx_soft_void(SCREEN_UV, VERTEX, INV_PROJECTION_MATRIX, INV_VIEW_MATRIX, PROJECTION_MATRIX, void_floor_y, vd);
	ALBEDO = COLOR.rgb * energy;
	ALPHA = clamp(shape * COLOR.a * soft, 0.0, 1.0);
}
