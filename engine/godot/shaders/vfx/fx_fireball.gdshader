// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_fireball.gdshader (imported 2026-10-25)
// Changes: the #include now uses the relative path "fx_common.gdshaderinc" (was res://oxp/fx/shaders/fx_common.gdshaderinc); code otherwise unchanged.
// Fireball sprites of one explosion: a MultiMesh, one instance per OpenXcom sub-explosion (its own position and
// start delay), driven by the explosion's age. Two flipbooks of the same Mantaflow fireball: emission (rgb =
// sqrt(fire light over black), a = opacity) and the smoke light map (fx_common). The fire is HDR, so the glow
// post effect blooms it; the smoke part is lit by the scene's sun and ambient.
// INSTANCE_CUSTOM: x = start delay (s), y = life (s), z = seed, w = size (m). COLOR: rgb fire tint, a = fire energy.
shader_type spatial;
render_mode unshaded, blend_premul_alpha, depth_draw_never, cull_disabled, shadows_disabled, skip_vertex_transform;

#include "fx_common.gdshaderinc"

uniform sampler2D emission_tex : hint_default_transparent, filter_linear_mipmap, repeat_disable;
uniform sampler2D lightmap : hint_default_transparent, filter_linear_mipmap, repeat_disable;
uniform float emission_energy = 5.0;
uniform float hdr_boost = 2.0;
uniform vec3 smoke_albedo = vec3(0.06, 0.057, 0.054);
uniform float rise = 1.1;          // metres the sprite rises over its life
uniform float grow_from = 0.85;
uniform float grow_to = 1.25;
uniform float opacity = 1.0;
uniform float frame_end = 44.0;   // the flipbook's fire ends near frame 32; the blast's smoke column takes over
instance uniform float age = 0.0;
instance uniform float ground_y = 0.0;    // the blast's floor: over the void the sprites fade into it

varying float v_phase;
varying float v_rot;
varying float v_alive;

void vertex() {
	float t = age - INSTANCE_CUSTOM.x;
	float life = max(INSTANCE_CUSTOM.y, 0.01);
	v_alive = step(0.0, t) * step(t, life);
	float ph = clamp(t / life, 0.0, 1.0);
	v_phase = ph;
	float seed = INSTANCE_CUSTOM.z;
	v_rot = (seed - 0.5) * 6.2831853 + ph * (seed - 0.5) * 1.2;
	float size = INSTANCE_CUSTOM.w * mix(grow_from, grow_to, 1.0 - pow(1.0 - ph, 2.2)) * v_alive;
	vec3 centre = MODEL_MATRIX[3].xyz + vec3(0.0, rise * ph * (0.4 + 0.6 * ph), 0.0);
	vec3 world = fx_billboard(centre, VERTEX.xy, v_rot, size, INV_VIEW_MATRIX);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	if (v_alive < 0.5) {
		discard;
	}
	float vd;
	float soft = fx_soft_void(SCREEN_UV, VERTEX, INV_PROJECTION_MATRIX, INV_VIEW_MATRIX, PROJECTION_MATRIX, ground_y, vd);
	float frame = v_phase * frame_end;
	vec4 e = fx_flipbook_bias(emission_tex, UV, frame, 8.0, 8.0, void_blur * vd);
	vec4 lm = fx_flipbook_bias(lightmap, UV, frame, 8.0, 8.0, void_blur * vd);
	vec3 em = e.rgb * e.rgb;
	float lum = dot(em, vec3(0.3, 0.59, 0.11));
	// Hot cores approach yellow-white; cooler edges keep the flipbook's orange.
	// Preserve the emission mask, so the smoke phase never becomes luminous.
	vec3 hot = mix(em, vec3(lum), smoothstep(0.12, 0.65, lum) * 0.65);
	vec3 fire = hot * COLOR.rgb * COLOR.a * emission_energy * (1.0 + hdr_boost * lum * lum);
	float fade = 1.0 - smoothstep(0.6, 1.0, v_phase);
	float a = clamp(max(lm.a, e.a) * opacity * fade, 0.0, 1.0) * soft;
	// where it burns the sprite is fire, not lit smoke (lit smoke under the flame washes it out to salmon)
	vec3 smoke = smoke_albedo * fx_smoke_light(lm, fx_sprite_light(v_rot)) * (1.0 - smoothstep(0.02, 0.25, lum));
	// still-hot smoke stays warm (never the ambient's blue) and cools to neutral grey
	smoke *= mix(vec3(1.0), vec3(1.3, 1.04, 0.78), clamp(1.25 - 1.4 * v_phase, 0.0, 1.0));
	float ka = mix(1.0, void_smoke, vd);   // over the void: the glow stays, the dark smoke thins (no cut-out shapes)
	ALBEDO = fire * soft * soft * fade + smoke * a * ka;
	ALPHA = a * ka;
}
