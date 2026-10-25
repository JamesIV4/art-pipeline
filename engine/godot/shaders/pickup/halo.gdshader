// Origin: S:\Repos\trick-or-treat\game\shaders\halo.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Additive camera-facing glow behind each candy. Colour from the MultiMesh instance colour.
shader_type spatial;
render_mode blend_add, unshaded, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform float strength = 0.85;

varying float phase;

void vertex() {
	phase = INSTANCE_CUSTOM.r;
	vec3 scale = vec3(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz), length(MODEL_MATRIX[2].xyz));
	mat4 bb = mat4(INV_VIEW_MATRIX[0] * scale.x, INV_VIEW_MATRIX[1] * scale.y, INV_VIEW_MATRIX[2] * scale.z, MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = VIEW_MATRIX * bb;
	VERTEX.y += sin(TIME * 2.3 + phase) * 0.09 / max(scale.y, 0.01);
}

void fragment() {
	vec2 d = UV - 0.5;
	float r = length(d) * 2.0;
	float a = pow(clamp(1.0 - r, 0.0, 1.0), 2.4);
	float tw = 0.85 + 0.15 * sin(TIME * 3.0 + phase * 3.0);
	ALBEDO = COLOR.rgb * a * strength * tw;
}
