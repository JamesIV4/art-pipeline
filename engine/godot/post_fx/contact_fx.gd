# Origin: S:\Repos\trick-or-treat\game\scripts\contact_fx.gd (imported 2026-10-25)
# Changes: none (verbatim copy plus this header; identical to S:\Repos\OpenXcom-Extended-3D\xcom-3d-godot\battlescape-dev\oxp\contact_fx.gd apart from its own header line).
extends CompositorEffect
## Ported from the OpenXcom-Extended-3D battlescape (oxp/contact_fx.gd, unchanged apart from this header).
## Screen-space contact shadows (Bend Studio style, simplified) and a depth-only small-radius AO for the 3D
## view (Godot 4.7 has neither; contact shadows arrive in 4.8). Two compute passes after the
## transparent pass, on visible pixels only:
##  1. per pixel: view position and a normal reconstructed from the resolved depth buffer;
##     contact shadow = a short ray march toward the sun through the depth buffer (surface facing the sun only);
##     depth AO = 6 directions x 3 steps within a small radius, occlusion from the depth-derived geometry, so
##     grass blades (whose shading normals point up) still occlude the gaps between them.
##  2. a small depth-aware blur, then colour *= (1 - contact) * (1 - AO).
## Half resolution (default): pass 1 runs on every 2nd pixel in x and y, pass 2 upsamples 3x3 half-res texels with
## spatial x depth weights (no halos across unit / wall silhouettes). Multiplicative, so it commutes with the LOS overlay (also multiplicative); pixels without geometry (the
## never-seen void) are skipped. The host sets sun_dir (world, toward the sun) every frame.

var sun_dir := Vector3(0, 1, 0)
var cs_on := false           # user 2026-10-06: depth AO only by default (contact shadows stay a panel option)
var cs_length := 0.4         # m
var cs_thickness := 0.3      # m: how thick an occluder in the depth buffer is assumed to be
var cs_intensity := 0.7
var cs_steps := 12
var ao_on := true
var ao_radius := 0.4         # m
var ao_intensity := 1.0
var ao_bias := 0.1
var debug := 0               # 1 = show the darkening factor
var half_res := true         # occlusion at half resolution + depth-aware upsample (false: full resolution, review)
var gpu_ms := 0.0             # this pass's GPU time, averaged (GPU timestamps; 0 while off)
var _gpu_hist: Array = []

var rd: RenderingDevice
var _occ_shader: RID
var _occ_pipe: RID
var _apply_shader: RID
var _apply_pipe: RID
var _sampler: RID
var _params: RID
var _occ_tex: RID
var _occ_size := Vector2i.ZERO


func _init() -> void:
	effect_callback_type = EFFECT_CALLBACK_TYPE_POST_TRANSPARENT
	access_resolved_depth = true
	access_resolved_color = true
	RenderingServer.call_on_render_thread(_setup)


func _setup() -> void:
	rd = RenderingServer.get_rendering_device()
	if rd == null:
		return
	_occ_shader = _compile(COMMON + OCC_SRC)
	_apply_shader = _compile(COMMON + APPLY_SRC)
	if _occ_shader.is_valid():
		_occ_pipe = rd.compute_pipeline_create(_occ_shader)
	if _apply_shader.is_valid():
		_apply_pipe = rd.compute_pipeline_create(_apply_shader)
	var ss := RDSamplerState.new()
	ss.min_filter = RenderingDevice.SAMPLER_FILTER_NEAREST
	ss.mag_filter = RenderingDevice.SAMPLER_FILTER_NEAREST
	ss.repeat_u = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	ss.repeat_v = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	_sampler = rd.sampler_create(ss)
	_params = rd.storage_buffer_create(64 * 4)


func _compile(src: String) -> RID:
	var s := RDShaderSource.new()
	s.language = RenderingDevice.SHADER_LANGUAGE_GLSL
	s.source_compute = src
	var spirv := rd.shader_compile_spirv_from_source(s)
	if spirv.compile_error_compute != "":
		push_error("OXP contact_fx shader: " + spirv.compile_error_compute)
		return RID()
	return rd.shader_create_from_spirv(spirv)


func _notification(what: int) -> void:
	if what == NOTIFICATION_PREDELETE and rd:
		for r in [_occ_tex, _occ_pipe, _occ_shader, _apply_pipe, _apply_shader, _sampler, _params]:
			if r.is_valid():
				rd.free_rid(r)


