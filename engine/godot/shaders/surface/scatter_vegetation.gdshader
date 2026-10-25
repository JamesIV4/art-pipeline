// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\x-com--ufo-defense-3d\assets\shaders\scatter_vegetation.gdshader (imported 2026-10-25)
// Changes: added `uniform bool use_visibility = false` gating the OpenXcom per-tile visibility texture block in
//   fragment() (vis_tex discard + shade + unseen darkening); with it off (the new default) the cards render as plain
//   lit foliage. Set use_visibility = true to get the original XCOM behaviour. Everything else unchanged
//   (burn_tex is already gated by burn_on; trample needs the host to fill actors[] / actor_count).
// Scattered vegetation cards (assets/shared_materials/vegetation.json; built at runtime by the
// presenter's oxp/vegetation_layer.gd into MultiMesh chunks). One card cross per instance; the
// instance transform carries position, yaw, width and height. INSTANCE_CUSTOM:
//   x atlas cell index, y colour variation 0..1, z sway phase, w how surrounded by its own type (0..1).
// Shading for grass cards: the lighting normal is bent toward the ground normal (up) so the
// thin double-sided cards shade like a tuft and not like a wall, a translucency term lets the
// sun through the blades, a root-to-tip gradient darkens the base, and every instance has its
// own hue / brightness so a field is not one flat green. The tips sway in the wind.
// Visibility and light come straight from terrain_layer's per-tile visibility texture (R shade,
// G visible now, B floor discovered), so never-seen tiles show nothing and explored-but-unseen
// tiles darken as the overlay does.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D atlas : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec2 atlas_grid = vec2(2.0, 2.0);     // cells across, down
uniform vec4 tint : source_color = vec4(1.0);
uniform float cutoff = 0.42;
uniform float roughness = 0.85;
uniform float specular = 0.25;
uniform float translucency = 0.45;            // light through the blades (BACKLIGHT)
uniform float normal_bend = 0.7;              // 0 = card normal, 1 = ground normal
uniform float tip_light = 0.12;               // brightening toward the tip
uniform float root_dark = 0.5;                // darkening at the root (ambient occlusion of the tuft)
uniform float root_dark_sparse = 0.0;         // the same where the type's field is thin (a lone tuft is lit, not buried)
uniform float base_lift = 0.0;                // 0..1: lifts the atlas's own near-black base toward base_floor
uniform float base_floor = 0.07;              // linear luminance the lower blades are lifted to
uniform float value_gain = 1.0;               // overall brightness (e.g. dark blue blossoms)
uniform float desaturate = 0.0;               // 1 = the atlas's own colour removed (dead, dried tufts take the tint)
uniform float hue_variation = 0.08;           // per-instance yellow <-> blue shift
uniform float value_variation = 0.22;         // per-instance darker / lighter
uniform float wind = 0.5;                     // sway amplitude (metres at the tip, x wind_gust)
uniform float wind_speed = 1.1;
uniform vec4 tip_tint : source_color = vec4(1.0); // colour the upper blades blend toward (dry seed heads)
uniform float tip_mix = 0.0;                  // 0 = none, 1 = the tips take tip_tint fully
uniform float tip_start = 0.55;               // card height (0 root .. 1 tip) where the tip colour begins

// trample (vegetation_layer.set_actors): xyz a unit's feet, w the radius; grass inside is pressed down
uniform vec4 actors[48];
uniform int actor_count = 0;
uniform float trample_height = 0.22;          // remaining height at the centre (x the card's height)
uniform float trample_push = 0.35;            // metres the tips are pushed away at the centre

// blast scars (terrain_layer.add_blast_scar, 2026-10-13): the grass inside is burnt away, charred stubble along the edge.
// burn_tex: the map's burn mask (terrain_layer: every scar painted into it with the scar decal's shape, any number of
// them), map-sized in x / z, one colour channel per level (R level 0, G 1, B 2).
uniform sampler2D burn_tex : filter_linear, repeat_disable;
uniform float burn_on = 0.0;

// visibility (terrain_layer.gd): R shade * 17, G visible now, B floor discovered
uniform bool use_visibility = false;          // art-pipeline port: off = no OpenXcom visibility texture
uniform sampler3D vis_tex : filter_linear, repeat_disable;
uniform vec3 map_size = vec3(1.0);
uniform float tile_size = 2.0;
uniform float light_strength = 1.0;
uniform float light_curve = 1.0;
uniform float light_min = 0.0;
uniform float unseen_strength = 0.67;
uniform int debug_view = 0;                   // 1 = height factor, 2 = colour variation

instance uniform float veg_level = 0.0;       // the chunk's map level

varying vec3 world_pos;
varying vec2 cell_uv;
varying float root;                           // 0 root .. 1 tip
varying vec4 inst;
varying float burn;                           // 0 untouched .. 1 charred stubble at a blast scar's edge




