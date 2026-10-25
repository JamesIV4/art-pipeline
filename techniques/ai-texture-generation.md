# AI texture generation (painted tiling sources with provenance)

## What it is

Painted tiling material sources are generated one image per call with Codex's built-in image_gen
tool (signed-in ChatGPT account, no API key), copied into the repo with a provenance sidecar, then
processed by make_materials.py. Prompts are a fixed style string plus a per-layer subject.

## Why

The textured low-poly look needs about 30 consistent hand-painted surfaces. Generating them from
one shared style string keeps them coherent; provenance keeps their origin honest (AI-made
texture material, not original source art) and reproducible.

## How

tools/imagegen/codex_imagegen.ps1:

    powershell -NoProfile -File tools/imagegen/codex_imagegen.ps1 -PromptFile p.txt -Out <path>.png
        [-Reference a.png,b.png] [-Transparent]

- Runs `codex exec --json --sandbox read-only --skip-git-repo-check` in an empty temp folder,
  instructing it to call image_gen exactly once and reply DONE; reference images via `-i`.
- Finds the thread id in the JSONL events, takes the newest image from
  `~/.codex/generated_images/<thread>`, copies it to `-Out` (refuses to overwrite, must be inside
  the workspace), and writes `<Out>.provenance.json`: tool, codex version, UTC time, thread id,
  source file, sha256, full prompt, references with hashes, transparency flag, and a note that it
  is AI-generated.

Style string used for every layer (materials.json `style`): "Seamless tileable square texture,
top-down orthographic view, hand-painted stylized game texture for a cozy toy-like low-poly game,
soft painterly brush strokes, even flat lighting with no cast shadows or vignette, neutral light
grey colour with only subtle hue variation so it can be tinted later, no text, no border, edges
must tile seamlessly. Subject: ..."

Prompting lessons (2026-10-24 pass, 27 layers, 5 retries):

- Count the structure: "exactly 6 boards", "exactly 7 rows", "exactly 8 courses", "exactly 4
  identical straight parallel ribs ... groove exactly at the left and right edges". Counts that
  divide the tile make the seam blend harmless.
- Say where the edges fall: "perfect 3 by 3 grid filling the tile ... half a gap along each outer
  edge".
- Say what to avoid: "one continuous uniform piece, no seams, folds or lines" (denim had a seam);
  "no tufted cushion grid, no shiny specular highlights" (vinyl baked highlights that did not
  tile); "soft horizontal brushed streaks running evenly across the whole tile" (faint mottled metal
  blew up into purple blotches after levelling).
- Ask for neutral grey with value-only variation (leaves) so the palette does the colour.

Bookkeeping: keep rejected attempts in `source/rejected/` and unmodified generator output in
`source/raw/` when a post-process (np.roll offset, patching a corner artifact) was applied; add a
`postprocess` field to the final provenance describing the change and which file the hash covers.
Record every layer's attempts, verdict and weaknesses in a CHECKPOINT table.

## Gotchas

- The generator often ignores "faint" and "subtle" (felt stitching, fabric plaid stronger than
  asked) and drifts realistic (paper crinkle, felt fibres). Judge after levelling, in engine.
- Grass came out slightly side-on tufts rather than strictly top-down; acceptable when stylised.
- Generated seams can sit off-grid; offsetting the image half a period puts the seam inside
  continuous content. Patch leftover checker artifacts by copying a neighbouring feature.
- Never present outputs as original art; keep the provenance with the file.

## Source

trick-or-treat: art/tools/codex_imagegen.ps1, art/materials/CHECKPOINT.md,
art/materials/materials.json, art/materials/source/*.provenance.json (pavers, pumpkin postprocess).