func _render_callback(_type: int, render_data: RenderData) -> void:
	if rd == null or not _occ_pipe.is_valid() or not _apply_pipe.is_valid():
		return
	_read_timestamps()
	var csi := cs_intensity if cs_on else 0.0
	var aoi := ao_intensity if ao_on else 0.0
	if csi <= 0.0 and aoi <= 0.0 and debug == 0:
		return
	var rb := render_data.get_render_scene_buffers() as RenderSceneBuffersRD
	var sd := render_data.get_render_scene_data() as RenderSceneDataRD
	if rb == null or sd == null:
		return
	var size := rb.get_internal_size()
	if size.x <= 0 or size.y <= 0:
		return
	var sc := 2 if half_res else 1
	var osize := Vector2i((size.x + sc - 1) / sc, (size.y + sc - 1) / sc)
	if osize != _occ_size:
		if _occ_tex.is_valid():
			rd.free_rid(_occ_tex)
		var tf := RDTextureFormat.new()
		tf.format = RenderingDevice.DATA_FORMAT_R16G16_SFLOAT
		tf.width = osize.x
		tf.height = osize.y
		tf.usage_bits = RenderingDevice.TEXTURE_USAGE_STORAGE_BIT | RenderingDevice.TEXTURE_USAGE_SAMPLING_BIT
		_occ_tex = rd.texture_create(tf, RDTextureView.new())
		_occ_size = osize
	var proj: Projection = sd.get_cam_projection()
	var inv := proj.inverse()
	var cam: Transform3D = sd.get_cam_transform()
	var sv := (cam.basis.inverse() * sun_dir).normalized()
	var f := PackedFloat32Array()
	for m in [proj, inv]:
		for c in 4:
			var col: Vector4 = m[c]
			f.append_array([col.x, col.y, col.z, col.w])
	f.append_array([sv.x, sv.y, sv.z, 0.0])
	f.append_array([cs_length, cs_thickness, csi, float(cs_steps)])
	f.append_array([ao_radius, aoi, ao_bias, float(debug)])
	f.append_array([float(size.x), float(size.y), 1.0 / size.x, 1.0 / size.y])
	f.append_array([float(osize.x), float(osize.y), float(sc), 1.0 if half_res else 2.0])
	var bytes := f.to_byte_array()
	rd.buffer_update(_params, 0, bytes.size(), bytes)
	var depth := rb.get_depth_layer(0)
	var color := rb.get_color_layer(0)
	var u_depth := RDUniform.new()
	u_depth.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	u_depth.binding = 0
	u_depth.add_id(_sampler)
	u_depth.add_id(depth)
	var u_occ := RDUniform.new()
	u_occ.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
	u_occ.binding = 1
	u_occ.add_id(_occ_tex)
	var u_par := RDUniform.new()
	u_par.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
	u_par.binding = 2
	u_par.add_id(_params)
	var u_col := RDUniform.new()
	u_col.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
	u_col.binding = 3
	u_col.add_id(color)
	var occ_u: Array[RDUniform] = [u_depth, u_occ, u_par]
	var apply_u: Array[RDUniform] = [u_depth, u_occ, u_par, u_col]
	var set_occ := UniformSetCacheRD.get_cache(_occ_shader, 0, occ_u)
	var set_apply := UniformSetCacheRD.get_cache(_apply_shader, 0, apply_u)
	var gx := (size.x + 7) / 8
	var gy := (size.y + 7) / 8
	rd.capture_timestamp("oxp_cfx_begin")
	var cl := rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(cl, _occ_pipe)
	rd.compute_list_bind_uniform_set(cl, set_occ, 0)
	rd.compute_list_dispatch(cl, (osize.x + 7) / 8, (osize.y + 7) / 8, 1)
	rd.compute_list_add_barrier(cl)
	rd.compute_list_bind_compute_pipeline(cl, _apply_pipe)
	rd.compute_list_bind_uniform_set(cl, set_apply, 0)
	rd.compute_list_dispatch(cl, gx, gy, 1)
	rd.compute_list_end()
	rd.capture_timestamp("oxp_cfx_end")


## GPU time of this pass in the last finished frame (render thread), averaged over 60 frames.
func _read_timestamps() -> void:
	var a := -1
	var b := -1
	for i in rd.get_captured_timestamps_count():
		var n := rd.get_captured_timestamp_name(i)
		if n == "oxp_cfx_begin":
			a = i
		elif n == "oxp_cfx_end":
			b = i
	if a < 0 or b < 0:
		return
	_gpu_hist.append((rd.get_captured_timestamp_gpu_time(b) - rd.get_captured_timestamp_gpu_time(a)) / 1000000.0)
	if _gpu_hist.size() > 60:
		_gpu_hist.pop_front()
	var s := 0.0
	for v in _gpu_hist:
		s += v
	gpu_ms = s / _gpu_hist.size()


