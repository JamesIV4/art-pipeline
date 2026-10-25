// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\fx\shaders\fx_ribbon.gdshader (imported 2026-10-25)
// Changes: the #include now uses the relative path "fx_common.gdshaderinc" (was res://oxp/fx/shaders/fx_common.gdshaderinc); code otherwise unchanged.
// A velocity-stretched streak between two world points (tracer rounds, plasma trails, rocket exhaust): a QuadMesh
// (1 x 1) turned about the tail-to-head axis to face the camera, with rounded ends. Additive and HDR: a hot core
// line inside a coloured sheath, brightest at the head and fading to nothing at the tail.
// Instance uniforms: head / tail (world), width (m), core and sheath colour (rgb x a = energy), flicker 0..1.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, skip_vertex_transform;

#include "fx_common.gdshaderinc"

instance uniform vec3 head = vec3(0.0);
instance uniform vec3 tail = vec3(0.0, 0.0, 0.01);
instance uniform float width = 0.08;
instance uniform vec4 core_color = vec4(1.0, 0.95, 0.85, 4.0);
instance uniform vec4 sheath_color = vec4(1.0, 0.45, 0.1, 1.5);
instance uniform float tail_power = 1.6;     // how quickly the streak fades toward its tail
instance uniform float core_width = 18.0;    // larger = thinner core
instance uniform float sheath_falloff = 3.2; // larger = crisper outline
instance uniform float head_taper = 0.0;     // laser bolts: share of the length over which the front tapers to a point
instance uniform float tail_taper = 0.0;     // ... and the tail (0 / 0 = round caps: tracers, trails, exhaust)

varying float v_along;
varying float v_across;
varying float v_caps;      // segment length in half-widths

void vertex() {
	float along = VERTEX.y + 0.5;                  // 0 at the tail, 1 at the head
	vec3 axis = head - tail;
	float len = max(length(axis), 1e-4);
	vec3 ax = axis / len;
	vec3 to_cam = normalize(INV_VIEW_MATRIX[2].xyz);
	vec3 side = cross(ax, to_cam);
	side = length(side) < 1e-4 ? normalize(INV_VIEW_MATRIX[0].xyz) : normalize(side);
	// the quad runs half a width past each end, so both ends come out round
	float ext = width * 0.5;
	vec3 p = tail - ax * ext + ax * (len + 2.0 * ext) * along + side * VERTEX.x * width;
	v_along = (along * (len + 2.0 * ext) - ext) / len;
	v_across = VERTEX.x * 2.0;
	v_caps = len / max(width * 0.5, 1e-4);
	VERTEX = (VIEW_MATRIX * vec4(p, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	float x = v_across;
	if (tail_taper > 0.0) {
		// a comet: a hot head that tapers to a point over a short front, a long tapering tail; no caps
		float a = v_along;
		float ph = clamp((1.0 - a) / max(head_taper, 0.01), 0.0, 1.0);
		float pt = clamp(a / max(tail_taper, 0.01), 0.0, 1.0);
		float prof = pow(ph, 0.6) * pow(pt, 1.1) * step(0.0, a) * step(a, 1.0);
		float xs = x / max(prof, 0.03);
		float d2s = xs * xs + (prof < 0.03 ? 100.0 : 0.0);
		float hot = smoothstep(0.35, 0.85, a);                       // the white core sits toward the front
		float corez = exp(-d2s * core_width) * hot;
		float glow = exp(-d2s * sheath_falloff) * mix(0.25, 1.0, pt) + 0.25 * exp(-x * x * 2.0) * pt * ph;
		vec3 cc = core_color.rgb * core_color.a * corez + sheath_color.rgb * sheath_color.a * glow;
		float softc = clamp(fx_soft(SCREEN_UV, VERTEX, INV_PROJECTION_MATRIX) * 2.0, 0.0, 1.0);
		ALBEDO = cc;
		ALPHA = clamp(max(corez, glow * 0.85), 0.0, 1.0) * softc;
	} else {
	// round caps: distance from the segment, in half-widths
	float over = max(v_along - 1.0, 0.0) + max(-v_along, 0.0);
	float oc = over * v_caps;
	float d2 = x * x + oc * oc;
	float core = exp(-d2 * core_width);
	// a crisp-edged sheath with a soft bloom outside it (laser bolts), or a soft glow (tracers, trails, exhaust)
	float sheath = sheath_falloff > 7.5 ? (1.0 - smoothstep(0.5, 0.72, sqrt(d2))) + 0.22 * exp(-d2 * 2.0) : exp(-d2 * sheath_falloff);
	float along = clamp(v_along, 0.0, 1.0);
	float taper = pow(along, tail_power);
	float headb = smoothstep(0.7, 1.0, along);
	vec3 c = core_color.rgb * core_color.a * core * (0.35 + 0.65 * taper + 0.8 * headb)
		+ sheath_color.rgb * sheath_color.a * sheath * taper;
	float soft = clamp(fx_soft(SCREEN_UV, VERTEX, INV_PROJECTION_MATRIX) * 2.0, 0.0, 1.0);
	ALBEDO = c;
	ALPHA = clamp(max(core, sheath * 0.8) * max(taper, 0.25 * core), 0.0, 1.0) * soft;
	}
}
