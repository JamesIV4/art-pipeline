# Trailer shots: scripted capture, per-shot clips, review, user-picked worlds

## What it is

A game trailer (and its marketing stills) recorded from the game itself: a scripted cinematic
director inside the game plays named shots (camera path, kid behaviour, caption), Godot's movie
writer records each shot as its own clip, every clip is reviewed from sampled frames before anything
is assembled, and the clips are cut together with one music bed. Tools: `tools/marketing/`
(`trailer_clips.ps1`, `shot_options.ps1`).

## Why

- trick-or-treat's first trailer passes were one ~10 minute full-reel render. Every problem (thorn
  vines through the cosy opening, a wrong caption, a camera inside a hedge) cost a full re-render, and
  the user found the problems by watching. Per-shot clips make a fix cost one ~15 s shot.
- The user's standing rule (2026-10-26): check every shot procedurally before assembling, and
  selectively redo only the bad ones. Trailer shots get the most scrutiny.
- A trailer must show the real game. The user rejected debug shortcuts in shots: freeing a town or
  killing a nest with a debug command, a fabricated candy fountain that was never collected.

## How

1. **Director in the game** (trick-or-treat: `native/src/play/festival_cine.cpp`). Each shot is a
   struct: name, caption, duration, `setup()` (place the kid, props, monsters), `tick(t)` (bot input),
   `cam(t, fov)` (camera transform), plus flags: its own world `seed`, `gameplay` (the normal camera
   rig and HUD instead of a scripted camera), `trailer` (in the reel or stills only), `vines` (hide
   hazards for travelling shots), `face_camera`, `caption_top` (a menu fills the middle), `avoid` (pull
   the camera in front of obstacles), `cutout` (occluder dither, below). An `ORDER` list sets the reel.
2. **Deterministic worlds.** Cine runs default to one fixed seed (101), so re-recording one shot gives
   the same world as the rest. A shot that needs a better spot gets its own seed; switching worlds
   mid-reel reloads the world, so look up areas and positions inside `setup()` at run time (pointers
   or positions captured when the reel was built go stale), and **wait a few frames after loading
   before `setup()`**: the old world's physics bodies stay in the space until they are freed at the
   end of the frame, and clear-view raycasts run against both worlds otherwise.
3. **Camera lanes, not hope.** Before a shot runs, search candidate camera offsets (sides x
   distances) and keep the first whose camera-to-subject and camera-to-target rays are clear at the
   start, middle and end of the move (`cine_lane`, `cine_clear` both ways so a camera starting inside a
   post still counts as blocked). Check the frame edges too: rays from the lens a little forward and to
   each side catch a lamp post or tree trunk filling one side of the picture.
4. **Things without colliders.** Raycasts miss decorations with no physics body (thorn tendrils).
   Measure distance to them analytically (`thorn_distance`) and, for the kid's spot and the camera
   path, hide the offenders for the shot (`hide_thorns_near`). Hidden must also mean inert: disable
   the hitbox and damage, not only the mesh (the user called this out).
5. **Occluder cutout instead of dodging.** For close, moving shots the simplest robust fix is the
   gameplay camera's occluder cutout (the toon shader dithers anything between camera and kid): enable
   it for the shot (`s.cutout`, `FestivalCamera::set_cinematic_cutout`) and let the camera hold its path
   (`avoid = false`).
6. **Context in shots.** Nests need their monsters around them (spawn the brood for the shot), the
   kid fires real fireballs at a real target, candy pickups are the street's own candy.
7. **Lens.** The toy-lens DOF blurred the kid in close shots: per shot, turn near blur off and push
   far blur beyond the subject (`max(32, dist + 12)` m).
8. **Record per shot** (`trailer_clips.ps1 -Stage record`): `--write-movie clip.avi --fixed-fps 30
   -- --cine=<shot> --cine-no-music` at 2560 x 1440 through a temporary `override.cfg`. Music is off
   so one continuous bed goes under the whole cut.
9. **Review every clip** (`-Stage review`): six frames tiled 3 x 2 per clip; read each against its
   caption and intent (blocked lens, wrong subject, hazards, blur, clipping, empty frames). Re-record
   only failures.
10. **Let the user pick the world** when a shot's location is a taste call: `shot_options.ps1` renders
    the shot in 6-8 seeds and tiles labelled stills. The user picks by seed, the seed goes into the
    shot definition, and the option clip can be copied straight into the clips folder.
11. **Assemble** (`-Stage assemble`): trim the 0.75 s world-loading head, 0.3 s fade in / 0.4 s fade
    out per shot (dip to black), concat, loop the game's music at its in-game level (-9 dB) mixed with
    the shots' effects (`amix normalize=0`), fade the bed in 1 s / out 2 s. Shots that go off the boil
    partway are cut short with `-MaxLength` rather than re-recorded.

## Gotchas

- **Never cut Godot's output pipe short.** `& godot ... | Select-Object -First 2` kills Godot
  when it has the lines it wants, before the movie writer finalises the AVI: ffprobe then reports
  `duration=N/A` and frame tiling fails ("Impossible to set time base"). Collect the whole output, then
  filter.
- Run long passes as a **detached process** (`Start-Process` with a log). Harness background shells
  die when tool connections drop. Kill Godot before rebuilding a GDExtension: the running movie
  holds the DLL.
- The user watches the recording window and often picks or rejects before the sheet is done. Don't
  block the session waiting on option renders; start them detached and respond to the user.
- A captured `home` pointer or a position computed at reel-build time is wrong once a shot loads its
  own world (one crash came from this). Look things up in `setup()`.
- Ask what "seed N" means if two option sheets are in play; number options per sheet and label each
  with its seed.
- Hide the controls hint in scripted/gameplay clips; captions need `z_index` above HUD panels.
- Remove `override.cfg` after every run (the scripts do it in `finally`); a leftover one changes the
  game's resolution for the user.
- Copy decisions: caption wording matters to the user ("On Halloween night", not "One Halloween night").

## Source

trick-or-treat, 2026-10-26: `native/src/play/festival_cine.cpp` (director, shots, `cine_lane`,
`cine_clear`, per-shot seeds and `cine_wait_`), `festival_camera.*` (`set_cinematic_cutout`),
`monsters.*` (`set_hidden`, `thorn_distance`, `hide_thorns_near`, `fill_nest_near`); session scripts
generalised into `tools/marketing/`. Related: `godot-review-captures.md`, `review-sheets.md`.
