# Glow cells and bloom calibration (emissive parts on assets)

## What it is

Emissive parts of assets (lantern panes, jack faces, eyes, flames, runes, candy knots) are faces
painted with palette glow cells. The shader emits `cell_rgb * 2.6 * flicker * glow_boost`, which
then goes through glow/bloom and tonemapping. Choosing the cell, its brightness and what surrounds
it decides whether the part reads as a coloured light or a white blob.

## Why

Bloom and tonemapping shift bright saturated emission toward yellow-white and spread it over
neighbouring detail. Several lanes lost faces, pupils and colour this way; the fixes were all
asset-side choices worth reusing.

## How

Rules distilled from engine passes:

1. Dimmer cells often read more coloured. A jack bulb shell at #ea6a1c and #c24c10 bloomed to
   yellow-white and swallowed its face; `glow_jack_shell #a0400c` (flicker 0.08) kept the globe
   orange and the pale face (`glow_jack_face #ffd864`) readable.
2. Fire reads as a hot core plus darker licks: wand flame core on glow_jack_hot / glow_jack with
   glow_jack_shell on the lobe crests and tip. All-glow_jack read lemon-yellow; glow_lantern_red
   read peach-white.
3. Two-tone panes: lantern glass as an amber rim (glow_lantern) around a pale hot core (glow_lamp)
   with dark mullions kept visible; one flat bright pane loses the frame.
4. A glowing chamber under a dark floor: a fully glowing bucket interior washed out the candy heap.
5. Separate glow from neighbours by value: a gold cup next to a yellow flame went to the darker
   foil_gold_dark; a cream stripe was invisible on gold under the candy shader (use warm white).
6. Glow eyes: bloom swallows pupils (bat, spider, cat, skeleton teal pupils). Accept "glowing eyes"
   at distance, or put the cute pupil and glint on non-glow cells over a smaller glow.
7. Flicker lives in the emit alpha (0.6 for jacks and candles, 0.15 lanterns, 0 steady windows).
   Small dim cells contribute little flicker; put the flicker on the large hot bands.
8. Locked/unlit state: a whole asset half can be dimmed with the `glow_boost` instance uniform
   (travel gate lantern at 0.12 while the area is locked). Put every switch-on glow in one asset or
   part so one uniform controls it; keep the other half free of glow cells (verified by listing the
   cells an export uses, `inspect_gltf.py`).
9. Non-glow whites at night: lolly_white read pink under warm light; trim_white held. Cream number
   plates glared; caramel/brass did not.

## Gotchas

- Workbench shows glow cells as tan or orange; judge only in engine, and at night.
- Studio light plus glow over-blooms (golden apple, lolly jack, golden bar); night is the reference.
- A glow halo of many small emissive faces (cauldron potion and bubbles) blooms into one mass;
  space them out or dim some.
- The cart doormat's burlap looked nearly emissive next to a glow ring at night: emissive edges
  raise the apparent brightness of neighbours.
- Specular glints on chamfers and leaves can read as unwanted glow (lamp plinth rim, wreath leaves).

## Source

trick-or-treat: game/shaders/toon.gdshader, art/palette/palette.json (row 8 glow cells, row 10),
CHECKPOINTs of decor/batch03 (string_jack, lamps), play_props/batch03 (fire_wand),
characters_candy/batch02 (bucket), candy_variety/batch03 (golden twist), monsters/batch03,
decor_ground/batch03 (cat), landmarks/batch03 (gate, mailbox), vines/batch03, yard_street/batch02.
