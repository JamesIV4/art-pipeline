// Origin: S:\Repos\trick-or-treat\game\shaders\post_fx.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Post effects Godot 4 has no built-in for, ported from the OpenXcom-Extended-3D battlescape
// (oxp/debug/post_fx.gdshader): sharpen and vignette on the 3D image only (a canvas layer above the
// 3D view, under the HUD), plus a tiny dither against 8-bit banding. No film grain.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear;
uniform float sharpen = 0.0;
uniform float vignette_strength = 0.0;
uniform float vignette_radius = 0.85;
uniform float vignette_softness = 0.45;
uniform vec4 vignette_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);

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
		float r = length(d) / length(vec2(0.5 * aspect, 0.5)); // 1 in the corners
		float inside = 1.0 - smoothstep(vignette_radius - vignette_softness, vignette_radius, r);
		c = mix(vignette_color.rgb, c, mix(1.0, inside, vignette_strength));
	}
	// Anti-banding dither, about +-0.5 of an 8-bit step (interleaved gradient noise, Jimenez 2014).
	float ign = fract(52.9829189 * fract(dot(FRAGCOORD.xy, vec2(0.06711056, 0.00583715))));
	c += (ign - 0.5) / 255.0;
	COLOR = vec4(c, 1.0);
}
