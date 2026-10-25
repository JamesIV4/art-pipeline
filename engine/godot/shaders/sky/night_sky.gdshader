// Origin: S:\Repos\trick-or-treat\game\shaders\sky.gdshader (imported 2026-10-25)
// Changes: renamed sky.gdshader -> night_sky.gdshader; code unchanged.
// Deep-blue Halloween night: navy zenith, violet horizon glow, twinkling stars, a big storybook
// moon with halo and craters, and painterly cute-but-stormy cloud banks that drift slowly, catch
// silver light near the moon and sometimes slide across it.
shader_type sky;

uniform vec3 moon_dir = vec3(0.3, 0.4, -0.86);
uniform vec3 zenith : source_color = vec3(0.025, 0.04, 0.12);
uniform vec3 horizon : source_color = vec3(0.16, 0.14, 0.33);
uniform vec3 moon_color : source_color = vec3(1.0, 0.94, 0.76);
uniform float moon_size = 0.088; // angular radius, ~10 degrees across
uniform float cloud_cover = 0.5;
uniform vec3 cloud_dark : source_color = vec3(0.07, 0.08, 0.17);
uniform vec3 cloud_light : source_color = vec3(0.27, 0.27, 0.45);
uniform float lightning = 0.0;

float hash(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float hash2(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash2(i), b = hash2(i + vec2(1, 0)), c = hash2(i + vec2(0, 1)), d = hash2(i + vec2(1, 1));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
	float v = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) {
		v += vnoise(p) * a;
		p = p * 2.03 + vec2(1.7, 9.2);
		a *= 0.5;
	}
	return v;
}

void sky() {
	vec3 d = normalize(EYEDIR);
	float h = d.y;
	vec3 col = mix(horizon, zenith, smoothstep(-0.05, 0.65, h));
	col += vec3(0.10, 0.05, 0.13) * exp(-abs(h) * 8.0);
	if (h < 0.0) {
		col = mix(col, horizon * 0.6, smoothstep(0.0, -0.3, h));
	}
	// Stars.
	vec3 sd = d * 190.0;
	vec3 cell = floor(sd);
	float rnd = hash(cell);
	if (rnd > 0.996) {
		vec3 f = fract(sd) - 0.5;
		float s = smoothstep(0.28, 0.0, length(f));
		float tw = 0.55 + 0.45 * sin(TIME * (1.5 + rnd * 3.0) + rnd * 100.0);
		col += vec3(1.0, 0.95, 0.85) * s * tw * smoothstep(0.03, 0.3, h) * 1.4;
	}
	// Moon.
	vec3 md = normalize(moon_dir);
	float ang = acos(clamp(dot(d, md), -1.0, 1.0));
	float disc = smoothstep(moon_size, moon_size - 0.003, ang);
	vec3 tx = normalize(cross(md, vec3(0.0, 1.0, 0.0)));
	vec3 ty = cross(tx, md);
	vec3 pd = d - md * dot(d, md);
	vec2 uv = vec2(dot(pd, tx), dot(pd, ty)) / moon_size;
	float crat = 0.0;
	crat += smoothstep(0.24, 0.2, length(uv - vec2(-0.32, 0.22)));
	crat += smoothstep(0.17, 0.13, length(uv - vec2(0.36, -0.12)));
	crat += smoothstep(0.13, 0.1, length(uv - vec2(-0.06, -0.46)));
	crat += smoothstep(0.1, 0.075, length(uv - vec2(0.22, 0.48)));
	crat += smoothstep(0.08, 0.06, length(uv - vec2(-0.55, -0.2)));
	vec3 mc = moon_color * (1.0 - 0.16 * clamp(crat, 0.0, 1.0)) * (0.9 + 0.1 * uv.y);
	float outside = max(ang - moon_size, 0.0);
	float halo = exp(-outside * 7.0) * 0.32 + exp(-outside * 35.0) * 0.4;
	col += vec3(0.72, 0.74, 0.95) * halo * (1.0 - disc);
	col = mix(col, mc * 2.4, disc);
	// Painterly cloud banks (projected onto a dome, drifting).
	if (h > 0.0) {
		vec2 cuv = d.xz / (h + 0.18) * 0.9 + vec2(TIME * 0.006, TIME * 0.0025);
		float n = fbm(cuv * 1.1);
		float shape = smoothstep(1.0 - cloud_cover - 0.08, 1.0 - cloud_cover + 0.22, n);
		float body = fbm(cuv * 2.3 + 4.0);
		float moonward = pow(max(dot(d, md), 0.0), 18.0);
		vec3 ccol = mix(cloud_dark, cloud_light, body * 0.9);
		// Silver lining toward the moon on the cloud edges.
		float edge = shape * (1.0 - shape) * 4.0;
		ccol += vec3(0.75, 0.78, 1.0) * (edge * 0.55 + 0.25) * moonward * 1.6;
		ccol += vec3(0.55, 0.45, 0.95) * lightning * (0.4 + body);
		float fade = smoothstep(0.02, 0.2, h);
		float alpha = shape * fade * (1.0 - disc * 0.55);
		col = mix(col, ccol, alpha);
	}
	COLOR = col;
}
