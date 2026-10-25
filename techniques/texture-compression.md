# Runtime texture format, Godot import policy and content-addressed sharing

## What it is

Three coordinated steps applied after every export: (1) finalize runtime
textures as 8-bit lossless WebP and rewrite every reference, (2) enforce a Godot
texture import policy (mipmaps, normal-map flag, compression mode), and
(3) deduplicate byte-identical textures into immutable content-addressed shared
folders.

## Why

- Repository/download size: PNG runtime textures and repeated per-asset copies.
  WebP lossless shrinks disk size; it does NOT reduce VRAM.
- GPU: perf lab found shipped terrain textures were lossless without mipmaps.
  Mipmaps + VRAM block compression cut tactical-zoom GPU by 0.8-1.5 ms (about
  half) and texture memory 155 -> 104 MB (base map), 388 -> 159 MB (mixed).
- Without mipmaps, normal and albedo maps alias into sparkle at game zoom (seen
  in the unit lab, whose imports had `mipmaps/generate=false`).
- Concurrent scene imports reset texture options, so a policy must be re-applied.

## How: finalize (XCOM `art/tools/compress_project_textures.py`, port `tools/textures/`)

- Preview: `python compress_project_textures.py` (counts, sizes).
- Apply: `--apply --allow-8bit --replace-existing --backup-dir <NEW dir outside repo>`.
- 8-bit RGBA encodes lossless with `exact=True` (keeps hidden RGB under
  transparent pixels), then decodes and compares pixels before accepting.
- 16-bit PNGs are first decoded by Godot (so runtime pixels match what Godot
  would have produced), then encoded; this reduces source precision. Keep
  high-precision originals outside the runtime tree.
- Rewrites glTF images to `EXT_texture_webp`, Godot resource paths, preserves
  import UIDs and array slice counts, refreshes dependency seals; backs up PNGs
  plus changed metadata with `conversion-report.json` (hashes, bit depths,
  before/after sizes). Archives PNGs only after encode + reference updates
  succeed. Conflicting WebP stops the run unless `--replace-existing`.
- WebP max dimension 16,383 px: split oversized array atlases; never downscale
  silently.
- Exporters call the finalizer automatically before saving the Blender source
  (Blender may need `XCOM_TEXTURE_PYTHON` pointing at a Python with Pillow).

## How: import policy (XCOM `art/tools/texture_import_policy.py`)

Rewrites only the policy keys in each `.import` [params]:
`mipmaps/generate=true`, `mipmaps/limit=-1`, `compress/normal_map=1` for
`*_normal*` files (0 otherwise), plus the compression mode. `--check` exits
non-zero on drift; the review gate re-applies it after every import and
re-imports if anything changed. Array textures skip the normal/detect keys.
A file must be imported once before the policy can be applied (missing keys =
error, by design).

Compression mode history (decide per project): 2026-10-02 XCOM enabled VRAM
compression + mipmaps on all 1,395 textures (BC5 for normals, ORM forced BC1 in
the lab) for the GPU win above. From 2026-10-03 the policy file sets
`compress/mode=0` (Lossless) + mipmaps and `detect_3d/compress_to=0` so Detect
3D cannot override it. Note: an import type named `CompressedTexture2D` appears
in Lossless mode too; it does not mean block compression is on. Recommended
default for a new game: mipmaps always; VRAM compression (BC7/BC5 normal) for
large terrain/environment sets when GPU or memory bound; lossless for UI, small
atlases with flat swatch cells, and masks where block artefacts show.

## How: deduplicate (XCOM `art/tools/deduplicate_project_textures.py`)

- Groups textures by (content SHA-256, import settings, extension); identical
  groups move to `assets/textures/shared/<hash(content+settings+ext)>/<name>`.
- Rewrites glTF image paths and dependency seals, Godot paths and UIDs, layered
  material signatures; stops on colliding layered signatures.
- Shared files are immutable: export changed pixels to a NEW file. This keeps
  old model snapshots valid.
- `assets/texture_aliases.json` lets Blender relink old paths when reopening
  sources. Report: `deduplication-report.json`.
- Missing `.import` sidecars are skipped: import new textures before deduping.

## Rules

- Every delivered texture is 8-bit WebP (lossless for normal/ORM/masks; albedo
  lossless or high quality); no 16-bit maps, no PNG copies in runtime assets,
  never commit `.godot/` caches. Intermediates can be anything outside the tree.
- Reference unchanged maps by their current path; never copy maps to give an
  asset its own filenames.
- Scripts that read textures must fall back to `.webp` and read
  `EXT_texture_webp` (no `source` field).

## Gotchas

- Mipmaps generated in sRGB space dim high-contrast textures 5-10% at distance.
- Old lossless cache files under `.godot/imported` waste disk only.
- One item referenced a .jpg; gates should flag non-WebP runtime textures.
- Run the finalizer outside the project lock holder or it deadlocks
  (XCOM's gate retries it before taking the lock).

## Source

- XCOM `art/README.md` ("Saving runtime textures", "Sharing identical runtime
  textures")
- XCOM `art/tools/compress_project_textures.py`, `texture_import_policy.py`,
  `deduplicate_project_textures.py`, `root_gate_batch.py` (docstrings/code)
- XCOM `art/review/perf_lab/REPORT.md` finding 5
- XCOM `art/review/opus_revision_queue.md` (renderer DONE row, texture format row)
- XCOM `art/team/ORCHESTRATION_OPUS55.md` ("Texture format", "WebP")
- XCOM `art/team/tools/previewer_lighting/CHECKPOINT.md` (unit-lab mipmaps)
