// Origin: S:\Repos\trick-or-treat\game\shaders\toon.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Shared textured toon material for every mesh in the neighborhood.
//   UV  : material tiling coordinates in metres (projected per face)
//   UV2 : x = material layer + palette cell u (fract), y = palette cell v
//   COLOR.r : baked ambient occlusion
// The painted material (texture array slice) modulates the palette tint, so one siding texture
// serves every house colour. Glow comes from palette_emit (alpha = flicker). Soft two-band
// diffuse so shadows read as the blue night ambient and lantern light reads orange. Occluders
// between camera and player dither away. Meshes without UV2 fall back to the flat palette path.
shader_type spatial;
render_mode cull_back, specular_schlick_ggx;

uniform sampler2D palette : source_color, filter_nearest;
uniform sampler2D palette_emit : source_color, filter_nearest;
uniform sampler2DArray albedo_array : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray normal_array : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float layer_scale[32];
uniform float layer_strength[32];
uniform float layer_normal[32];
uniform float emit_strength = 2.6;
uniform float ramp_soft = 0.2;
uniform vec3 shadow_tint : source_color = vec3(0.55, 0.65, 1.0);
uniform float ao_strength = 0.85;
uniform vec3 cast_shadow_tint : source_color = vec3(0.42, 0.58, 1.0);
uniform float cast_shadow_fill = 0.32;

instance uniform float rim_strength = 0.0;
instance uniform vec3 rim_color : source_color = vec3(0.62, 0.76, 1.0);
instance uniform float glow_boost = 1.0;
instance uniform float flash = 0.0;
instance uniform vec3 hit_flash : source_color = vec3(0.0); // monster hit / telegraph glow
instance uniform float wind = 0.0;
instance uniform float keep_visible = 0.0; // 1: never dithered away by the player cutout (monsters)

global uniform vec3 cutout_from;
global uniform vec3 cutout_to;
global uniform float cutout_radius;

varying vec3 world_pos;
varying float seed;

float bayer4(vec2 p) {
	ivec2 i = ivec2(mod(p, 4.0));
	int idx = i.x + i.y * 4;
	const float m[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
	return (m[idx] + 0.5) / 16.0;
}

void vertex() {
	vec3 origin = MODEL_MATRIX[3].xyz;
	seed = fract(sin(dot(origin, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
	if (wind > 0.0) {
		float h = max(VERTEX.y, 0.0);
		float sway = sin(TIME * 1.3 + seed * 6.28 + origin.x * 0.15) * 0.5 + sin(TIME * 2.1 + seed * 3.1) * 0.25;
		VERTEX.x += sway * wind * h * h * 0.012;
		VERTEX.z += cos(TIME * 1.1 + seed * 4.0) * wind * h * h * 0.008;
	}
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	// Only things standing up above the player's feet can occlude; the ground never cuts out.
	if (cutout_radius > 0.0 && keep_visible < 0.5 && world_pos.y > cutout_to.y - 0.25) {
		vec3 seg = cutout_to - cutout_from;
		float len = length(seg);
		vec3 dir = seg / max(len, 0.001);
		float t = dot(world_pos - cutout_from, dir);
		float fade = 0.0;
		if (t > 0.0 && t < len - 1.1) {
			float radius = cutout_radius + (len - t) * 0.22;
			float r = length(world_pos - (cutout_from + dir * t));
			fade = smoothstep(radius, radius * 0.55, r);
		}
		fade = max(fade, smoothstep(3.6, 2.2, distance(world_pos, cutout_from)));
		if (fade > bayer4(FRAGCOORD.xy)) {
			discard;
		}
	}
	float layer = 0.0;
	vec2 cell = UV;
	if (UV2.x != 0.0 || UV2.y != 0.0) {
		layer = floor(UV2.x);
		cell = vec2(fract(UV2.x), UV2.y);
	}
	int li = clamp(int(layer), 0, 31);
	vec3 tint = texture(palette, cell).rgb;
	vec2 tuv = UV / max(layer_scale[li], 0.01);
	vec3 det = texture(albedo_array, vec3(tuv, layer)).rgb;
	ALBEDO = tint * mix(vec3(1.0), det * 2.0, layer_strength[li]);
	if (layer > 0.5) {
		NORMAL_MAP = texture(normal_array, vec3(tuv, layer)).rgb;
		NORMAL_MAP_DEPTH = layer_normal[li] * 1.4;
	}
	AO = mix(1.0, COLOR.r, ao_strength);
	AO_LIGHT_AFFECT = 0.35;
	vec4 e = texture(palette_emit, cell);
	float flick = 1.0 - e.a * (0.3 + 0.3 * sin(TIME * 9.0 + seed * 40.0) * sin(TIME * 5.3 + seed * 13.0));
	EMISSION = e.rgb * emit_strength * flick * glow_boost;
	EMISSION += flash * vec3(0.55, 0.48, 0.95);
	EMISSION += hit_flash;
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	EMISSION += rim_color * rim * rim_strength;
	ROUGHNESS = 0.8;
	SPECULAR = 0.3;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float ramp = smoothstep(-ramp_soft, ramp_soft, ndl);
	float lit = ramp * ATTENUATION;
	vec3 shade = LIGHT_COLOR * shadow_tint * 0.12 * (1.0 - ramp) * clamp(ATTENUATION + 0.4, 0.0, 1.0);
	// Cast shadows from the moon stay a soft blue rather than going dark: a cool fill where the surface
	// faces the light but is shadowed.
	if (LIGHT_IS_DIRECTIONAL) {
		shade += LIGHT_COLOR * cast_shadow_tint * cast_shadow_fill * ramp * (1.0 - ATTENUATION);
	}
	DIFFUSE_LIGHT += (LIGHT_COLOR * lit + shade) / PI;
	// Soft painterly highlight.
	vec3 h = normalize(LIGHT + VIEW);
	float spec = pow(max(dot(NORMAL, h), 0.0), 24.0) * 0.18 * ATTENUATION;
	SPECULAR_LIGHT += LIGHT_COLOR * spec;
}
