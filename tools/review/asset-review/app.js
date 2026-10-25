// Origin: S:/Repos/OpenXcom-Extended-3D/art/tools/asset-review/app.js (imported 2026-10-25)
// Changed: header only
// Asset revision reviewer (served by asset_review.py). One WebGL canvas over the page draws every visible
// card's 3D view through a scissor rect, under the battlescape's lighting (battlescape-dev/oxp/battlescape_view.gd
// apply_daylight + debug/shipped_render_defaults.gd), night by default.
import * as THREE from './vendor/three.bundle.js';

const $ = s => document.querySelector(s);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

// ------------------------------------------------------------------------------------------- Godot look
// Godot 4's Filmic tonemapper (white 1.0, exposure 1.0) in place of three's custom hook.
THREE.ShaderChunk.tonemapping_pars_fragment = THREE.ShaderChunk.tonemapping_pars_fragment.replace(
  'vec3 CustomToneMapping( vec3 color ) { return color; }',
  `vec3 godotFilmic( vec3 c ) {
    const float A = 0.22 * 4.0; const float B = 0.30 * 2.0; const float C = 0.10;
    const float D = 0.20 * 4.0; const float E = 0.01 * 4.0; const float F = 0.30;
    return ( ( c * ( A * c + C * B ) + D * E ) / ( c * ( A * c + B ) + D * F ) ) - E / F;
  }
  vec3 CustomToneMapping( vec3 color ) {
    color = max( color * toneMappingExposure, 0.0 );
    return clamp( godotFilmic( color ) / godotFilmic( vec3( 1.0 ) ).x, 0.0, 1.0 );
  }`);
// The game's neutral sky feeds reflections only (env.reflected_light_source = sky); the ambient is a plain colour.
THREE.ShaderChunk.lights_fragment_maps = THREE.ShaderChunk.lights_fragment_maps.replace(
  'iblIrradiance += getIBLIrradiance( geometryNormal );', '');

// Godot light energies -> three intensities: Godot folds pi into its light energies, three does not.
const L = {
  daySun: 3.44, dayAmb: 2.22, nightSun: 0.14, nightAmb: 0.15, maxShade: 15,
  sunColor: '#897f6a', ambColor: '#4f6995', sunElev: 45.5, sunAzim: 149.5,
  lampColor: '#ffe6bf', lampEnergy: 3.0, lampDecay: 0.5, lampRange: 1.0,
  squadColor: '#fff2d9', squadEnergy: 1.95,
};
const PLAYER_UNITS = new Set(['XCOM_0', 'XCOM_1', 'XCOM_2', 'TANKS', 'X_REAP', 'X_ROB']);
const TILE = 2.0;
const VIEW_BG = new THREE.Color(0x07090c);
const DEG = Math.PI / 180;

const settings = Object.assign({ shade: 15, lamps: true, squad: false }, readLocal('ar.settings', {}));
function readLocal(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }
function writeLocal(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private window */ } }

const canvas = $('#gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight, false);
renderer.toneMapping = THREE.CustomToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;

const scene = new THREE.Scene();
const ambient = new THREE.AmbientLight(L.ambColor, 0);
const sun = new THREE.DirectionalLight(L.sunColor, 0);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.015;
const squad = new THREE.DirectionalLight(L.squadColor, 0);
scene.add(ambient, sun, sun.target, squad, squad.target);
// the sun's rotation_degrees (-elev, azim, 0); it shines along its -Z, so +Z points at the sun
const sunTo = new THREE.Vector3(0, 0, 1).applyEuler(new THREE.Euler(-L.sunElev * DEG, L.sunAzim * DEG, 0, 'YXZ'));
scene.environment = makeReflectionSky();
const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 100);

