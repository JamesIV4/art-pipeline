# XCOM 2026-10-16: in-game GPU cost of shadow and lighting settings

## Method

`rt/tools/sweep_render_cost.py`: one game run per scene (1920x1080, 3D view,
shipped render profile, scatter vegetation on); render panel values changed one
at a time through `OXP_RENDER_STEPS`; GPU ms averaged over 60 frames after a
settle (viewport render timer; RTX 5060 Ti). Delta vs the mean of first and last
baseline runs (they agreed within 0.05 ms). Noise 0.05-0.1 ms.
Shipped profile at the time: ambient #4f6995 x2.22, sun #897f6a x3.44, SSAO
intensity 16 radius 1.61, SSIL on, glow on, MSAA 8x, 8192 shadow maps, PSSM4,
vignette/grain/sharpen post.

## Results (GPU ms delta: farmland / forest / urban fire night)

Baselines 5.38 / 3.65 / 4.45.
- Biggest savings: MSAA off -1.77 / -0.61 / -1.02 (2x: -1.34 / -0.33 / -0.46);
  depth AO off -0.62 / -0.52 / -0.68; shadows off -0.45 / 0 / -0.56; SSIL off
  -0.25 / +0.04 / -0.44; all AO/GI/glow off -1.46 / -1.18 / -1.40.
- Small: shadow map 4096/2048/1024 -0.05 to -0.17; glow off -0.09 to -0.31; post
  fx off ~-0.1; never-seen fog ~0.
- Costs: shadow filter Ultra +1.01 / +0.19 / +0.25 (Low/Medium oddly +0.33-0.38
  on farmland); SDFGI +0.33-0.43; TAA +0.24-0.39; SSR +0.12-0.34; contact
  shadows +0.20 farmland; fire lights +0.15-0.21; heat haze +0.17; volumetric
  fog +0.47 in the night scene.
- Presets: LOW -1.52 / -0.69 / -0.72; LOWEST (no shadows/AO/glow, MSAA off)
  1.94 / 1.24 / 1.75 ms total.

## Takeaways for art/pipeline

- Asset-side costs (materials, triangles) are small compared with MSAA and AO
  choices; do not trade art quality for frame time before checking these.
- Shadow map resolution is nearly free to lower; filter quality is not.
- Camera-centred GI (SDFGI, volumetric fog) is ineffective with a distant ortho
  camera (earlier panel measurements: SDFGI showed almost nothing at 250 m).
- Earlier farm-map panel numbers (1280x800): shipped 0.51 ms, SSAO 0.62, SSIL
  0.74, VoxelGI 0.78 (6.3 s blocking runtime bake), SDFGI 0.98.

## Sources

XCOM `docs/RENDER_COST_SHADOWS_LIGHTING.md`, `docs/BATTLESCAPE_3D_INTEGRATION.md`
(render debug panel).
