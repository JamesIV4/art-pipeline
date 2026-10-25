// Origin: S:\Repos\trick-or-treat\game\shaders\candy_outline.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Glowing outline around every candy (second pass of candy.gdshader): an inflated back-face shell
// that follows the same spin and bob, tinted per candy (INSTANCE_CUSTOM.gba), pulsing softly.
shader_type spatial;
render_mode cull_front, unshaded, shadows_disabled, fog_disabled;

uniform float thickness = 0.03;
uniform float glow = 2.6;
// Pieces that aren't MultiMesh instances (spilled and dropped candy) set this instead.
instance uniform vec3 outline_tint : source_color = vec3(1.0, 0.8, 0.35);

varying vec3 tint;
varying float pulse;

void vertex() {
	float phase = INSTANCE_CUSTOM.r;
	tint = dot(INSTANCE_CUSTOM.gba, vec3(1.0)) > 0.01 ? INSTANCE_CUSTOM.gba : outline_tint;
	pulse = 0.8 + 0.2 * sin(TIME * 3.2 + phase * 2.0);
	float a = TIME * 1.7 + phase;
	mat2 r = mat2(vec2(cos(a), sin(a)), vec2(-sin(a), cos(a)));
	VERTEX.xz = r * VERTEX.xz;
	NORMAL.xz = r * NORMAL.xz;
	float s = max(length(MODEL_MATRIX[0].xyz), 0.01);
	vec3 dir = normalize(mix(normalize(VERTEX + vec3(0.0001)), NORMAL, 0.35));
	VERTEX += dir * thickness / s;
	VERTEX.y += sin(TIME * 2.3 + phase) * 0.09;
}

void fragment() {
	ALBEDO = tint;
	EMISSION = tint * glow * pulse;
}
