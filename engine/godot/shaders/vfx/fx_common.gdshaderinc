// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_common.gdshaderinc (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Shared helpers of the battlescape effects (oxp/fx). Every fx shader is unshaded: its light comes from the
// uniforms below, which fx_director.gd copies from the scene's sun and ambient light every frame, so the effects
// follow the render panel's lighting like the lit models do.

uniform sampler2D fx_depth : hint_depth_texture, filter_nearest, repeat_disable;
uniform float soft_distance = 0.6;          // metres over which a sprite fades out where it meets the scene
uniform vec3 sun_dir_view = vec3(0.0, 0.7, 0.7);   // toward the sun, view space
uniform vec3 sun_radiance = vec3(1.0);      // sun colour x energy (x the panel's smoke light)
uniform vec3 ambient_radiance = vec3(0.5);  // ambient colour x energy
uniform float fx_time = 0.0;                // fx_director's clock (s)
uniform float ambient_desat = 0.65;         // share of the ambient's tint smoke ignores (the blue fill turned grey smoke blue)
uniform float void_floor_y = 0.0;           // OpenXcom's view-level floor (m): the ground a sprite fades into over the void
uniform float void_fade = 0.9;              // metres above that floor over which sprites fade in, over the void
uniform float void_smoke = 0.5;             // share of a lit smoke / dust sprite's opacity kept over the void
uniform float void_blur = 3.0;              // extra flipbook mip level over the void: softer silhouettes on black

// Linear view depth of the opaque scene at a screen point (orthographic or perspective).
float fx_scene_depth(vec2 suv, mat4 inv_proj) {
	float d = textureLod(fx_depth, suv, 0.0).r;
	vec4 v = inv_proj * vec4(suv * 2.0 - 1.0, d, 1.0);
	return -v.z / v.w;
}

// Soft particles: 0 where the sprite touches the scene, 1 once it is soft_distance in front of it.
float fx_soft(vec2 suv, vec3 vertex_view, mat4 inv_proj) {
	if (soft_distance <= 0.001) {
		return 1.0;
	}
	return clamp((fx_scene_depth(suv, inv_proj) + vertex_view.z) / soft_distance, 0.0, 1.0);
}

// Over OpenXcom's void (never-seen tiles draw nothing, so there is no depth) a sprite has no ground to fade into and
// shows hard edges against the black, or a lower edge cut by nothing. There it fades into a virtual floor at
// floor_y instead, along the view ray, exactly as it fades into real ground; a low fog slab over never-seen tiles
// then hides nothing that should show. Returns the soft factor; void_out = 1 over the void, 0 over the scene.
float fx_void_floor(vec3 vertex_view, mat4 inv_view, mat4 proj, float floor_y) {
	vec3 wp = (inv_view * vec4(vertex_view, 1.0)).xyz;
	vec3 dv = proj[3][3] > 0.5 ? vec3(0.0, 0.0, -1.0) : normalize(vertex_view);
	vec3 dw = mat3(inv_view) * dv;
	return clamp((wp.y - floor_y) / max(-dw.y, 0.05) / max(void_fade, 0.01), 0.0, 1.0);
}

float fx_soft_void(vec2 suv, vec3 vertex_view, mat4 inv_proj, mat4 inv_view, mat4 proj, float floor_y, out float void_out) {
	float gap = fx_scene_depth(suv, inv_proj) + vertex_view.z;
	void_out = smoothstep(60.0, 120.0, gap);
	float soft = soft_distance <= 0.001 ? 1.0 : clamp(gap / soft_distance, 0.0, 1.0);
	return mix(soft, fx_void_floor(vertex_view, inv_view, proj, floor_y), void_out);
}

vec2 fx_atlas_uv(vec2 uv, float frame, float cols, float rows) {
	return (clamp(uv, vec2(0.002), vec2(0.998)) + vec2(mod(frame, cols), floor(frame / cols))) / vec2(cols, rows);
}

