// Origin: S:\Repos\trick-or-treat\game\shaders\grass.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Lawn grass blades: root-to-tip gradient tinted per lot (MultiMesh instance colour), wind sway,
// per-clump brightness variation, soft translucency so lantern light glows through the tips.
shader_type spatial;
render_mode cull_disabled, specular_disabled;

uniform vec3 root_tint : source_color = vec3(0.35, 0.5, 0.42);
uniform vec3 tip_tint : source_color = vec3(1.25, 1.2, 0.95);
uniform float wind_strength = 0.09;

varying float blade_h;
varying float shade;
varying vec3 lot_color;

void vertex() {
	blade_h = UV.y;
	vec3 origin = MODEL_MATRIX[3].xyz;
	float n = fract(sin(dot(origin.xz, vec2(12.9898, 78.233))) * 43758.5453);
	shade = 0.8 + 0.35 * n;
	lot_color = COLOR.rgb;
	float w = sin(TIME * 1.6 + origin.x * 0.35 + origin.z * 0.2) * 0.6 + sin(TIME * 2.7 + n * 6.0) * 0.4;
	VERTEX.x += w * wind_strength * blade_h * blade_h;
	VERTEX.z += cos(TIME * 1.3 + origin.z * 0.3) * wind_strength * 0.6 * blade_h * blade_h;
}

void fragment() {
	vec3 base = lot_color * shade;
	ALBEDO = base * mix(root_tint, tip_tint, blade_h);
	ROUGHNESS = 0.9;
	BACKLIGHT = vec3(0.35) * blade_h;
	AO = mix(0.55, 1.0, blade_h);
	AO_LIGHT_AFFECT = 0.5;
}
