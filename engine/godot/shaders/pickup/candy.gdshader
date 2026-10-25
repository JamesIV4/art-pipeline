// Origin: S:\Repos\trick-or-treat\game\shaders\candy.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Floating candy: spins and bobs per instance (phase in INSTANCE_CUSTOM.r), glossy, glows softly.
// Same UV2 encoding as toon.gdshader (layer + palette cell); falls back to UV for older meshes.
shader_type spatial;
render_mode cull_back;

uniform sampler2D palette : source_color, filter_nearest;
uniform sampler2D palette_emit : source_color, filter_nearest;
uniform float self_glow = 0.55;

void vertex() {
	float phase = INSTANCE_CUSTOM.r;
	float a = TIME * 1.7 + phase;
	mat2 r = mat2(vec2(cos(a), sin(a)), vec2(-sin(a), cos(a)));
	VERTEX.xz = r * VERTEX.xz;
	NORMAL.xz = r * NORMAL.xz;
	VERTEX.y += sin(TIME * 2.3 + phase) * 0.09;
}

void fragment() {
	vec2 cell = (UV2.x != 0.0 || UV2.y != 0.0) ? vec2(fract(UV2.x), UV2.y) : UV;
	vec3 c = texture(palette, cell).rgb;
	// Push the colour past the palette's pastel so candy reads as vivid sugar under night light;
	// the rim glows in the candy's own colour (not white) so pieces stay saturated at a distance.
	vec3 vivid = clamp(mix(vec3(dot(c, vec3(0.299, 0.587, 0.114))), c, 1.4), 0.0, 1.0);
	ALBEDO = vivid;
	EMISSION = vivid * self_glow + texture(palette_emit, cell).rgb * 3.0;
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.5);
	EMISSION += mix(vivid, vec3(1.0), 0.25) * rim * 0.7;
	ROUGHNESS = 0.22;
	SPECULAR = 0.8;
}
