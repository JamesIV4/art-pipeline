# Atlas packing: swatch/props atlases, fit and lathe mapping, cutout atlases

## What it is

The atlas conventions XCOM used to keep props within 1-3 material surfaces,
plus the rules for cutout atlases (leaves, hair, scatter) and for array atlases
in the layered merge.

## Why

Small coloured parts (cash register, keypad, goods prints, logos, hose rubber,
chrome) each wanted their own material; that blew the per-asset surface budget.
Atlases with no gutters bled colours between cells in mips; dense cutout atlases
mipped into solid blocks; generated cutouts showed coloured halos.

## How: cell atlases for props (urban26/27/28, frniture, items)

- 2048 px atlas on an 8x8 grid of 256 px units; cells of 256 or 512 px.
- Each cell is filled edge to edge with its own colour/content; UVs use only the
  cell's inner rectangle with a 7% margin per cell (mip-bleed guard).
- Faces are tagged in the builder as `<atlas>|<cell>[|group]`; each part/group
  is fit-mapped into its cell; the finalizer keeps those preset UVs.
- Extra UV modes, both atlas-gated:
  - lathe-in-cell (bottles, tins, drums, tyres): u = turn, v = height/arc length
    mapped into the cell; tread/sidewall maps use separate u/v texel sizes;
  - `@top` groups force a top-down projection on heightfield produce so steep
    lump faces do not jump to other cells; the produce cell is painted from the
    same deterministic lump list that built the geometry (registered texture).
- Swatch atlas (items): each cell is one flat source colour plus a subtle CC0
  micro-surface (Metal032 for metal and lightly for paint, Rubber004 for grips);
  smart-project each swatch group into its cell; overlapping islands are fine in
  uniform cells.
- Calibrate cells, not the atlas: multiply affected cells by per-channel
  source/Godot ratios from a colour lab capture (e.g. a drum ratio^0.8 because
  half its sprite is baked shadow).
- When an atlas fills, start a second atlas rather than adding materials.

## How: cutout atlases (leaves, hair, scatter)

- Content has gaps: less foliage on the texture, more cards in the mesh.
- Dilate/bleed colour under alpha; harden alpha for generated cutouts
  (XCOM `install_scatter_atlas.py`) so fringes never halo.
- Re-pack generated cells by connected components if they cross the
  generator's quadrant lines.
- Hair: islands by type (opaque base, breakup, wispy hairline), root alpha fade
  over the first 15%, random UV mirroring across cards (`hair-cards.md`).

## How: arrays for the layered merge

One array per size class (next power of two >= largest member; upsample only).
Texture sets cost VRAM per class; re-tints are free rows. See
`layered-merges.md`.

## Gate: `atlas_uvs_inside_cells`

Every atlas triangle's UVs must lie inside its cell's inner rectangle (account
for exported v = 1 - v). XCOM also checked lathe v bounds and that clip
geometry matches between item and standalone files. The atlas gate caught 2 m
crate lids mapped outside a 1.5 m atlas extent.

## Physical honesty

- Record the native crop texels and physical period per region; a 1024 quarter
  of a 2048 atlas is not "native 2k". XCOM used a 0.968 inner fraction per
  1024 quarter in shared 2048 atlases.
- Unique baked maps need UV island margins; seamless physical-scale maps for
  modular surfaces.

## Gotchas

- ORM checks must sample the texels the mesh uses, not the whole atlas (an
  unused metal cell failed a non-metal asset).
- True-metal cells in a goods atlas turned the sprite's light lids dark gray;
  decide per cell.
- Satin "fake metal" cells linger in old atlases; convert when revisited.
- Glass stays its own BLEND material even when everything else is atlased.

## Source

- XCOM `art/team/environment_replacement/batches/urban26_opus/research.md`,
  `urban27_opus/research.md`, `urban28_opus/research.md`
- XCOM `art/team/frniture_opus55/batch01-03/research.md`
- XCOM `art/team/items_opus55/research.md` (swatch atlas)
- XCOM `art/team/stairs_opus/batch01/research.md` (ORM sampling)
- XCOM `docs/GROUND_MATERIALS.md` (scatter atlases), `art/review/perf_lab/REPORT.md`
