// Origin: S:\Repos\trick-or-treat\game\shaders\fire_trail.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Fireball flame trail: a camera-facing ribbon through the ball's recent positions. UV.x runs 0 at
// the ball to 1 at the tail, UV.y across. Scrolling noise licks the flame's edges, the colour cools
// from a white-yellow core through orange to deep red, and the tail breaks up into wisps.
shader_type spatial;
render_mode blend_add, unshaded, cull_disabled, depth_draw_never, shadows_disabled, fog_disabled;

instance uniform float fade = 1.0;
uniform float intensity = 1.5;

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
		p = p * 2.03 + vec2(1.7, 9.2);
		a *= 0.5;
	}
	return v;
}

void fragment() {
	float t = mod(TIME, 300.0);
	float along = UV.x;
	float across = abs(UV.y * 2.0 - 1.0);
	// Turbulence streams backward along the trail and flickers across it.
	float n = fbm(vec2(along * 7.0 - t * 11.0, UV.y * 3.0 + t * 2.1));
	float lick = fbm(vec2(along * 9.0 - t * 14.0, UV.y * 5.0 - t * 2.3));
	float width = mix(0.9, 0.2, pow(along, 0.7));
	float edge = across + (n - 0.5) * 1.1 * (0.3 + along);
	float body = 1.0 - smoothstep(width * 0.25, width, edge);
	// Heat: hottest at the ball and the centre line, cooling toward the tail and edges.
	float heat = clamp((1.0 - along * 1.35) * (1.0 - across * 0.9) + (lick - 0.5) * 0.5, 0.0, 1.0);
	vec3 col = mix(vec3(0.55, 0.06, 0.02), vec3(1.0, 0.38, 0.06), smoothstep(0.1, 0.45, heat));
	col = mix(col, vec3(1.0, 0.72, 0.22), smoothstep(0.45, 0.75, heat));
	col = mix(col, vec3(1.0, 0.9, 0.6), smoothstep(0.85, 1.0, heat));
	// The tail tears into separate wisps.
	float wisps = smoothstep(0.2, 0.6, n + (1.0 - along) * 0.5);
	float a = body * wisps * pow(1.0 - along, 0.9) * fade;
	ALBEDO = col * intensity * (0.6 + heat);
	ALPHA = clamp(a, 0.0, 1.0);
}
