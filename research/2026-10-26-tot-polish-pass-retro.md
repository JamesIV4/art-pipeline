# 2026-10-26 trick-or-treat: polish pass, trailer and icon retro

One long session after the v3 art pass: costumes matched to a reference sheet, movement and VFX
tweaks, cleared-house feedback, signs, clouds, trampolines, then a full trailer and stills re-shoot
and a game icon. Source: the session's user feedback and the trick-or-treat working tree.

## Art and feel decisions (user feedback, in order)

- **Costumes** (`techniques/character-costume-fidelity-pass.md`): the reference sheet showed the very
  costumes, so the user chose "follow the image" (keep face, bucket, wand). Then: no wings on ghost,
  witch or pumpkin; wingless costumes double jump and hover with **magic dust and no ring**; witch
  hair redone; no hair poking through the pumpkin helmet; cat tail a continuous S with a gentle
  snake-like swish travelling down its length (a toon-shader `tail_wave` instance uniform, not bones).
- **Rings removed**: the user disliked expanding circles on the magic spin, double jump and glide.
- **Cleared house**: a small light in an already lit area was confusing; lights out was rejected
  because it makes streets (and whole town buildings) dark and un-cosy. Chosen: the porch dims a
  little ("1") and a "Thank you!" sign with its own little lantern appears on the door ("4").
- **Signs**: text must fit the board; signposts white, taller text; long names widen the board
  (`techniques/sign-labels-3d.md`).
- **Candy**: licorice twist replaced by a Swedish fish (rounded top: the first one was "too
  angular"); the default costume's bucket shows the 3D candy too, filling with the wallet.
- **Clouds**: "cuter and bigger" remodel and texture were rejected ("I like the old model better");
  the old model stays, with 16 clouds. Boxy artefacts on the clouds came from **shadow-map stepping
  on their own cast shadows**: turning cloud shadow casting off fixed it, a sky-shader hash change did
  not (reverted). Clouds must not follow the player's height; follow only the ground position, lazily.
- **Trampolines** (big and mini) must not clip into other props: placement checks a footprint
  against lot edges, oriented boxes and props (`Yard::clear_of_solids`, r 2.2 m big, 0.95 m mini).
- **Grass ramp** removed entirely (it led onto a porch roof), and every marketing shot showing it.

## Trailer (`techniques/trailer-shot-capture.md`)

- Final cut: 20 shots, 1:37, 2560 x 1440 at 30 fps, one -9 dB music bed. Opening caption
  "On Halloween night, ring every doorbell".
- Shots the user re-chose from seed option sheets: doorbell 109, monsters 110, town 103, car 103
  (with play_drive), aerial "But monsters have moved in" 103 with four nests of different monster
  kinds, three monsters each, strung along the bending street; bucket 104 with no camera avoidance
  and the occluder cutout.
- Rejected content: debug kills / town freeing, a fabricated candy fountain, kid blurred by DOF,
  kid standing in a thorn vine, cameras inside hedges, houses and the kid's head, a giant candy
  floating through the lens. Added on request: "Find hidden costumes" lineup, "Spend candy to upgrade
  your abilities" (shop UI, caption at the top).
- Pipeline lessons: per-shot clips, frame-sheet review, the movie-writer pipe gotcha, waiting frames
  after a per-shot world load, stale pointers after reloads, detached renders.

## Upscalers (rejected for now)

Asked for DLSS, FSR 3 and FSR 4. Findings (Oct 2026): Godot 4.7 stable's `Viewport.Scaling3DMode` is
only Bilinear, FSR 1, FSR 2.2, MetalFX spatial/temporal and Nearest. No GDExtension route exists
until a custom upscaler API lands (godotengine/godot PR 114670, open, moved from the 4.7 milestone to
4.x). The FSR 3.1 PR (111631) will not be merged in its form; FSR 4 is DX12-only and RDNA 4 only;
DLSS needs device extensions enabled at Vulkan device creation, which a plugin cannot do, and NVIDIA
is reported to be working on its own Streamline integration. Decision: the user removed upscaling
entirely; the 3D view always renders at the window's size. Revisit when the API ships.

## Icon (`techniques/engine-rendered-icon.md`)

The game's own happy jack-o'-lantern, rendered in engine on black and white and matted. Accepted:
pumpkin only (no backdrop or moon), straight on, slightly low, 14 degree lens.