void vertex() {
	inst = INSTANCE_CUSTOM;
	root = UV.y;   // card UV: y 1 at the root (bottom of the atlas cell), 0 at the tip
	float cell = inst.x;
	vec2 cells = atlas_grid;
	vec2 c = vec2(mod(cell, cells.x), floor(cell / cells.x));
	cell_uv = (c + UV) / cells;
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float tip = 1.0 - UV.y;
	float t = TIME * wind_speed + inst.z * 6.2831 + wp.x * 0.35 + wp.z * 0.27;
	float gust = 0.6 + 0.4 * sin(TIME * 0.37 + wp.x * 0.05 + wp.z * 0.08);
	vec2 sway = vec2(sin(t), cos(t * 0.8 + 1.3)) * wind * gust * 0.08 * tip * tip;
	wp.xz += sway;
	// trample: pressed down and bent away near units (the instance root is its origin)
	vec3 rootp = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float press = 0.0;
	vec2 away = vec2(0.0);
	for (int a = 0; a < actor_count; a++) {
		vec4 ac = actors[a];
		vec2 dxz = rootp.xz - ac.xz;
		float dist = length(dxz);
		if (abs(rootp.y - ac.y) < 1.2 && dist < ac.w) {
			float f = smoothstep(ac.w, ac.w * 0.35, dist);
			if (f > press) {
				press = f;
				away = dist > 0.001 ? dxz / dist : vec2(1.0, 0.0);
			}
		}
	}
	if (press > 0.0) {
		wp.y = rootp.y + (wp.y - rootp.y) * mix(1.0, trample_height, press);
		wp.xz += away * trample_push * press * tip;
	}
	// blast scars: inside the scar the tuft is gone (collapsed to its root), along the edge a short charred stubble
	burn = 0.0;
	if (burn_on > 0.5) {
		vec4 bm = textureLod(burn_tex, rootp.xz / tile_size / map_size.xy, 0.0);
		int lv = int(veg_level + 0.5);
		burn = clamp(lv == 0 ? bm.r : (lv == 1 ? bm.g : (lv == 2 ? bm.b : 0.0)), 0.0, 1.0);
	}
	if (burn > 0.0) {
		if (burn > 0.82) {
			wp = rootp;   // burnt away
		} else {
			wp.y = rootp.y + (wp.y - rootp.y) * mix(1.0, 0.22, smoothstep(0.0, 0.82, burn));
		}
	}
	world_pos = wp;
	VERTEX = (inverse(MODEL_MATRIX) * vec4(wp, 1.0)).xyz;
}


void fragment() {
	vec4 tex = texture(atlas, cell_uv);
	ALPHA = tex.a;
	ALPHA_SCISSOR_THRESHOLD = cutoff;

	// per-instance colour: a yellow <-> blue hue drift and a value drift
	float h = inst.y * 2.0 - 1.0;
	vec3 shift = vec3(1.0 + hue_variation * h, 1.0 + hue_variation * 0.4 * h, 1.0 - hue_variation * h);
	float val = 1.0 + value_variation * (fract(inst.y * 7.31) * 2.0 - 1.0);
	// inst.w: how surrounded the instance is by its own type (0 lone .. 1 inside a full field)
	float rd = mix(root_dark_sparse, root_dark, clamp(inst.w, 0.0, 1.0));
	float grad = mix(1.0 - rd, 1.0 + tip_light, 1.0 - root);
	vec3 base_col = mix(tex.rgb, vec3(dot(tex.rgb, vec3(0.2126, 0.7152, 0.0722))), desaturate);
	if (base_lift > 0.0) {
		// the atlas's dark lower blades: lift them toward base_floor, most at the root, none at the tip
		float lum0 = max(dot(base_col, vec3(0.2126, 0.7152, 0.0722)), 0.004);
		float lift = min(max(base_floor / lum0, 1.0), 3.0);
		base_col *= mix(1.0, lift, base_lift * smoothstep(0.35, 1.0, root));
	}
	vec3 color = base_col * tint.rgb * shift * val * grad * value_gain;
	// dry seed heads: the upper blades blend toward a straw colour (keeping the texture's own shading)
	float tipw = smoothstep(tip_start, 1.0, 1.0 - root) * tip_mix * (0.6 + 0.4 * fract(inst.y * 3.7));
	float lum = dot(tex.rgb, vec3(0.3, 0.59, 0.11));
	color = mix(color, tip_tint.rgb * lum * 2.2 * val, tipw);
	// singed by a blast: blackened stubble with brown-orange scorched tips
	if (burn > 0.0) {
		vec3 singed = mix(vec3(0.025, 0.02, 0.016), vec3(0.16, 0.08, 0.03) * (0.5 + lum), 1.0 - root);
		color = mix(color, singed, smoothstep(0.0, 0.6, burn));
	}

	// visibility / light of the floor under the card
	if (use_visibility) {
		vec3 uvw = vec3(world_pos.xz / tile_size / map_size.xy, (veg_level + 0.5) / map_size.z);
		vec4 v = texture(vis_tex, uvw);
		if (v.b < 0.5) {
			discard;
		}
		float shade = v.r * 255.0 / 17.0;
		float light_a = clamp(min(pow(clamp(shade / 16.0, 0.0, 1.0), light_curve) * 0.9 * light_strength, 1.0 - light_min), 0.0, 1.0);
		float unseen = (1.0 - v.g) * unseen_strength;
		color *= (1.0 - light_a) * (1.0 - unseen);
	}

	ALBEDO = color;
	ROUGHNESS = roughness;
	SPECULAR = specular;
	METALLIC = 0.0;
	BACKLIGHT = vec3(translucency);
	// bent normal: the card's normal faces the viewer, blended toward the ground normal (world up)
	vec3 n = FRONT_FACING ? NORMAL : -NORMAL;
	vec3 up = normalize((VIEW_MATRIX * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
	NORMAL = normalize(mix(n, up, normal_bend));

	if (debug_view == 1) {
		ALBEDO = vec3(inst.w);
	} else if (debug_view == 2) {
		ALBEDO = vec3(inst.y, 1.0 - inst.y, 0.2);
	}
}