function makeReflectionSky() {
  const lin = v => new THREE.Color().setRGB(v, v, v, THREE.SRGBColorSpace);
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    uniforms: { top: { value: lin(0.50) }, horizon: { value: lin(0.42) }, bottom: { value: lin(0.25) } },
    vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform vec3 top; uniform vec3 horizon; uniform vec3 bottom; varying vec3 vDir;
      void main(){ float y = vDir.y; vec3 c = y > 0.0 ? mix(horizon, top, sqrt(y)) : mix(horizon, bottom, sqrt(-y)); gl_FragColor = vec4(c, 1.0); }`,
  });
  const sky = new THREE.Scene();
  sky.add(new THREE.Mesh(new THREE.SphereGeometry(10, 32, 16), mat));
  const pmrem = new THREE.PMREMGenerator(renderer);
  const rt = pmrem.fromScene(sky, 0, 0.1, 50);
  pmrem.dispose();
  return rt.texture;
}

function describeLighting(s = settings) {
  const k = s.shade / L.maxShade;
  const sunE = THREE.MathUtils.lerp(L.daySun, L.nightSun, k), ambE = THREE.MathUtils.lerp(L.dayAmb, L.nightAmb, k);
  return `global shade ${s.shade}${s.shade === 15 ? ' (night, darkest)' : s.shade === 0 ? ' (day)' : ''}: sun ${sunE.toFixed(2)}, ambient ${ambE.toFixed(2)}` +
    `; lamps ${s.lamps ? 'on' : 'off'}; squad light ${s.squad ? 'on' : 'off (X-COM units always in their own)'}`;
}

function setLightsFor(model) {
  const k = settings.shade / L.maxShade;
  sun.intensity = THREE.MathUtils.lerp(L.daySun, L.nightSun, k) * Math.PI;
  ambient.intensity = THREE.MathUtils.lerp(L.dayAmb, L.nightAmb, k) * Math.PI;
  const a = model.asset;
  const isUnit = a.category === 'unit';
  // unit_layer.gd: the soldier light lights the ground around a soldier at its full energy; units in the pool get a
  // twin scaled by the darkness. X-COM's own units always stand in their own pool.
  const inPool = settings.squad || (isUnit && PLAYER_UNITS.has(a.family));
  squad.intensity = inPool ? L.squadEnergy * (isUnit ? k : 1) * Math.PI : 0;
  squad.visible = squad.intensity > 0;
  for (const lamp of model.lamps) {
    const effective = lamp.userData.power - (L.maxShade - settings.shade);   // light_sources.gd
    lamp.visible = settings.lamps && effective > 0;
    lamp.intensity = L.lampEnergy * Math.max(effective, 0) / L.maxShade * Math.PI;
    lamp.distance = Math.max(0.5, effective * TILE * L.lampRange);
  }
  const c = model.center, r = model.radius;
  sun.position.copy(c).addScaledVector(sunTo, r * 4 + 2);
  sun.target.position.copy(c);
  squad.position.copy(sun.position);
  squad.target.position.copy(c);
  const sc = sun.shadow.camera;
  sc.left = sc.bottom = -r * 1.15; sc.right = sc.top = r * 1.15; sc.near = 0.01; sc.far = r * 10 + 4;
  sc.updateProjectionMatrix();
  sun.target.updateMatrixWorld(); squad.target.updateMatrixWorld();
}

// ---------------------------------------------------------------------------------------------- loading
const sharedTextures = new Map();
// One GPU texture per image file across every glTF (tiles of a family share their texture sets). Registered under
// the EXT_texture_webp name so it takes that built-in plugin's place.
class SharedTexturePlugin {
  constructor(parser) { this.parser = parser; this.name = 'EXT_texture_webp'; }
  loadTexture(index) {
    const p = this.parser, json = p.json, def = json.textures[index];
    const src = def.extensions?.EXT_texture_webp?.source ?? def.source;
    const img = src !== undefined ? json.images?.[src] : null;
    if (!img) return null;
    if (!img.uri || img.uri.startsWith('data:')) return p.loadTextureImage(index, src, p.textureLoader);   // embedded
    const url = new URL(img.uri, new URL(p.options.path, location.href)).href;
    const key = url + '|' + JSON.stringify(json.samplers?.[def.sampler] ?? null);
    if (!sharedTextures.has(key)) sharedTextures.set(key, p.loadTextureImage(index, src, p.textureLoader));
    return sharedTextures.get(key);
  }
}
const gltfLoader = new THREE.GLTFLoader();
gltfLoader.register(p => new SharedTexturePlugin(p));
const texLoader = new THREE.TextureLoader();
const plainTextures = new Map();
function tex(url, srgb) {
  const key = url + (srgb ? '|s' : '|l');
  if (!plainTextures.has(key)) {
    const t = texLoader.load(url, () => requestRender());
    t.flipY = false;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = 8;
    plainTextures.set(key, t);
  }
  return plainTextures.get(key);
}

let INDEX = null, ASSETS = [], BY_ID = new Map(), REVS = {};
const models = new Map();   // id -> {asset, root, center, radius, lamps, promise, error}
window.assetReview = { models, renderer };   // for poking at from the devtools console

function ensureModel(asset) {
  let m = models.get(asset.id);
  if (!m) {
    m = { asset, root: null, lamps: [], center: new THREE.Vector3(), radius: 1, error: null };
    m.promise = buildModel(m).then(() => { requestRender(); updateCardState(asset.id); return m; },
      err => { console.error(asset.id, err); m.error = String(err?.message || err); updateCardState(asset.id); return m; });
    models.set(asset.id, m);
  }
  return m;
}

async function buildModel(m) {
  const a = m.asset;
  let root;
  if (a.kind === 'gltf') {
    const gltf = await gltfLoader.loadAsync(a.url);
    poseIdle(gltf.scene, gltf.animations);
    root = new THREE.Group();
    root.add(gltf.scene);
    // Units look along Godot's -Z (north); turn them to facing 3 (south-east, toward the game camera), the sprite shown.
    if (a.category === 'unit') gltf.scene.rotation.y = -0.75 * Math.PI;
  } else if (a.kind === 'natural') {
    root = await buildNatural(a);
  } else {
    throw new Error(a.missing ? 'Model file missing' : 'No model yet');
  }
  root.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root, true);
  if (box.isEmpty()) box.set(new THREE.Vector3(-0.5, 0, -0.5), new THREE.Vector3(0.5, 1, 0.5));
  const size = box.getSize(new THREE.Vector3());
  // Terrain and units are framed with their tile (2 x 2 m, large units 4 x 4) so they read at a common scale.
  let foot = 0;
  if (a.category === 'terrain') foot = TILE;
  if (a.category === 'unit') foot = Math.max(size.x, size.z) > TILE * 1.15 ? TILE * 2 : TILE;
  if (foot) box.union(new THREE.Box3(new THREE.Vector3(-foot / 2, 0, -foot / 2), new THREE.Vector3(foot / 2, 0.01, foot / 2)));
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  m.center.copy(sphere.center);
  m.radius = Math.max(sphere.radius, 0.05);
  if (foot) root.add(footprint(foot));
  if (a.category === 'terrain' && a.light_source > 0) {
    const lamp = new THREE.PointLight(L.lampColor, 0, 1, L.lampDecay);
    lamp.userData.power = a.light_source;
    const part = a.part || 'object';   // light_sources.gd _position
    lamp.position.set(part === 'west_wall' ? -0.8 : 0, part === 'floor' ? 0.4 : 1.8, part === 'north_wall' ? -0.8 : 0);
    root.add(lamp);
    m.lamps.push(lamp);
  }
  m.root = root;
}

function poseIdle(root, clips) {
  if (!clips?.length) return;
  const clip = clips.find(c => /^idle(-loop)?$/i.test(c.name)) || clips.find(c => /idle/i.test(c.name));
  if (!clip) return;
  const mixer = new THREE.AnimationMixer(root);
  mixer.clipAction(clip).play();
  mixer.update(0);
}

function footprint(size) {
  const h = size / 2, y = 0.003;
  const g = new THREE.BufferGeometry().setFromPoints([[-h, -h], [h, -h], [h, h], [-h, h], [-h, -h]].map(([x, z]) => new THREE.Vector3(x, y, z)));
  const line = new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0x3a4a5e, toneMapped: false, transparent: true, opacity: 0.8 }));
  line.userData.helper = true;
  return line;
}

// ------------------------------------------------------------------------- procedural natural ground
// A port of xcom-3d-godot/x-com--ufo-defense-3d/scripts/natural_terrain.gd (mesh_for, heights, height_at).
const heightCache = new Map();
function heights(shape) {
  if (heightCache.has(shape)) return heightCache.get(shape);
  const def = INDEX.shapes[shape], pitch = INDEX.voxel_pitch, surf = def.surface;
  const v = def.heights_voxels.slice();
  if (surf.kind === 'ramp' || surf.kind === 'corner') {
    for (let z = 0; z < 16; z++) for (let x = 0; x < 16; x++) {
      let u = x / 15, w = z / 15, value;
      if (surf.kind === 'ramp') { value = surf.axis === 'x' ? u : w; if (surf.reverse) value = 1 - value; }
      else { if (surf.reverse_x) u = 1 - u; if (surf.reverse_z) w = 1 - w; value = surf.operation === 'min' ? Math.min(u, w) : Math.max(u, w); }
      v[z * 16 + x] = (surf.low + (surf.high - surf.low) * value) * pitch;
    }
  } else {
    const low = Math.min(...v), high = Math.max(...v);
    if (high - low === 6 && Math.trunc(low) % 8 === 2 && Math.trunc(high) % 8 === 0)
      for (let i = 0; i < v.length; i++) v[i] = low - 2 + (v[i] - low) * 8 / 6;
    for (let i = 0; i < v.length; i++) v[i] *= pitch;
  }
  heightCache.set(shape, v);
  return v;
}
function heightAt(shape, x, z) {
  const v = heights(shape);
  const u = THREE.MathUtils.clamp((x + 1) * 7.5, 0, 15), w = THREE.MathUtils.clamp((z + 1) * 7.5, 0, 15);
  const ix = Math.min(Math.floor(u), 14), iz = Math.min(Math.floor(w), 14);
  const lerp = THREE.MathUtils.lerp;
  return lerp(lerp(v[iz * 16 + ix], v[iz * 16 + ix + 1], u - ix), lerp(v[(iz + 1) * 16 + ix], v[(iz + 1) * 16 + ix + 1], u - ix), w - iz);
}

function naturalGeometry(shape) {
  const v = heights(shape), surf = INDEX.shapes[shape].surface;
  const P = [];
  for (let z = 0; z < 16; z++) for (let x = 0; x < 16; x++) P.push(new THREE.Vector3(x / 7.5 - 1, v[z * 16 + x], z / 7.5 - 1));
  const pos = [], nrm = [], uv = [];
  let topCount = 0;
  // Godot's front faces are clockwise, three's counter-clockwise: each triangle is emitted a, c, b.
  const tri = (a, b, c, normal, side) => {
    if (!side) normal = new THREE.Vector3().subVectors(c, a).cross(new THREE.Vector3().subVectors(b, a)).normalize();
    for (const p of [a, c, b]) {
      pos.push(p.x, p.y, p.z); nrm.push(normal.x, normal.y, normal.z);
      if (side) uv.push((p.x + p.z) * 0.5, p.y * 0.5); else uv.push((p.x + 1) * 0.5, (p.z + 1) * 0.5);
    }
  };
  const level = v.every(h => Math.abs(h - v[0]) < 1e-6);
  const UP = new THREE.Vector3(0, 1, 0);
  if (level) { tri(P[0], P[15], P[240], UP); tri(P[15], P[255], P[240], UP); }
  else {
    const reverse = surf.kind === 'corner' && surf.reverse_x === surf.reverse_z;
    for (let z = 0; z < 15; z++) for (let x = 0; x < 15; x++) {
      const a = z * 16 + x;
      if (reverse) { tri(P[a], P[a + 1], P[a + 17], UP); tri(P[a], P[a + 17], P[a + 16], UP); }
      else { tri(P[a], P[a + 1], P[a + 16], UP); tri(P[a + 1], P[a + 17], P[a + 16], UP); }
    }
  }
  topCount = pos.length / 3;
  let edges = [];
  for (let x = 0; x < 16; x++) edges.push(x);
  for (let z = 1; z < 16; z++) edges.push(z * 16 + 15);
  for (let x = 14; x >= 0; x--) edges.push(240 + x);
  for (let z = 14; z > 0; z--) edges.push(z * 16);
  if (level) edges = [0, 15, 255, 240];
  for (let i = 0; i < edges.length; i++) {
    const a = P[edges[i]], b = P[edges[(i + 1) % edges.length]];
    const c = new THREE.Vector3(a.x, -0.09, a.z), d = new THREE.Vector3(b.x, -0.09, b.z);
    const n = new THREE.Vector3(b.z - a.z, 0, a.x - b.x).normalize();
    tri(a, c, b, n, true); tri(b, c, d, n, true);
  }
  const DOWN = new THREE.Vector3(0, -1, 0);
  tri(new THREE.Vector3(-1, -0.09, -1), new THREE.Vector3(-1, -0.09, 1), new THREE.Vector3(1, -0.09, -1), DOWN, true);
  tri(new THREE.Vector3(1, -0.09, -1), new THREE.Vector3(-1, -0.09, 1), new THREE.Vector3(1, -0.09, 1), DOWN, true);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.addGroup(0, topCount, 0);
  g.addGroup(topCount, pos.length / 3 - topCount, 1);
  return g;
}

const naturalMaterials = new Map();
function naturalMaterial(res) {
  if (naturalMaterials.has(res)) return naturalMaterials.get(res);
  const d = INDEX.materials[res];
  let m;
  if (!d) m = new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 1 });
  else if (d.type === 'shore') m = shoreMaterial(d);
  else {
    m = new THREE.MeshStandardMaterial({ roughness: d.roughness, metalness: d.metallic_texture && d.metallic_channel !== 2 ? 0 : d.metallic });
    if (d.albedo_color) m.color.setRGB(d.albedo_color[0], d.albedo_color[1], d.albedo_color[2], THREE.SRGBColorSpace);
    if (d.albedo) m.map = tex(d.albedo, true);
    if (d.roughness_texture && d.roughness_channel === 1) m.roughnessMap = tex(d.roughness_texture, false);
    if (d.metallic_texture && d.metallic_channel === 2) m.metalnessMap = tex(d.metallic_texture, false);
    if (d.ao) m.aoMap = tex(d.ao, false);
    // OpenGL normal maps without tangents: three's derivative tangents need y flipped (as GLTFLoader does)
    if (d.normal) { m.normalMap = tex(d.normal, false); m.normalScale.set(d.normal_scale, -d.normal_scale); }
    if (d.transparency === 2 || d.transparency === 3) m.alphaTest = d.alpha_scissor;
    else if (d.transparency === 1) m.transparent = true;
    if (d.double_sided) m.side = THREE.DoubleSide;
  }
  naturalMaterials.set(res, m);
  return m;
}
// natural_shore.gdshader, still: navy water and the shore mask's snow, no ripples.
function shoreMaterial(d) {
  const m = new THREE.MeshStandardMaterial({ roughness: 0.07, metalness: 0 });
  m.defines = { USE_UV: '' };
  const mask = d.shore_mask ? tex(d.shore_mask, false) : null, snow = d.snow_albedo ? tex(d.snow_albedo, true) : null;
  m.onBeforeCompile = sh => {
    sh.uniforms.shoreMask = { value: mask }; sh.uniforms.snowAlb = { value: snow };
    sh.uniforms.waterCol = { value: new THREE.Color().setRGB(d.water[0], d.water[1], d.water[2], THREE.SRGBColorSpace) };
    sh.fragmentShader = 'uniform sampler2D shoreMask;\nuniform sampler2D snowAlb;\nuniform vec3 waterCol;\n' + sh.fragmentShader
      .replace('#include <map_fragment>', 'float snowM = texture2D( shoreMask, vUv ).r;\ndiffuseColor.rgb = mix( waterCol, texture2D( snowAlb, vUv ).rgb, snowM );')
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = mix( 0.07, 0.9, snowM );');
  };
  m.customProgramCacheKey = () => 'natural_shore';
  return m;
}

async function buildNatural(a) {
  const n = a.natural;
  const root = new THREE.Group();
  root.name = a.id;
  const base = new THREE.Mesh(naturalGeometry(n.shape), n.materials.map(naturalMaterial));
  base.name = 'SharedBase';
  root.add(base);
  const details = await Promise.all(n.details.map(d => gltfLoader.loadAsync(d.url).then(g => [d, g.scene])));
  for (const [d, node] of details) {
    node.position.set(d.anchor[0], heightAt(n.shape, d.anchor[0], d.anchor[1]) + d.height_offset, d.anchor[1]);
    node.rotation.y = d.rotation * DEG;
    node.scale.setScalar(d.scale);
    root.add(node);
  }
  return root;
}

function disposeAll() {
  for (const m of models.values()) {
    m.root?.traverse(o => {
      o.geometry?.dispose();
      for (const mat of [].concat(o.material || [])) if (!naturalMaterials.has(mat)) mat.dispose?.();
    });
  }
  models.clear();
  for (const p of sharedTextures.values()) p.then(t => t.dispose(), () => {});
  sharedTextures.clear();
}

// Loading queue: only cards near the viewport load, a few at a time.
const wanted = new Set();
const queue = [];
let active = 0;
function want(id) { if (!models.has(id) && !queue.includes(id)) queue.push(id); pump(); }
function pump() {
  while (active < 6 && queue.length) {
    const id = queue.shift();
    if (!wanted.has(id) || models.has(id)) continue;
    active++;
    ensureModel(BY_ID.get(id)).promise.finally(() => { active--; pump(); });
  }
}

// ----------------------------------------------------------------------------------------------- views
// A view = a card's (or the inspector's) camera on a model: game framing (yaw 45, pitch 30), drag to orbit.
function newView(asset, from) {
  return { asset, el: null, yaw: from?.yaw ?? 45 * DEG, pitch: from?.pitch ?? 30 * DEG, zoom: from?.zoom ?? 1 };
}
const cards = new Map();   // id -> {view, card, ...}
let modalView = null;
let renderPending = false;
function requestRender() { if (!renderPending) { renderPending = true; requestAnimationFrame(renderAll); } }

function placeCamera(view, model, w, h) {
  const r = model.radius * 1.06 / view.zoom, aspect = w / h;
  if (aspect >= 1) { cam.top = r; cam.bottom = -r; cam.right = r * aspect; cam.left = -r * aspect; }
  else { cam.right = r; cam.left = -r; cam.top = r / aspect; cam.bottom = -r / aspect; }
  const dist = model.radius * 4 + 2;
  cam.near = 0.01; cam.far = dist + model.radius * 4;
  const cp = Math.cos(view.pitch);
  cam.position.set(Math.sin(view.yaw) * cp, Math.sin(view.pitch), Math.cos(view.yaw) * cp).multiplyScalar(dist).add(model.center);
  cam.lookAt(model.center);
  cam.updateProjectionMatrix();
}

function drawView(view, rect, clip, H) {
  const model = models.get(view.asset.id);
  if (!model?.root) return false;
  const x0 = Math.max(rect.left, clip.left), x1 = Math.min(rect.right, clip.right);
  const y0 = Math.max(rect.top, clip.top), y1 = Math.min(rect.bottom, clip.bottom);
  if (x1 <= x0 || y1 <= y0) return false;
  renderer.setViewport(rect.left, H - rect.bottom, rect.width, rect.height);
  renderer.setScissor(x0, H - y1, x1 - x0, y1 - y0);
  renderer.setClearColor(VIEW_BG, 1);
  scene.add(model.root);
  setLightsFor(model);
  placeCamera(view, model, rect.width, rect.height);
  renderer.render(scene, cam);
  scene.remove(model.root);
  return true;
}

let exporting = false;
function renderAll() {
  renderPending = false;
  if (exporting) return;
  const W = innerWidth, H = innerHeight;
  const size = renderer.getSize(new THREE.Vector2());
  if (size.x !== W || size.y !== H) renderer.setSize(W, H, false);
  renderer.setScissorTest(false);
  renderer.setClearColor(0x000000, 0);
  renderer.clear();
  if (!$('#exportDlg').hidden) return;
  renderer.setScissorTest(true);
  if (modalView) { const r = modalView.el.getBoundingClientRect(); drawView(modalView, r, r, H); return; }
  const clip = $('#grid').getBoundingClientRect();
  for (const c of cards.values()) {
    const r = c.view.el.getBoundingClientRect();
    if (r.bottom < clip.top || r.top > clip.bottom) continue;
    drawView(c.view, r, clip, H);
  }
}

function bindOrbit(view, opts = {}) {
  const e = view.el;
  let drag = null;
  e.addEventListener('pointerdown', ev => { if (ev.button !== 0) return; drag = { x: ev.clientX, y: ev.clientY }; e.setPointerCapture(ev.pointerId); });
  e.addEventListener('pointermove', ev => {
    if (!drag) return;
    view.yaw -= (ev.clientX - drag.x) * 0.009;
    view.pitch = THREE.MathUtils.clamp(view.pitch + (ev.clientY - drag.y) * 0.009, -20 * DEG, 89 * DEG);
    drag = { x: ev.clientX, y: ev.clientY };
    requestRender();
  });
  const end = () => { if (drag) { drag = null; opts.onEnd?.(); } };
  e.addEventListener('pointerup', end);
  e.addEventListener('pointercancel', end);
  e.addEventListener('dblclick', () => { view.yaw = 45 * DEG; view.pitch = 30 * DEG; view.zoom = 1; requestRender(); opts.onEnd?.(); });
  if (opts.wheel) e.addEventListener('wheel', ev => {
    ev.preventDefault();
    view.zoom = THREE.MathUtils.clamp(view.zoom * Math.exp(-ev.deltaY * 0.0015), 0.3, 12);
    requestRender();
  }, { passive: false });
}

// ------------------------------------------------------------------------------------------- revisions
let saveTimers = new Map();
function setSaveState(text, err) {
  const s = $('#saveState');
  s.textContent = text;
  s.title = text + (INDEX ? '\nNotes file: ' + INDEX.revisions_file : '');
  s.classList.toggle('err', !!err);
}

async function postRevision(body) {
  setSaveState('Saving…');
  try {
    const res = await fetch('/api/revision', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const doc = await res.json();
    if (doc.error) throw new Error(doc.error);
    // keep any newer text still being typed in this page
    for (const [id, t] of saveTimers) if (doc.revisions[id] && REVS[id]) doc.revisions[id].note = REVS[id].note;
    REVS = doc.revisions;
    setSaveState(`Saved · ${Object.keys(REVS).length} notes`);
    renderTree();
  } catch (err) {
    setSaveState('Not saved: ' + err.message, true);
  }
}

function viewOf(id) { return (modalView?.asset.id === id ? modalView : cards.get(id)?.view); }
function viewAngles(id) { const v = viewOf(id); return v ? { yaw_deg: +(v.yaw / DEG).toFixed(1), pitch_deg: +(v.pitch / DEG).toFixed(1), zoom: +v.zoom.toFixed(2) } : undefined; }

function setFlag(id, on) {
  if (on) {
    REVS[id] = { id, note: '', status: 'open' };
    postRevision({ id, note: '', status: 'open', view: viewAngles(id), lighting: describeLighting() });
  } else {
    delete REVS[id];
    postRevision({ id, delete: true });
  }
  refreshEditors(id);
  renderTree();
}

function noteChanged(id, text) {
  if (!REVS[id]) return;
  REVS[id].note = text;
  clearTimeout(saveTimers.get(id));
  setSaveState('Editing…');
  saveTimers.set(id, setTimeout(() => {
    saveTimers.delete(id);
    postRevision({ id, note: REVS[id]?.note ?? '', view: viewAngles(id), lighting: describeLighting() });
  }, 600));
}

function setStatus(id, status) {
  REVS[id].status = status;
  postRevision({ id, status, note: REVS[id].note, view: viewAngles(id), lighting: describeLighting() });
  refreshEditors(id);
}

const STATUS_TEXT = { open: 'open', in_progress: 'in progress', done: 'done', wont_fix: "won't fix" };
// The flag checkbox + note editor for an asset; used by its card and by the inspector.
function buildEditor(asset, host, flagHost) {
  const id = asset.id;
  flagHost.replaceChildren();
  host.replaceChildren();
  const rev = REVS[id];
  const label = el('label');
  const box = el('input'); box.type = 'checkbox'; box.checked = !!rev;
  box.addEventListener('change', () => {
    if (!box.checked && REVS[id]?.note?.trim() && !confirm(`Remove the note for ${id}?\n\n${REVS[id].note}`)) { box.checked = true; return; }
    setFlag(id, box.checked);
    if (box.checked) setTimeout(() => document.querySelector(`[data-note="${CSS.escape(id)}"]`)?.focus(), 0);
  });
  label.append(box, document.createTextNode('Needs revision'));
  flagHost.append(label);
  if (!rev) return;
  flagHost.append(el('span', 'chip ' + rev.status, STATUS_TEXT[rev.status] || rev.status));
  if (rev.model && rev.model !== asset.model) flagHost.append(el('span', 'chip stale', 'model changed'));
  const ta = el('textarea');
  ta.placeholder = "What's wrong with it? Be specific: shape, scale, texture, colour, sprite match, seams…";
  ta.value = rev.note || '';
  ta.dataset.note = id;
  ta.addEventListener('input', () => { noteChanged(id, ta.value); syncNote(id, ta); });
  ta.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Escape') ta.blur(); });
  host.append(ta);
  if (rev.resolution) host.append(el('div', 'res', 'Fixed: ' + rev.resolution + (rev.resolved_model ? `\n→ ${rev.resolved_model}` : '')));
  const acts = el('div', 'acts');
  const btn = (text, fn, title) => { const b = el('button', null, text); if (title) b.title = title; b.addEventListener('click', fn); acts.append(b); };
  if (rev.status === 'done' || rev.status === 'wont_fix') btn('Reopen', () => setStatus(id, 'open'), 'Not fixed yet: back to open (the earlier round is kept in history)');
  else if (rev.status === 'in_progress') btn('Back to open', () => setStatus(id, 'open'));
  if (rev.status !== 'done') btn('Mark done', () => setStatus(id, 'done'), 'The model is fine now');
  host.append(acts);
}
function syncNote(id, source) {
  for (const ta of document.querySelectorAll(`[data-note="${CSS.escape(id)}"]`)) if (ta !== source) ta.value = source.value;
}
function refreshEditors(id) {
  const c = cards.get(id);
  if (c) { buildEditor(c.asset, c.editor, c.flag); c.card.className = cardClass(c.asset); }
  if (modalView?.asset.id === id) buildEditor(modalView.asset, $('#modalEditor'), modalFlagHost);
}

// -------------------------------------------------------------------------------------------- UI: tree
let current = readLocal('ar.folder', 'terrain/FOREST');
let visibleList = [];
function folderKey(a) { return a.category + '/' + a.folder; }
function isFlagged(id) { return !!REVS[id]; }
function isOpen(id) { const s = REVS[id]?.status; return s === 'open' || s === 'in_progress'; }

function renderTree() {
  const t = $('#tree');
  t.replaceChildren();
  const link = (key, text, count, flagged, special) => {
    const a = el('a', (special ? 'special ' : '') + (key === current ? 'sel' : ''));
    a.append(el('span', null, text));
    const right = el('span');
    if (flagged) right.append(el('span', 'f', flagged + ' ⚑'));
    right.prepend(el('span', 'n', count + ' '));
    a.append(right);
    a.addEventListener('click', () => selectFolder(key));
    t.append(a);
  };
  const open = Object.keys(REVS).filter(isOpen).length;
  link('*flagged', 'Flagged for revision', Object.keys(REVS).length, open, true);
  link('*all', 'All assets', ASSETS.length, 0, true);
  for (const g of INDEX.groups) {
    t.append(el('div', 'cat', g.label));
    for (const f of g.families) {
      const key = g.category + '/' + f.family;
      const flagged = ASSETS.filter(a => folderKey(a) === key && isOpen(a.id)).length;
      link(key, f.family === 'ALL' ? 'All ' + g.label.toLowerCase() : f.family, f.count, flagged);
    }
  }
}

function folderAssets(key) {
  if (key === '*all') return ASSETS;
  if (key === '*flagged') return ASSETS.filter(a => isFlagged(a.id));
  return ASSETS.filter(a => folderKey(a) === key);
}
function folderTitle(key) {
  if (key === '*all') return 'All assets';
  if (key === '*flagged') return 'Flagged for revision';
  const [cat, fam] = key.split('/');
  const label = INDEX.groups.find(g => g.category === cat)?.label || cat;
  return fam === 'ALL' ? label : label + ' / ' + fam;
}

function selectFolder(key) {
  current = key;
  writeLocal('ar.folder', key);
  renderTree();
  renderCards();
  $('#grid').scrollTop = 0;
}

function filtered() {
  const q = $('#search').value.trim().toLowerCase();
  const show = $('#show').value;
  return folderAssets(current).filter(a => {
    if (show === 'flagged' && !isFlagged(a.id)) return false;
    if (show === 'open' && !isOpen(a.id)) return false;
    if (show === 'done' && !(isFlagged(a.id) && !isOpen(a.id))) return false;
    if (show === 'unflagged' && isFlagged(a.id)) return false;
    if (!q) return true;
    return [a.id, a.part, a.status, a.source_label, a.recipe, REVS[a.id]?.note].some(s => s && String(s).toLowerCase().includes(q));
  });
}

// ------------------------------------------------------------------------------------------- UI: cards
const io = new IntersectionObserver(entries => {
  for (const e of entries) {
    const id = e.target.dataset.id;
    if (e.isIntersecting) { wanted.add(id); want(id); } else wanted.delete(id);
  }
}, { root: $('#grid'), rootMargin: '900px 0px' });

function cardClass(a) { const r = REVS[a.id]; return 'card' + (r ? ' flagged st-' + r.status : ''); }
function stateText(a) {
  const m = models.get(a.id);
  if (a.kind === 'none') return a.missing ? 'Model file missing' : 'No model yet';
  if (m?.error) return 'Failed to load\n' + m.error;
  return 'Loading…';
}
function updateCardState(id) {
  const c = cards.get(id);
  if (c) c.state.textContent = models.get(id)?.root ? '' : stateText(c.asset);
  if (modalView?.asset.id === id) $('#modalView .state').textContent = models.get(id)?.root ? '' : stateText(modalView.asset);
}
function subText(a) {
  const bits = [];
  if (a.part) bits.push(a.part.replace('_', ' '));
  if (a.kind === 'natural') bits.push('procedural ground' + (a.recipe ? ' · ' + a.recipe : ''));
  if (a.triangles) bits.push(a.triangles >= 1000 ? (a.triangles / 1000).toFixed(1) + 'k tris' : a.triangles + ' tris');
  if (a.light_source) bits.push('lamp ' + a.light_source);
  return bits.join(' · ');
}

function renderCards() {
  const list = filtered();
  visibleList = list;
  io.disconnect();
  wanted.clear();
  queue.length = 0;
  cards.clear();
  const ids = new Set(list.map(a => a.id));
  if (models.size > 260 && [...models.keys()].some(id => !ids.has(id))) disposeAll();
  $('#folderTitle').textContent = folderTitle(current);
  const flagged = list.filter(a => isFlagged(a.id)).length;
  $('#folderInfo').textContent = `${list.length} asset${list.length === 1 ? '' : 's'}` + (flagged ? ` · ${flagged} flagged` : '') + ' · drag a view to rotate, double-click to reset';
  const host = $('#cards');
  host.replaceChildren();
  for (const a of list) {
    const card = el('div', cardClass(a));
    card.dataset.id = a.id;
    const viewEl = el('div', 'view');
    const state = el('div', 'state', stateText(a));
    viewEl.append(state);
    const meta = el('div', 'meta');
    const spr = el('div', 'spr');
    if (a.sprites?.[0]) { const img = el('img'); img.src = a.sprites[0]; img.alt = 'original sprite'; img.title = 'Original X-COM sprite'; img.onload = () => { img.style.width = img.naturalWidth * 2 > 64 ? '64px' : img.naturalWidth * 2 + 'px'; }; spr.append(img); }
    else spr.append(el('span', 'muted small', '—'));
    const txt = el('div', 'txt');
    txt.append(el('div', 'title', a.id.split('/').slice(1).join('/') || a.id), el('div', 'sub', subText(a)));
    meta.append(spr, txt);
    const flag = el('div', 'flagrow');
    const editor = el('div', 'editor');
    const open = el('button', null, '⤢'); open.title = 'Inspect large';
    card.append(viewEl, meta, flag, editor);
    const view = newView(a);
    view.el = viewEl;
    const entry = { asset: a, card, view, state, editor, flag, open };
    cards.set(a.id, entry);
    buildEditor(a, editor, flag);
    meta.append(open);
    open.style.marginLeft = 'auto';
    open.addEventListener('click', () => openModal(a.id));
    bindOrbit(view);
    host.append(card);
    io.observe(card);
    if (models.get(a.id)?.root) state.textContent = '';
  }
  requestRender();
}

// ----------------------------------------------------------------------------------------- inspector
let modalFlagHost = el('div', 'flagrow');
function openModal(id) {
  const a = BY_ID.get(id);
  const from = cards.get(id)?.view;
  modalView = newView(a, from);
  modalView.el = $('#modalView');
  $('#modal').hidden = false;
  $('#modalView').replaceChildren(el('div', 'state', stateText(a)));
  ensureModel(a);
  updateCardState(id);
  const i = visibleList.findIndex(x => x.id === id);
  $('#modalPos').textContent = i >= 0 ? `${i + 1} / ${visibleList.length}` : '';
  $('#modalTitle').textContent = a.id;
  const meta = [folderTitle(folderKey(a)), subText(a), a.status && 'catalog: ' + a.status.replaceAll('_', ' '), a.source_label, a.model_file].filter(Boolean);
  $('#modalMeta').replaceChildren(...meta.map(t => el('div', null, t)));
  const sprites = $('#modalSprites');
  sprites.replaceChildren(...(a.sprites || []).map(u => { const img = el('img'); img.src = u; img.title = u.split('/').pop(); return img; }));
  const side = $('#modalEditor');
  side.replaceChildren();
  modalFlagHost = el('div', 'flagrow');
  side.before(modalFlagHost);
  $('.modal-side').querySelectorAll('.flagrow').forEach(f => { if (f !== modalFlagHost) f.remove(); });
  buildEditor(a, side, modalFlagHost);
  requestRender();
}
function closeModal() {
  if (!modalView) return;
  const id = modalView.asset.id;
  const c = cards.get(id);
  if (c) { c.view.yaw = modalView.yaw; c.view.pitch = modalView.pitch; }
  modalView = null;
  $('#modal').hidden = true;
  refreshEditors(id);
  requestRender();
}
function stepModal(d) {
  if (!modalView) return;
  const i = visibleList.findIndex(x => x.id === modalView.asset.id);
  const next = visibleList[(i + d + visibleList.length) % visibleList.length];
  if (next) { const keep = { yaw: modalView.yaw, pitch: modalView.pitch, zoom: 1 }; openModal(next.id); Object.assign(modalView, keep); requestRender(); }
}

// --------------------------------------------------------------------------------------------- export
function exportCandidates() {
  const withDone = $('#pkgDone').checked;
  return ASSETS.filter(a => REVS[a.id] && (withDone || isOpen(a.id)));
}
function renderExportList() {
  const list = $('#pkgList');
  const prev = new Set([...list.querySelectorAll('input:checked')].map(i => i.value));
  const first = !list.dataset.ready;
  list.replaceChildren();
  let group = null;
  for (const a of exportCandidates()) {
    const g = folderTitle(folderKey(a));
    if (g !== group) { group = g; list.append(el('div', 'grp', g)); }
    const label = el('label');
    const box = el('input'); box.type = 'checkbox'; box.value = a.id;
    box.checked = first ? (current.startsWith('*') || folderKey(a) === current) : prev.has(a.id);
    box.addEventListener('change', countExport);
    const txt = el('div');
    txt.append(el('div', null, a.id), el('div', 'note', REVS[a.id].note || '(no note yet)'));
    label.append(box, txt);
    list.append(label);
  }
  if (!list.children.length) list.append(el('div', 'grp', 'Nothing flagged yet'));
  list.dataset.ready = '1';
  countExport();
}
function countExport() {
  const n = $('#pkgList').querySelectorAll('input:checked').length;
  $('#pkgCount').textContent = `${n} selected`;
  $('#pkgGo').disabled = !n || exporting;
}

function toBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

// Renders one view of a model into a 2D canvas (draw right after render: the WebGL buffer is still there).
function snapshot(model, yaw, pitch, size) {
  const pr = renderer.getPixelRatio();
  const css = size / pr, H = innerHeight;
  const rect = { left: 0, top: 0, right: css, bottom: css, width: css, height: css };
  renderer.setScissorTest(true);
  const view = { asset: model.asset, yaw, pitch, zoom: 1 };
  drawView(view, rect, rect, H);
  const out = document.createElement('canvas');
  out.width = out.height = size;
  out.getContext('2d').drawImage(canvas, 0, 0, size, size, 0, 0, size, size);
  return out;
}

function wrapText(ctx, text, maxWidth) {
  const lines = [];
  for (const para of String(text).split('\n')) {
    let line = '';
    for (const word of para.split(/\s+/)) {
      const test = line ? line + ' ' + word : word;
      if (ctx.measureText(test).width > maxWidth && line) { lines.push(line); line = word; } else line = test;
    }
    lines.push(line);
  }
  return lines;
}

async function loadImage(url) {
  return new Promise(res => { const img = new Image(); img.onload = () => res(img); img.onerror = () => res(null); img.src = url; });
}

async function runExport() {
  const ids = [...$('#pkgList').querySelectorAll('input:checked')].map(i => i.value);
  if (!ids.length) return;
  const progress = $('#pkgProgress');
  const saved = { ...settings };
  const light = $('#pkgLight').value;
  if (light !== 'current') settings.shade = +light;
  const lighting = describeLighting();
  exporting = true;
  countExport();
  canvas.style.visibility = 'hidden';
  const VIEW = 300, items = [];
  try {
    for (let i = 0; i < ids.length; i++) {
      const a = BY_ID.get(ids[i]);
      progress.textContent = `Rendering ${i + 1} / ${ids.length}: ${a.id}`;
      const m = await ensureModel(a).promise;
      const rev = REVS[a.id] || {};
      const yaw0 = (rev.view?.yaw_deg ?? 45) * DEG, pitch = (rev.view?.pitch_deg ?? 30) * DEG;
      const shots = m.root ? [0, 1, 2, 3].map(k => snapshot(m, yaw0 + k * Math.PI / 2, pitch, VIEW)) : [];
      const sprite = a.sprites?.[0] ? await loadImage(a.sprites[0]) : null;
      let glb = null;
      if (m.root && a.kind === 'natural') {
        const helpers = [];
        m.root.traverse(o => { if (o.userData.helper || o.isLight) helpers.push(o); });
        helpers.forEach(h => h.removeFromParent());
        try { glb = toBase64(await new THREE.GLTFExporter().parseAsync(m.root, { binary: true })); }
        finally { helpers.forEach(h => m.root.add(h)); }
      }
      items.push({ a, rev, shots, sprite, glb });
      await new Promise(r => setTimeout(r, 0));
    }
    progress.textContent = 'Composing sheets…';
    const previews = {}, glbs = {};
    for (const it of items) {
      const c = document.createElement('canvas');
      c.width = c.height = VIEW * 2;
      const ctx = c.getContext('2d');
      ctx.fillStyle = '#07090c'; ctx.fillRect(0, 0, c.width, c.height);
      it.shots.forEach((s, k) => ctx.drawImage(s, (k % 2) * VIEW, Math.floor(k / 2) * VIEW));
      if (!it.shots.length) { ctx.fillStyle = '#8592a3'; ctx.font = '20px system-ui'; ctx.fillText('No model yet', 20, 40); }
      previews[it.a.id] = c.toDataURL('image/png');
      if (it.glb) glbs[it.a.id] = it.glb;
    }
    const sheets = composeSheets(items, lighting);
    progress.textContent = 'Writing the zip…';
    const res = await fetch('/api/export', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: $('#pkgName').value.trim(), ids, lighting, sheets, previews, glbs }),
    });
    const out = await res.json();
    if (out.error) throw new Error(out.error);
    progress.replaceChildren(document.createTextNode(`Saved ${out.path} (${(out.size / 1048576).toFixed(1)} MB) · `));
    const dl = el('a', null, 'download'); dl.href = out.url; dl.download = '';
    const reveal = el('a', null, 'show in folder'); reveal.href = '#';
    reveal.addEventListener('click', ev => { ev.preventDefault(); fetch('/api/reveal', { method: 'POST', body: JSON.stringify({ path: out.path }) }); });
    progress.append(dl, document.createTextNode(' · '), reveal);
  } catch (err) {
    progress.textContent = 'Export failed: ' + err.message;
    console.error(err);
  } finally {
    Object.assign(settings, saved);
    exporting = false;
    canvas.style.visibility = '';
    countExport();
    requestRender();
  }
}

function composeSheets(items, lighting) {
  const PER = 8, CELL = 220, SPR = 150, TEXTW = 640, PAD = 16, HEAD = 64;
  const W = PAD * 2 + CELL * 4 + SPR + TEXTW + PAD * 2, ROW = CELL + PAD;
  const pages = [];
  for (let p = 0; p * PER < items.length; p++) {
    const chunk = items.slice(p * PER, p * PER + PER);
    const c = document.createElement('canvas');
    c.width = W; c.height = HEAD + chunk.length * ROW + PAD;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#0e1116'; ctx.fillRect(0, 0, c.width, c.height);
    ctx.fillStyle = '#e0a73a'; ctx.font = 'bold 22px system-ui, sans-serif';
    ctx.fillText(`${$('#pkgName').value.trim() || 'Asset revisions'} — sheet ${p + 1} of ${Math.ceil(items.length / PER)}`, PAD, 32);
    ctx.fillStyle = '#8592a3'; ctx.font = '14px system-ui, sans-serif';
    ctx.fillText(`Four views from the reviewed angle, 90° apart · original X-COM sprite · note · lit like the game: ${lighting}`, PAD, 52);
    chunk.forEach((it, r) => {
      const y = HEAD + r * ROW;
      ctx.fillStyle = '#151a21'; ctx.fillRect(PAD / 2, y - PAD / 2, W - PAD, ROW);
      it.shots.forEach((s, k) => ctx.drawImage(s, PAD + k * CELL, y, CELL - 6, CELL - 6));
      if (!it.shots.length) { ctx.fillStyle = '#8592a3'; ctx.fillText('No model yet', PAD + 10, y + 24); }
      const sx = PAD + CELL * 4 + 8;
      ctx.fillStyle = '#000'; ctx.fillRect(sx, y, SPR - 16, CELL - 6);
      if (it.sprite) {
        const scale = Math.max(1, Math.floor(Math.min((SPR - 24) / it.sprite.naturalWidth, (CELL - 14) / it.sprite.naturalHeight)));
        const w = it.sprite.naturalWidth * scale, h = it.sprite.naturalHeight * scale;
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(it.sprite, sx + (SPR - 16 - w) / 2, y + (CELL - 6 - h) / 2, w, h);
        ctx.imageSmoothingEnabled = true;
      }
      const tx = sx + SPR + 4;
      ctx.fillStyle = '#d8dee6'; ctx.font = 'bold 17px system-ui, sans-serif';
      ctx.fillText(it.a.id, tx, y + 20);
      ctx.fillStyle = '#8592a3'; ctx.font = '13px system-ui, sans-serif';
      ctx.fillText([folderTitle(folderKey(it.a)), subText(it.a)].filter(Boolean).join(' · '), tx, y + 40);
      ctx.fillStyle = '#f0c060'; ctx.font = '15px system-ui, sans-serif';
      const lines = wrapText(ctx, it.rev.note || '(no note)', TEXTW - 10);
      lines.slice(0, 9).forEach((line, i) => ctx.fillText(line, tx, y + 66 + i * 19));
      if (lines.length > 9) ctx.fillText('… (full note in README.md)', tx, y + 66 + 9 * 19);
    });
    pages.push(c.toDataURL('image/png'));
  }
  return pages;
}

// ------------------------------------------------------------------------------------------------ boot
function syncLightingUI() {
  $('#shade').value = settings.shade;
  $('#shadeOut').textContent = settings.shade + (settings.shade === 15 ? ' · night' : settings.shade === 0 ? ' · day' : '');
  $('#lamps').checked = settings.lamps;
  $('#squad').checked = settings.squad;
}
function onLighting() {
  settings.shade = +$('#shade').value;
  settings.lamps = $('#lamps').checked;
  settings.squad = $('#squad').checked;
  writeLocal('ar.settings', settings);
  syncLightingUI();
  requestRender();
}

async function boot() {
  syncLightingUI();
  ['#shade', '#lamps', '#squad'].forEach(s => $(s).addEventListener('input', onLighting));
  let searchTimer;
  $('#search').addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(renderCards, 200); });
  $('#show').addEventListener('change', renderCards);
  $('#grid').addEventListener('scroll', requestRender, { passive: true });
  addEventListener('resize', requestRender);
  new ResizeObserver(requestRender).observe($('#cards'));
  bindModalOrbit();
  $('#closeBtn').addEventListener('click', closeModal);
  $('#prevBtn').addEventListener('click', () => stepModal(-1));
  $('#nextBtn').addEventListener('click', () => stepModal(1));
  $('#modal').addEventListener('pointerdown', ev => { if (ev.target === $('#modal')) closeModal(); });
  addEventListener('keydown', ev => {
    if (ev.target.matches?.('textarea, input[type=text], input[type=search]')) return;
    if (!$('#exportDlg').hidden && ev.key === 'Escape') { $('#exportDlg').hidden = true; requestRender(); return; }
    if (!modalView) return;
    if (ev.key === 'Escape') closeModal();
    if (ev.key === 'ArrowLeft') stepModal(-1);
    if (ev.key === 'ArrowRight') stepModal(1);
  });
  $('#exportBtn').addEventListener('click', () => { closeModal(); $('#pkgList').dataset.ready = ''; renderExportList(); $('#pkgProgress').textContent = ''; $('#exportDlg').hidden = false; requestRender(); });
  $('#pkgCancel').addEventListener('click', () => { $('#exportDlg').hidden = true; requestRender(); });
  $('#pkgDone').addEventListener('change', renderExportList);
  $('#pkgAll').addEventListener('click', () => { $('#pkgList').querySelectorAll('input').forEach(i => i.checked = true); countExport(); });
  $('#pkgNone').addEventListener('click', () => { $('#pkgList').querySelectorAll('input').forEach(i => i.checked = false); countExport(); });
  $('#pkgGo').addEventListener('click', runExport);

  const [idx, revs] = await Promise.all([fetch('/api/index').then(r => r.json()), fetch('/api/revisions').then(r => r.json())]);
  INDEX = idx; ASSETS = idx.assets; BY_ID = new Map(ASSETS.map(a => [a.id, a])); REVS = revs.revisions || {};
  setSaveState(Object.keys(REVS).length ? `${Object.keys(REVS).length} notes` : 'No notes yet');
  if (!current.startsWith('*') && !ASSETS.some(a => folderKey(a) === current)) current = 'terrain/FOREST';
  renderTree();
  renderCards();
}

// The inspector element keeps one set of listeners that steer the current modalView.
function bindModalOrbit() {
  const proxy = { el: $('#modalView') };
  for (const k of ['yaw', 'pitch', 'zoom']) Object.defineProperty(proxy, k, { get: () => modalView?.[k] ?? 0, set: v => { if (modalView) modalView[k] = v; } });
  bindOrbit(proxy, { wheel: true });
}

boot().catch(err => { setSaveState('Failed to start: ' + err.message, true); console.error(err); });
