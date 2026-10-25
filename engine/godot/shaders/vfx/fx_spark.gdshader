// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_spark.gdshader (imported 2026-10-25)
// Changes: the #include now uses the relative path "fx_common.gdshaderinc" (was res://oxp/fx/shaders/fx_common.gdshaderinc); code otherwise unchanged.
// Velocity-stretched spark for GPUParticles3D with transform_align = Z-billboard + Y-to-velocity: the particle's
// Y axis runs along its velocity and its quad faces the camera, so the streak needs no billboarding here. The
// QuadMesh is long and thin with its head at the particle; scale over velocity shortens it as it slows down.
// COLOR = temperature over life (colour ramp), energy = HDR scale.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

#include "fx_common.gdshaderinc"

uniform float energy = 9.0;

void fragment() {
	float x = (UV.x - 0.5) * 2.0;
	float across = exp(-x * x * 5.0);
	float along = smoothstep(1.0, 0.75, UV.y) * smoothstep(0.0, 0.85, UV.y);   // UV.y 0 = top (head)
	float head = exp(-pow((UV.y - 0.12) * 6.0, 2.0)) * exp(-x * x * 3.0);
	float shape = clamp(across * (0.25 + 0.75 * (1.0 - UV.y)) * along + head, 0.0, 1.0);
	ALBEDO = COLOR.rgb * energy;
	// over the void sparks go out at the virtual floor (hidden ground does not stop them)
	float vd = smoothstep(60.0, 120.0, fx_scene_depth(SCREEN_UV, INV_PROJECTION_MATRIX) + VERTEX.z);
	float floor_k = mix(1.0, fx_void_floor(VERTEX, INV_VIEW_MATRIX, PROJECTION_MATRIX, void_floor_y), vd);
	ALPHA = clamp(shape * COLOR.a, 0.0, 1.0) * floor_k;
}
