# XCOM 2026-10-07: recurring failure patterns in the root revision queue

Distilled from `art/review/opus_revision_queue.md` (~110 rows, 2026-10-01 to
10-07; root's queue of issues found at the Godot visual gate, plus runtime and
UI items). Columns used: asset(s), lane, severity (major = stays unapproved;
polish = approved, improve later; consistency; minor; paused/done), issue,
evidence image path. Only art-pipeline patterns are summarised here.

## 1. Colour drift under game lighting (most frequent, mostly polish)

The single largest class. Hue/saturation shifts relative to the sprite, read in
the Godot gate light:
- Earth/soil tones lean warm: red-orange terracotta vs dark chocolate (XBASE1
  000-005, U_BASE 061/060, debris mounds), lemon sand vs ochre (DESERT 017),
  ochre rocks vs red-brown (MARS 004/005).
- Saturated darks read pale: deep magenta dome as pale lavender, deep red glow
  floor as pink, dark teal ground as mint, dark char as brown, saturated blue
  engine glow blowing out to white (reduce emission energy, bluer colour).
- Neutrals drift: laminate near white, frame gray bluish, foot pads pale gray vs
  dark gray, hull surfaces plain gray.
- Skin/flesh: pale pink vs muted mauve, "hot-pink rubber balls" at joints.
Lesson: calibrate hue/saturation/contrast in a Godot colour lab before export;
never absolute brightness; emissive needs its own check; batch hue passes per
family after any global lighting change.

## 2. Source misreading of form (major)

- Multi-tile composites not assembled before modelling: a 2x2 fallen log built
  as two thin logs plus two rocks; tree tiles given a ground disc instead of the
  full grass tile drawn.
- Missing source features: raised mound arc around a dome; lost meander relief
  from a UV mirror; cockpit strips and lights; panel lines on craft.
- Proportion errors: jars 18% narrower than sprite; hedge stump footprint too
  big; roof slivers wider than drawn; props too thin vs the sprite's chunky read.
- Interpreted features that are really material: fissures and crevasses (dark
  lines) wrongly expected as attachments.
Lesson: decode actual MAP placements and composite neighbours first; measure
silhouettes numerically against the sprite (IoU, row widths).

## 3. Family consistency and modular interfaces (major/consistency)

- Stairs: every stair must have exactly 5 steps per tile (an earlier six-tread
  reading was wrong) and a sqrt(6) level, not 3 m.
- Walls/door heads/columns end 5 mm below LEVEL so they never share a plane with
  the slab above; mechanical pass over older walls.
- Mirrored drafts: 14 north walls built on the south edge; stairs rising the
  wrong way.
- Geometry poking through neighbours -> offline modular-fit clipping; floors with
  designed gaps failing the edge rule (rule vs model decision deferred).
- Newer shore library forced rebuild of older lips for consistency.
- Terrain tops below the game's walking height (crates 0.63 m vs 1.22 m) make
  units float: models must match gameplay heights.
Lesson: codify family dimension rules (steps, wall top, insets, bands) in a gate,
not just in prose.

## 4. Material physically wrong (polish, systemic)

- Metals faked as satin dielectric (metallic 0.3-0.35) before the reflection sky;
  re-author to metallic 1 when touched.
- Generated PBR metallic leaking onto skin/hair (silvery faces).
- Foliage matte/gray (uniform roughness ~0.76) -> waxy recipe; flat hedge tops
  glare.
- Texture stretch on broken tops; glass that grays what is behind it.
- Non-WebP textures slipping in (a .jpg; unit-lab PNGs).

## 5. Rig/animation contact (major for units)

Weapon sockets on the back of the hand (palm-normal sign bug); support hand 2.6-
5.5 cm short of the fore-end; thumbs inside grips; robes/armour crossing stocks;
knees 3 cm into the floor when kneeling; ragdoll head 0.40 m past the tile;
corpses identical; spring-bone jitter at speed (frame-rate dependent sim, shelved).
Lesson: numeric contact gates (palm to grip <= 1 cm, penetration <= 5 mm) and
per-rig socket offsets; fixed-timestep simulation for secondary motion.

## 6. Export/runtime handoff gaps

Animated tiles needing per-record (not per-material-name) animation; autotiling
variants (flat-end hull pieces next to doors, room-slab variants, ground-only
rubble) that the renderer must select; LOD seam cracks; stale opus-v1 exports
that failed `uvs_inside_0_1` must never be registered; morph default weights
exported as 1.0 (both looks shown) instead of 0.
Lesson: every variant contract goes into glTF extras and a sidecar the runtime
reads, and the catalog must say which variant the runtime should pick.

## Process observations

- Severity discipline worked: majors blocked approval; polish was batched into
  family passes.
- "Resolved" rows record the policy change that made the issue moot (5-material
  cap after the perf lab) instead of deleting history.
- Many rows bundle evidence paths to the exact verified sheet; that made later
  passes fast.
- User pauses (units until new models, fit work) are recorded inline so workers
  do not resume paused lanes.
