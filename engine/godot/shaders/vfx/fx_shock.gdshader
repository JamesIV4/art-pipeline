// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_shock.gdshader (imported 2026-10-25)
// Changes: the #include now uses the relative path "fx_common.gdshaderinc" (was res://oxp/fx/shaders/fx_common.gdshaderinc); code otherwise unchanged.
// Ground shock ring of an explosion: a flat quad (PlaneMesh, 1 m, scaled to the ring's full radius x 2) that
// bends the image behind it along an expanding ring and adds a faint hot rim. age / life per instance.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

#include "fx_common.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_linear, repeat_disable;
uniform float strength = 0.012;
instance uniform float age = 0.0;
instance uniform float life = 0.4;
instance uniform vec4 rim_color = vec4(1.0, 0.75, 0.45, 0.35);

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r = length(p);
	float ph = clamp(age / life, 0.0, 1.0);
	float R = mix(0.08, 1.0, 1.0 - pow(1.0 - ph, 3.0));
	float w = mix(0.035, 0.1, ph);
	float ring = exp(-pow((r - R) / w, 2.0) * 2.5) * (1.0 - ph) * step(r, 1.0);
	// the ring's outward direction on screen
	vec3 out_world = normalize(vec3(p.x, 0.0, p.y) + 1e-5);
	vec2 dir = normalize((VIEW_MATRIX * vec4(out_world, 0.0)).xy + 1e-5);
	vec2 off = vec2(dir.x, -dir.y) * ring * strength;
	vec3 bg = textureLod(screen_tex, SCREEN_UV - off, 0.0).rgb;
	ALBEDO = bg + rim_color.rgb * rim_color.a * ring * 0.5;
	// no ring drawn over the void (never-seen tiles show no ground for it to ripple)
	float vd = smoothstep(60.0, 120.0, fx_scene_depth(SCREEN_UV, INV_PROJECTION_MATRIX) + VERTEX.z);
	ALPHA = clamp(ring * 2.0, 0.0, 1.0) * (1.0 - vd);
}
