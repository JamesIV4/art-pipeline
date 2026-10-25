// Origin: S:\Repos\trick-or-treat\game\shaders\magic_trail.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Wispy purple magic smoke guiding the player to the houses. The mesh stores the trail centreline:
// VERTEX = centre point, TANGENT = path direction, NORMAL = a perpendicular, UV.x = distance along
// the path (m), UV.y = ribbon side (0/1), UV2.x = sheet index (0..2), UV2.y = fraction along the
// path (end fades). Three wide camera-facing sheets drift around the centreline in a slow swirl;
// layered scrolling noise carves them into soft flowing wisps. instance `fade` dims a visited branch.
shader_type spatial;
render_mode blend_mix, unshaded, cull_disabled, depth_draw_never, shadows_disabled, fog_disabled;

uniform float thickness = 0.8; // half-width of the widest sheet (m)
uniform float swirl = 0.28;
uniform float opacity = 0.36;
uniform float glow = 1.4;
uniform vec3 deep_purple : source_color = vec3(0.36, 0.14, 0.72);
uniform vec3 lilac : source_color = vec3(0.78, 0.55, 1.0);
instance uniform float fade = 1.0;
uniform sampler2D depth_tex : hint_depth_texture, filter_linear;

varying float side;
varying float u;
varying float sheet;
varying float frac;
varying float near_fade;

// Sine-free hash (Hoskins): stays smooth for the large inputs a long path and a long session give
// (sin-based hashes lose precision there and show up as blocky cells).
float hash2(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash2(i), hash2(i + vec2(1, 0)), f.x), mix(hash2(i + vec2(0, 1)), hash2(i + vec2(1, 1)), f.x), f.y);
}

float fbm(vec2 p) {
	float v = 0.0, a = 0.5;
	for (int i = 0; i < 4; i++) {
		v += vnoise(p) * a;
		p = p * 2.07 + vec2(3.1, 1.7);
		a *= 0.5;
	}
	return v;
}

void vertex() {
	u = UV.x;
	side = UV.y * 2.0 - 1.0;
	sheet = UV2.x;
	frac = UV2.y;
	vec3 T = normalize(TANGENT);
	vec3 N = normalize(NORMAL);
	vec3 B = normalize(cross(T, N));
	// Each sheet circles the centreline slowly, so the smoke seems to roll as it flows.
	float th = u * 0.55 + sheet * 2.094 + TIME * (0.45 + sheet * 0.12);
	vec3 c = VERTEX + (N * cos(th) + B * sin(th)) * swirl * (0.6 + 0.4 * sheet);
	c.y += sin(u * 0.4 + TIME * 0.6 + sheet) * 0.12;
	float half_width = thickness * (0.45 + 0.28 * sheet);
	vec3 world_c = (MODEL_MATRIX * vec4(c, 1.0)).xyz;
	vec3 view = normalize(CAMERA_POSITION_WORLD - world_c);
	vec3 tw = normalize((MODEL_MATRIX * vec4(T, 0.0)).xyz);
	vec3 sidev = normalize(cross(view, tw));
	near_fade = smoothstep(2.5, 9.0, distance(CAMERA_POSITION_WORLD, world_c));
	VERTEX = (inverse(MODEL_MATRIX) * vec4(world_c + sidev * side * half_width, 1.0)).xyz;
}

void fragment() {
	float x = side;
	float time = mod(TIME, 600.0);
	// Big slow billows plus finer curls, both flowing toward the destination.
	float billow = fbm(vec2(u * 0.4 - time * 0.32, x * 1.4 + sheet * 4.3 + time * 0.04));
	float curl = fbm(vec2(u * 0.9 - time * 0.6, x * 2.2 - time * 0.12 + sheet * 1.9));
	// Falls all the way to zero at the sheet's edges (no hard border).
	float edge = 1.0 - x * x;
	float across = exp(-x * x * 2.8) * edge * edge;
	float dens = smoothstep(0.28, 0.98, billow * 0.75 + curl * 0.4) * across;
	dens *= dens * (3.0 - 2.0 * dens); // extra-soft falloff into the night
	float ends = smoothstep(0.0, 0.08, frac) * smoothstep(1.0, 0.88, frac);
	// Soft intersection: fade out where a sheet dips into the ground or a wall, instead of a hard line.
	float scene_depth = texture(depth_tex, SCREEN_UV).r;
	vec4 sv = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, scene_depth, 1.0);
	float soft = smoothstep(0.0, 0.7, (-sv.z / sv.w) - (-VERTEX.z));
	float a = dens * opacity * (1.0 - sheet * 0.18) * ends * fade * near_fade * soft;
	ALBEDO = mix(deep_purple, lilac, clamp(curl * 1.2 * across, 0.0, 1.0)) * glow * (0.8 + 0.6 * dens);
	ALPHA = clamp(a, 0.0, 1.0);
}
