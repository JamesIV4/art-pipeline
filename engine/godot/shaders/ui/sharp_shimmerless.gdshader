// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\hud\sharp_shimmerless.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
shader_type canvas_item;
// Sharp, shimmer-free scaling of pixel art to any size (the HUD's unit portrait, roster pictures and hand sprites).
// Ported from the Sharp-Shimmerless shader by Woohyun Kang, CC0-1.0 (public domain):
// https://github.com/Woohyun-Kang/Sharp-Shimmerless-Shader
// The algorithm: an area-overlap box filter. An output pixel that lies inside one source texel takes that texel exactly;
// one that straddles a texel edge blends the two by how much of it lies on each side. So at any (non-integer) size
// only the pixels on texel edges blend, and nothing shimmers while the size changes.
// This port: the scale comes from the real drawn size in device pixels (output_size, set by sprite_portrait.gd from the
// baked HUD); the blend is done by hand from the four nearest texels in linear light with premultiplied alpha (the
// repository's gamma-correct idea), so blended edge pixels keep their brightness and transparent texels leave no dark
// fringe. Downscaling (output smaller than the texture) falls back to plain bilinear.

uniform vec2 output_size = vec2(1.0);
varying vec4 v_modulate;

void vertex() {
	v_modulate = COLOR;   // the item's modulate and the vertex colour, applied after the blend
}

vec4 to_linear(vec4 c) {
	return vec4(pow(c.rgb, vec3(2.2)) * c.a, c.a);   // linear light, premultiplied
}

void fragment() {
	ivec2 isize = textureSize(TEXTURE, 0);
	vec2 tex_size = vec2(isize);
	vec2 scale = max(output_size / tex_size, vec2(1.0));
	vec2 texel = UV * tex_size;
	vec2 fl = floor(texel);
	vec2 s = fract(texel);
	vec2 region = 0.5 - 0.5 / scale;              // around the texel centre: this texel only
	vec2 centre_dist = s - 0.5;
	vec2 f = (centre_dist - clamp(centre_dist, -region, region)) * scale + 0.5;
	// bilinear between texel centres at (fl + f), blended by hand in linear light
	vec2 p = fl + f - 0.5;
	ivec2 i0 = ivec2(floor(p));
	vec2 w = p - floor(p);
	ivec2 hi = isize - ivec2(1);
	vec4 c00 = to_linear(texelFetch(TEXTURE, clamp(i0, ivec2(0), hi), 0));
	vec4 c10 = to_linear(texelFetch(TEXTURE, clamp(i0 + ivec2(1, 0), ivec2(0), hi), 0));
	vec4 c01 = to_linear(texelFetch(TEXTURE, clamp(i0 + ivec2(0, 1), ivec2(0), hi), 0));
	vec4 c11 = to_linear(texelFetch(TEXTURE, clamp(i0 + ivec2(1, 1), ivec2(0), hi), 0));
	vec4 top = mix(c00, c10, w.x);
	vec4 bottom = mix(c01, c11, w.x);
	vec4 c = mix(top, bottom, w.y);
	vec4 straight = c.a > 0.0001 ? vec4(pow(c.rgb / c.a, vec3(1.0 / 2.2)), c.a) : vec4(0.0);
	COLOR = straight * v_modulate;
}