// Flipbook sample with blending between neighbouring frames (frame = 0 .. cols*rows-1, fractional).
vec4 fx_flipbook(sampler2D tex, vec2 uv, float frame, float cols, float rows) {
	float last = cols * rows - 1.0;
	frame = clamp(frame, 0.0, last);
	float f0 = floor(frame);
	vec4 a = texture(tex, fx_atlas_uv(uv, f0, cols, rows));
	vec4 b = texture(tex, fx_atlas_uv(uv, min(f0 + 1.0, last), cols, rows));
	return mix(a, b, frame - f0);
}

// The same with a mip bias (softer, blurrier frames).
vec4 fx_flipbook_bias(sampler2D tex, vec2 uv, float frame, float cols, float rows, float bias) {
	float last = cols * rows - 1.0;
	frame = clamp(frame, 0.0, last);
	float f0 = floor(frame);
	vec4 a = texture(tex, fx_atlas_uv(uv, f0, cols, rows), bias);
	vec4 b = texture(tex, fx_atlas_uv(uv, min(f0 + 1.0, last), cols, rows), bias);
	return mix(a, b, frame - f0);
}

// Looping flipbook (the last frame blends back into the first).
vec4 fx_flipbook_loop(sampler2D tex, vec2 uv, float frame, float cols, float rows) {
	float n = cols * rows;
	frame = mod(frame, n);
	float f0 = floor(frame);
	vec4 a = texture(tex, fx_atlas_uv(uv, f0, cols, rows));
	vec4 b = texture(tex, fx_atlas_uv(uv, mod(f0 + 1.0, n), cols, rows));
	return mix(a, b, frame - f0);
}

// Volumetric light map (Blender renders of the simulation): rgb = sqrt(light from the sprite's right, top, left),
// a = opacity. L = toward the light in the sprite's frame (x right, y up, z toward the viewer). Light from below,
// in front and behind is estimated from the three. Returns the sun's share, 0 .. ~1.
float fx_lightmap(vec4 lm, vec3 L) {
	vec3 m = lm.rgb * lm.rgb;
	float bottom = max(0.0, 1.0 - m.g) * 0.45 * lm.a + 0.05 * (m.r + m.b);
	float front = (m.r + m.g + m.b) * 0.42 + 0.08;
	float back = (1.0 - lm.a) * 0.75 + 0.18 * (m.r + m.b);
	vec3 w = abs(L);
	float s = (L.x > 0.0 ? m.r : m.b) * w.x + (L.y > 0.0 ? m.g : bottom) * w.y + (L.z > 0.0 ? front : back) * w.z;
	return s / max(w.x + w.y + w.z, 1e-3);
}

// Lit smoke colour (before the albedo): sun through the light map plus ambient with a little self-occlusion.
vec3 fx_smoke_light(vec4 lm, vec3 L_sprite) {
	vec3 m = lm.rgb * lm.rgb;
	float ao = clamp((m.r + m.g + m.b) * 0.8 + 0.3, 0.3, 1.0);
	vec3 amb = mix(ambient_radiance, vec3(dot(ambient_radiance, vec3(0.299, 0.587, 0.114))), ambient_desat);
	return sun_radiance * fx_lightmap(lm, L_sprite) + amb * ao;
}

// The sun direction in a camera-facing sprite turned by `rot` (radians, as the particle billboards turn it).
vec3 fx_sprite_light(float rot) {
	float c = cos(rot);
	float s = sin(rot);
	vec3 L = normalize(sun_dir_view);
	return vec3(c * L.x - s * L.y, s * L.x + c * L.y, L.z);
}

// Camera-facing quad corner in world space: centre + rotated corner * size (q = the QuadMesh vertex, -0.5..0.5).
vec3 fx_billboard(vec3 centre, vec2 q, float rot, float size, mat4 inv_view) {
	float c = cos(rot);
	float s = sin(rot);
	vec2 r = vec2(c * q.x + s * q.y, -s * q.x + c * q.y);
	return centre + (normalize(inv_view[0].xyz) * r.x + normalize(inv_view[1].xyz) * r.y) * size;
}

float fx_hash(float n) {
	return fract(sin(n * 12.9898) * 43758.5453);
}
