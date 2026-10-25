// Origin: S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\unit-lab\shaders\floor_grid.gdshader (imported 2026-10-25)
// Changes: none (verbatim copy plus this header).
// Lab floor: 2 m tile grid (tiles centred on the origin, edges at odd metres), 0.5 m sub-grid,
// and the death tile highlighted so spill past its edge can be read off a top-down screenshot.
shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

uniform vec3 floor_color : source_color = vec3(0.46, 0.46, 0.44);
uniform vec3 tile_color : source_color = vec3(0.60, 0.56, 0.47);
uniform vec3 edge_color : source_color = vec3(0.06, 0.06, 0.06);
uniform vec3 sub_color : source_color = vec3(0.33, 0.33, 0.32);
uniform vec2 death_tile = vec2(0.0);
uniform float tile_m = 2.0;
uniform float edge_width_m = 0.03;
uniform float sub_m = 0.5;
uniform float sub_width_m = 0.008;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

// 1 on grid lines of the given pitch (lines at offset + k * pitch), antialiased.
float grid(vec2 p, float pitch, float offset, float width) {
	vec2 q = (p - offset) / pitch;
	vec2 d = abs(q - round(q)) * pitch;
	vec2 aa = fwidth(p);
	vec2 l = 1.0 - smoothstep(vec2(width * 0.5), vec2(width * 0.5) + aa, d);
	return max(l.x, l.y);
}

void fragment() {
	vec2 p = world_pos.xz;
	vec3 c = floor_color;
	if (all(lessThan(abs(p - death_tile), vec2(tile_m * 0.5)))) {
		c = tile_color;
	}
	c = mix(c, sub_color, grid(p, sub_m, 0.0, sub_width_m) * 0.7);
	c = mix(c, edge_color, grid(p, tile_m, tile_m * 0.5, edge_width_m));
	ALBEDO = c;
	ROUGHNESS = 0.85;
}
