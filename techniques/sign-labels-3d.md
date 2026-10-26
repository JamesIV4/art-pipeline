# Text on signs (Label3D fitted to its board)

## What it is

World-space lettering (shop signs, street signposts, thank-you signs) as Godot `Label3D` measured
with its own font, so the text always sits inside its board: long names widen the board rather than
shrink the text.

## Why

The user flagged signs whose text spilled off the board, then signpost text that was too small and
dark, then long names that had been shrunk to fit: "Long names should make the signpost wider there,
not shrink text".

## How

- Measure: width = (`font.get_string_size(text, size).x` + outline) x `pixel_size`; height =
  `font.get_height(size) x 0.82` + outline (cap height, not the full line box).
- Signposts: fixed letter height; the arm/board width comes from the measured width plus padding, so a
  long street name gets a longer board. White text with a dark outline on a 0.4 m tall board read at
  street distance.
- Fixed-size boards (shop fronts with a `SignSpec width/height`): shrink `pixel_size` only (never grow)
  to fit `max_w x max_h`.
- Measure after the font and size are set, before placing the board.

## Gotchas

- Measuring without the outline lets outlined text touch the board edge.
- Shrinking to fit is only for fixed boards. On anything that can grow (signpost arms), the user
  rejected shrunken text: keep the letter height and widen the board.

## Source

trick-or-treat, 2026-10-26: `native/src/core/fonts.h` (`label_width`, `fit_label`),
`native/src/world/world_streamer.cpp` (signpost arms), `native/src/gen/neighborhood_generator.cpp`
(`build_thanks_sign`), `town.cpp` (`SignSpec`).
