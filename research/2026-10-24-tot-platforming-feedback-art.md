# 2026-10-24 trick-or-treat: platforming and feedback research, as it shapes art

The game's platforming design was grounded in published platformer work (README "Platforming
design"); several findings set art requirements: candy placement, guidance, landing readability
and reward feedback. Source: trick-or-treat README.md, user memory art-direction.md,
native/src/gen/candy.cpp, game/shaders/candy_beam.gdshader, candy_outline.gdshader,
art/tools/make_sfx.py.

## Research used and the art consequence

- Designed jump metrics (Pittman, "Building a Better Jump", GDC 2016): 1.9 m jump height, 0.37 s
  to apex, 1.6x heavier fall, early release cuts the rise. Art: walkable prop tops must sit at
  heights the metrics can reach; candy runs are laid along the simulated arc, so prop collision tops
  must be true (techniques/walkable-props-collision.md).
- Forgiveness (Thorson, "Celeste & Forgiveness"): coyote time, buffering, apex half gravity,
  ceiling correction, ledge-lip pop. The candy magnet widens horizontal reach, height still earned.
- Ledge grab (Super Mario 64, Spyro): only real ledges count (room on top, a lip within reach) so
  fence rails and trim never snag. Art: ledges need clean lips; thin trim must not look grabbable.
- Readable landings (Iwata Asks: Super Mario 3D Land): drop shadow under the kid and a glow under
  every floating candy. Art: the candy beam column (techniques/candy-beam-column.md).
- Unambiguous jumps ("Lessons from Suzy Cube: Measuring Up"): landings within 0.3 m of the single
  jump's peak become planned wing-flap jumps.
- Rhythm groups with rests (Smith et al., Launchpad): each candy run is one jump's beats, evenly
  spaced in time, at least 4 m from the next run.
- Introduce, develop, twist, conclude (Hayashida, Super Mario 3D Land): each lot starts with its
  lowest platform, chains higher, hangs a bonus above a platform top and ends on the porch roof.
- No jumping for stairs: steps and kerbs up to 0.45 m are walked up. Art: kerbs and porch steps
  stay under that height or are deliberate platforms.
- Feedback proportional to success (Kao 2020; Kao et al. 2024): no per-candy pitch climb or wobble;
  a small combo meter counts quick pickups; a clean full run earns a chime and a sparkle burst.

## User decisions (2026-10-24)

- Guidance is a subtle swirling glowing magic trail down the street to every doorstep, fading once
  that bell rings. Never a walk-along breadcrumb trail of candy.
- Candy mix revised: lots of easy ground candy in loose clusters around yards and sidewalks;
  jumping required only for chains (rhythm-group runs) and higher-value pieces; avoid piling candy
  on porch roofs.
- Candy glow is an outline around each piece, not a halo.
- The user asked for more "fun" but rejected candy wobble/jiggle near the player and pickup sounds
  that climb in pitch. Direction: scale feedback with success instead of amplifying everything.

## Art requirements that fall out

- Pickup VFX grow with value: glow pop + twinkles (plain), magic swirl (chocolate), star ring +
  confetti (lollipop), sparkle fountain (golden); candy flies to the bucket with a sparkle trail in
  its own colour.
- Pickup sound: one fixed bell ladder per candy kind; combo and run-complete sounds are separate.
- Tiered candy sizes (0.24 m everyday to 0.6 m lollipop) and outline colours make value readable
  before the jump.
- Trampolines as vertical toys: big ones launch 17 m/s, minis 14 m/s next to roofs; hold or timed
  press springs 1.45x higher. Art: unmistakable mats and pads, top height equal to collision_top.