const COMMON := """
#version 450
layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;
layout(set = 0, binding = 0) uniform sampler2D depth_tex;
layout(set = 0, binding = 2, std430) restrict readonly buffer Params {
	mat4 proj;
	mat4 inv_proj;
	vec4 sun_view;   // xyz: toward the sun, view space
	vec4 cs;         // length m, thickness m, intensity, steps
	vec4 ao;         // radius m, intensity, bias, debug
	vec4 screen;     // w, h, 1/w, 1/h
	vec4 occ;        // occlusion texture w, h; pixels per texel (1 or 2); upsample radius in texels
} p;

// The scene data's camera projection is the RD one (y flipped, reversed-Z [0, 1] depth: near 1, far 0), so the
// depth value IS its NDC z and texture row 0 is NDC y -1 (2026-10-07: the earlier 1 - 2d mirrored the depth,
// turning the geometry inside out: AO darkened convex edges instead of concave ones).
vec3 view_pos(vec2 uv, float d) {
	vec4 v = p.inv_proj * vec4(uv.x * 2.0 - 1.0, uv.y * 2.0 - 1.0, d, 1.0);
	return v.xyz / v.w;
}

float view_z(ivec2 px) {
	ivec2 q = clamp(px, ivec2(0), ivec2(p.screen.xy) - 1);
	vec2 uv = (vec2(q) + 0.5) * p.screen.zw;
	vec4 v = p.inv_proj * vec4(uv.x * 2.0 - 1.0, uv.y * 2.0 - 1.0, texelFetch(depth_tex, q, 0).r, 1.0);
	return v.z / v.w;
}

vec3 view_at(ivec2 px) {
	ivec2 q = clamp(px, ivec2(0), ivec2(p.screen.xy) - 1);
	return view_pos((vec2(q) + 0.5) * p.screen.zw, texelFetch(depth_tex, q, 0).r);
}

bool empty_at(ivec2 px) {
	ivec2 q = clamp(px, ivec2(0), ivec2(p.screen.xy) - 1);
	return texelFetch(depth_tex, q, 0).r <= 0.0000001;
}
"""

