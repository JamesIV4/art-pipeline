# Asset conventions

These hold for every asset built with `kits/lowpoly` (trick-or-treat style). XCOM-style PBR assets
share the axes and export rules; their extra conventions are at the end.

## Space

- 1 Blender unit = 1 m. Z up in Blender.
- Origin at the ground contact point. Floating assets (pickups, sky pieces, hanging lanterns) use
  their centre or hang point and opt out of the ground gate (`"floating": true` or a floating prefix).
- Front faces Blender **-Y**, which becomes glTF/Godot **+Z** (`Node3D.MODEL_FRONT`).
- Pick a hero scale reference per game and keep it in the brief: in trick-or-treat the kid is 1.1 m,
  a door 2.2 m, a porch step 0.2 m, and the gameplay camera sits about 15 m away, 35 degrees down.
  The review sheet's scale post is `scale_figure_height_m` tall.

## Colour and material

- Colour comes only from the palette: every face's `Tint` UV (UV2) sits on a palette cell centre.
  UV2.x = material layer index + cell u, UV2.y = cell v. `glow_*` cells are emissive in game, with the
  flicker amount in `palette_emit.png` alpha. See `techniques/palette-tint-uv.md`.
- Every face also names a painted material layer (`mat=`); the material tiles in metres through
  `UVMap` (UV) using the face's projection (`box`, `cyl`, `sphere`). Re-run `K.project()` after deforms
  or merges if textures stretch. See `techniques/painted-material-arrays.md`.
- Bake per-vertex AO (`K.bake_ao`) after the final merge or parenting; it exports as COLOR_0.
- Each lane owns one palette row; never insert cells mid-row in a shipped palette (later columns shift).

## Structure

- Sockets: empties named `socket_<anchor>` (placement points the game reads).
- Character / creature parts: named child objects with their origin at the joint and identity
  rotation; parent with `attach()` (no parent-inverse) so the glTF has clean local translations.
- Collision is catalog data (`collision`, `radius`, `height`, `collision_top`, `walkable`), not mesh
  data; boxes from the mesh AABB pick up plants, mirrors and ladders, so set them explicitly.

## Export

- glTF separate (`.gltf` + `.bin`), Y-up, `export_apply`, no materials, `TEXCOORD_0` + `TEXCOORD_1`,
  normals, active colour attribute (AO), extras on. The game applies the shared toon material.
- Path: `<models_out>/<catalog path>.gltf` (`K.export(objects, "props/pumpkin_a")`).
- A build id goes into the scene extras so Godot re-imports every rebuild.
- Review-only builds (`--lift`, `--combined`) must be rebuilt without the flag before hand-off.

## Quality bar (low-poly contract)

1. Reads instantly as a silhouette from the gameplay camera.
2. Palette only. Rounded and bevelled: visible facets are deliberate, never noise.
3. Toy-like proportions; nothing sharp, scary or realistic unless the game's direction says so.
4. Within the triangle budget, every required socket and part present, origin at ground.
5. Passing the gates earns a review, not an approval (see quality-contract.md).

## XCOM / PBR conventions (kits/xcom, tools/textures)

- Principled BSDF with image-backed maps only; OpenGL (+Y) normal maps; ORM packed Non-Color
  (R AO, G roughness, B metal). Real bevels plus weighted normals on manufactured edges.
- Alpha MASK (scissor) for foliage, never blended stacks. Triangulate before baking tangents.
- Skinned parts: join only after weighting, at most 4 normalised weights per vertex.
- Runtime textures are 8-bit lossless WebP, uniquely named by role and version; shared textures are
  content-addressed and immutable (`techniques/texture-compression.md`).
- Variants are new descriptive suffixes (`<NNN>.<variant>.gltf`, `opus-v1`, `v1b`), never overwrites;
  superseded variants are marked, not deleted. Seal dependency hashes before the final hash.
