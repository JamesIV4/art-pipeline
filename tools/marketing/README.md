# tools/marketing/

Trailer and icon tooling that drives a game's own capture modes. The game supplies the shots (a
scripted cinematic mode) and the renders; these scripts record, review, assemble and cut out. The
method and its pitfalls are in `techniques/trailer-shot-capture.md` and
`techniques/engine-rendered-icon.md`.

| File | What | Needs |
|---|---|---|
| `trailer_clips.ps1` | `-Stage record` one movie-writer clip per shot; `review` a 3 x 2 frame sheet per clip; `assemble` trim, dip to black, concat, one music bed | ffmpeg/ffprobe on PATH; a game that plays one named shot from user args and quits |
| `shot_options.ps1` | one clip + labelled still per seed for one shot, tiled into an options sheet for the user to pick a world | same |
| `matte_icon.py` | black/white difference matte -> centred transparent square icon, plus a 1024/256/64/32 px sizes sheet | Pillow |

Game-side contract (trick-or-treat implements it in `native/src/play/festival_cine.cpp` and
`festival_game.cpp`):

- `--cine=<shot>` plays one shot and quits; `--cine=reel` plays them all; `--cine-no-music` mutes the
  game's music so one bed can be laid under the whole trailer; `--cine-clean` drops captions for
  stills; a fixed default world seed so a re-recorded shot matches the rest of the reel; optional
  per-shot `--cine-seed=<n>` to try a shot in another world.
- `--preview=<res://gltf> --icon` renders one framed shot of an asset on black with no HUD;
  `--icon-white` the same on white (the pair feeds `matte_icon.py`).

Outputs default to `art/review/trailer/` in the game (gitignore it; clips are ~70 MB each at
2560 x 1440 MJPEG). The finished trailer goes wherever `-Output` says, e.g. `marketing/`.