const OCC_SRC := """
layout(rg16f, set = 0, binding = 1) uniform restrict writeonly image2D occ_img;

vec2 to_uv(vec3 v) {
	vec4 c = p.proj * vec4(v, 1.0);
	vec2 n = c.xy / c.w;
	return vec2(n.x * 0.5 + 0.5, n.y * 0.5 + 0.5);
}

float ign(vec2 px) {
	return fract(52.9829189 * fract(dot(px, vec2(0.06711056, 0.00583715))));
}

void main() {
	ivec2 ox = ivec2(gl_GlobalInvocationID.xy);
	if (ox.x >= int(p.occ.x) || ox.y >= int(p.occ.y)) {
		return;
	}
	ivec2 px = ox * int(p.occ.z);
	if (empty_at(px)) {
		imageStore(occ_img, ox, vec4(0.0));
		return;
	}
	vec3 P = view_at(px);
	vec3 pr = view_at(px + ivec2(1, 0));
	vec3 pl = view_at(px - ivec2(1, 0));
	vec3 pd = view_at(px + ivec2(0, 1));
	vec3 pu = view_at(px - ivec2(0, 1));
	vec3 dx = abs(pr.z - P.z) < abs(P.z - pl.z) ? pr - P : P - pl;
	vec3 dy = abs(pd.z - P.z) < abs(P.z - pu.z) ? pd - P : P - pu;
	vec3 N = normalize(cross(dx, dy));
	if (N.z < 0.0) {
		N = -N;
	}
	float jitter = ign(vec2(px));

	float shadow = 0.0;
	if (p.cs.z > 0.0) {
		vec3 L = normalize(p.sun_view.xyz);
		float lit = clamp(dot(N, L) * 4.0, 0.0, 1.0);
		if (lit > 0.0) {
			int steps = int(p.cs.w);
			float stepl = p.cs.x / float(steps);
			vec3 O = P + N * 0.01;
			for (int i = 0; i < steps; i++) {
				float t = (float(i) + jitter) * stepl + 0.01;
				vec3 R = O + L * t;
				vec2 suv = to_uv(R);
				if (suv.x < 0.0 || suv.y < 0.0 || suv.x > 1.0 || suv.y > 1.0) {
					break;
				}
				ivec2 sp = ivec2(suv * p.screen.xy);
				if (empty_at(sp)) {
					continue;
				}
				float delta = view_at(sp).z - R.z;   // > 0: the visible surface there is in front of the ray point
				if (delta > 0.01 && delta < p.cs.y) {
					shadow = 1.0 - 0.5 * t / p.cs.x;
					break;
				}
			}
			shadow *= lit;
		}
	}

	float occl = 0.0;
	if (p.ao.y > 0.0) {
		float r = p.ao.x;
		float rpx = max(length((to_uv(P + vec3(r, 0.0, 0.0)) - (vec2(px) + 0.5) * p.screen.zw) * p.screen.xy), 2.0);
		float a0 = jitter * 6.2831853;
		float sum = 0.0;
		for (int k = 0; k < 6; k++) {
			float a = a0 + float(k) * 1.0471976;
			vec2 dir = vec2(cos(a), sin(a));
			float horizon = 0.0;   // highest occluder seen in this direction (sine of its elevation above the surface)
			for (int s = 1; s <= 4; s++) {
				float fr = (float(s) - 0.5 * fract(jitter * 3.7 + float(k) * 0.618)) / 4.0;
				ivec2 sp = px + ivec2(round(dir * rpx * fr));
				if (empty_at(sp)) {
					continue;
				}
				vec3 V = view_at(sp) - P;
				float dist = length(V);
				float w = 1.0 - clamp(dist / r, 0.0, 1.0);
				horizon = max(horizon, max(dot(N, V / max(dist, 0.0001)) - p.ao.z, 0.0) * w);
			}
			sum += horizon;
		}
		occl = clamp(sum / 6.0 * 2.5, 0.0, 1.0);
	}
	imageStore(occ_img, ox, vec4(shadow, occl, 0.0, 0.0));
}
"""

const APPLY_SRC := """
layout(rg16f, set = 0, binding = 1) uniform restrict readonly image2D occ_img;
layout(rgba16f, set = 0, binding = 3) uniform restrict image2D color_img;

void main() {
	ivec2 px = ivec2(gl_GlobalInvocationID.xy);
	ivec2 size = ivec2(p.screen.xy);
	if (px.x >= size.x || px.y >= size.y || empty_at(px)) {
		return;
	}
	// depth-aware upsample / blur: occlusion texels around this pixel, weighted by distance and depth match
	float zc = view_z(px);
	int sc = int(p.occ.z);
	int r = int(p.occ.w);
	vec2 ofp = (vec2(px) + 0.5) / float(sc) - 0.5;   // this pixel in occlusion texel coordinates
	ivec2 o0 = ivec2(floor(ofp + 0.5));
	ivec2 osz = ivec2(p.occ.xy);
	vec2 acc = vec2(0.0);
	float wsum = 0.0;
	// half resolution: the 2x2 texels around the pixel, bilinear x depth weights; full resolution: (2r+1)^2 box
	ivec2 lo = sc > 1 ? ivec2(floor(ofp)) : o0 - ivec2(r);
	int n = sc > 1 ? 1 : 2 * r;
	for (int y = 0; y <= n; y++) {
		for (int x = 0; x <= n; x++) {
			ivec2 q = clamp(lo + ivec2(x, y), ivec2(0), osz - 1);
			ivec2 qp = q * sc;
			if (empty_at(qp)) {
				continue;
			}
			vec2 fr = abs(vec2(lo + ivec2(x, y)) - ofp);
			float ws = sc > 1 ? max(1.0 - fr.x, 0.0) * max(1.0 - fr.y, 0.0) + 0.001 : 1.0;
			float w = ws * exp(-abs(view_z(qp) - zc) * 12.0);
			acc += imageLoad(occ_img, q).rg * w;
			wsum += w;
		}
	}
	vec2 o = wsum > 0.0001 ? acc / wsum : vec2(0.0);
	float f = (1.0 - p.cs.z * o.x) * (1.0 - p.ao.y * o.y);
	vec4 c = imageLoad(color_img, px);
	if (p.ao.w > 0.5) {
		c.rgb = vec3(f);
	} else {
		c.rgb *= f;
	}
	imageStore(color_img, px, c);
}
"""
