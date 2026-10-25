// Origin: S:\Repos\trick-or-treat\game\shaders\candy_beam.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// A soft column of light under each candy, in the candy's colour: a flat strip that turns about the
// vertical to face the camera (not a 3D cylinder), widest where it rises from the ground and
// tapering and fading as it climbs past the candy. Where it meets the ground (or a roof) it fades in
// softly instead of showing a hard line. Colour: the MultiMesh instance colour, times `beam_tint`
// (set per node for candy that isn't in a MultiMesh).
shader_type spatial;
render_mode blend_add, unshaded, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform float strength = 0.18;
uniform sampler2D depth_tex : hint_depth_texture, filter_linear;
instance uniform vec3 beam_tint : source_color = vec3(1.0);

varying float shimmer;

void vertex() {
	vec3 origin = MODEL_MATRIX[3].xyz;
	vec3 sc = vec3(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz), length(MODEL_MATRIX[2].xyz));
	vec3 to_cam = CAMERA_POSITION_WORLD - origin;
	to_cam.y = 0.0;
	vec3 fwd = length(to_cam) > 0.001 ? normalize(to_cam) : vec3(0.0, 0.0, 1.0);
	vec3 right = vec3(fwd.z, 0.0, -fwd.x);
	mat4 bb = mat4(vec4(right * sc.x, 0.0), vec4(0.0, sc.y, 0.0, 0.0), vec4(fwd * sc.z, 0.0), vec4(origin, 1.0));
	MODELVIEW_MATRIX = VIEW_MATRIX * bb;
	shimmer = fract(sin(dot(origin.xz, vec2(12.9898, 78.233))) * 43758.5453) * 6.28;
}

void fragment() {
	float u = UV.x * 2.0 - 1.0;
	float h = 1.0 - UV.y; // 0 at the bottom, 1 at the top
	// The strip ends just below the candy (it never overlaps it): narrower where it rises from the
	// ground, widening toward the top, then fading out before it reaches the candy. Every edge fades
	// to nothing: the sides by shape, the top and bottom by ramps, and any surface it passes through
	// by depth below.
	float width = mix(0.42, 0.7, smoothstep(0.0, 0.85, h)); // never comes to a point
	float across = exp(-(u * u) / (width * width) * 2.2) * (1.0 - u * u);
	float along = mix(0.45, 1.0, smoothstep(0.0, 0.8, h)) * smoothstep(0.0, 0.3, h) * (1.0 - smoothstep(0.84, 1.0, h));
	float t = mod(TIME, 600.0);
	float flicker = 0.85 + 0.15 * sin(t * 2.2 + shimmer + h * 6.0);
	// Soft where the strip meets whatever it stands on.
	float scene = texture(depth_tex, SCREEN_UV).r;
	vec4 sv = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, scene, 1.0);
	float gap = (-sv.z / max(abs(sv.w), 1e-5)) - (-VERTEX.z);
	float soft = (gap == gap) ? smoothstep(0.0, 0.35, gap) : 0.0; // NaN-safe; a soft ramp, so surfaces never cut it with a line
	vec3 tint = COLOR.rgb * beam_tint;
	ALBEDO = max(tint * across * along * flicker * clamp(soft, 0.0, 1.0) * strength, vec3(0.0));
}
