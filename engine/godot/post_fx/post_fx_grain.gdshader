// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\debug\post_fx.gdshader (imported 2026-10-25)
// Changes: renamed post_fx.gdshader -> post_fx_grain.gdshader (the XCOM original with film grain; trick-or-treat dropped the grain); code unchanged.
// Post effects Godot 4 has no built-in for (render debug panel, Ctrl+Alt+D): sharpen, vignette and
// film grain on the 3D image only (canvas layer 1: above the 3D view, under the HUD and OpenXcom's
// screen). Hidden at the shipped settings, so it costs nothing then.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear;
uniform float sharpen = 0.0;
uniform float vignette_strength = 0.0;
uniform float vignette_radius = 0.85;
uniform float vignette_softness = 0.45;
uniform vec4 vignette_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform float grain_amount = 0.0;
uniform float grain_size = 1.5;
uniform float grain_time = 0.0;

// Film grain (user 2026-10-07: the old fract(sin()) hash banded, patterned and crawled across the screen).
// pcg3d integer hash (Jarzynski & Olano, "Hash Functions for GPU Rendering", JCGT 2020): no lattice patterns;
// seeded by an integer frame index at film cadence (24 fps), so no float drift. Grain larger than a pixel
// is smooth value noise (no blocks); the per-pixel grain is lightly high-passed so it has no clumps
// (after Lottes, AMD GPUOpen "Fine Art of Film Grain"). Strongest in the midtones, lighter in deep shadows
// and highlights. A tiny interleaved-gradient-noise dither (Jimenez 2014) breaks 8-bit banding.
uvec3 pcg3d(uvec3 v) {
	v = v * 1664525u + 1013904223u;
	v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
	v ^= v >> 16u;
	v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
	return v;
}

float hash01(vec2 cell, uint frame) {
	return float(pcg3d(uvec3(uvec2(ivec2(cell) + ivec2(32768)), frame)).x) * (1.0 / 4294967296.0);
}

float grain_noise(vec2 px, float size, uint frame) {
	if (size <= 1.0) {
		vec2 p = floor(px);
		float n = hash01(p, frame) - 0.25 * (hash01(p + vec2(1.0, 0.0), frame) + hash01(p - vec2(1.0, 0.0), frame)
			+ hash01(p + vec2(0.0, 1.0), frame) + hash01(p - vec2(0.0, 1.0), frame));
		return n * 0.894;   // the 5-tap high-pass keeps unit-ish contrast (1 / sqrt(1.25))
	}
	vec2 cell = px / size;
	vec2 i = floor(cell);
	vec2 f = fract(cell);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = hash01(i, frame);
	float b = hash01(i + vec2(1.0, 0.0), frame);
	float c = hash01(i + vec2(0.0, 1.0), frame);
	float d = hash01(i + vec2(1.0, 1.0), frame);
	return (mix(mix(a, b, u.x), mix(c, d, u.x), u.y) - 0.5) * 1.6;   // interpolation lowers contrast; restore it
}

void fragment() {
	vec2 uv = SCREEN_UV;
	vec3 c = texture(screen_tex, uv).rgb;
	if (sharpen > 0.0) {
		vec2 px = SCREEN_PIXEL_SIZE;
		vec3 blur = (texture(screen_tex, uv + vec2(px.x, 0.0)).rgb + texture(screen_tex, uv - vec2(px.x, 0.0)).rgb
			+ texture(screen_tex, uv + vec2(0.0, px.y)).rgb + texture(screen_tex, uv - vec2(0.0, px.y)).rgb) * 0.25;
		c += (c - blur) * sharpen;
	}
	if (vignette_strength > 0.0) {
		float aspect = SCREEN_PIXEL_SIZE.y / SCREEN_PIXEL_SIZE.x;
		vec2 d = (uv - 0.5) * vec2(aspect, 1.0);
		float r = length(d) / length(vec2(0.5 * aspect, 0.5));   // 1 in the corners
		float inside = 1.0 - smoothstep(vignette_radius - vignette_softness, vignette_radius, r);
		c = mix(vignette_color.rgb, c, mix(1.0, inside, vignette_strength));
	}
	uint frame = uint(max(floor(grain_time * 24.0), 0.0));
	if (grain_amount > 0.0) {
		float n = grain_noise(FRAGCOORD.xy, max(grain_size, 0.5), frame);
		float lum = clamp(dot(c, vec3(0.2126, 0.7152, 0.0722)), 0.0, 1.0);
		float response = mix(0.3, 1.0, 4.0 * lum * (1.0 - lum));   // midtones strongest, like film
		c += vec3(n * grain_amount * response);
	}
	// anti-banding dither, about ±0.5 of an 8-bit step
	vec2 dp = FRAGCOORD.xy + 5.588238 * float(frame % 64u);
	float ign = fract(52.9829189 * fract(dot(dp, vec2(0.06711056, 0.00583715))));
	c += (ign - 0.5) / 255.0;
	COLOR = vec4(c, 1.0);
}
