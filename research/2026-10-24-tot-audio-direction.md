# 2026-10-24 trick-or-treat: audio direction (AdLib FM)

Source: user memory art-direction.md; trick-or-treat art/tools/fm_synth.py, make_sfx.py,
make_music.py; README "Notes and deviations" and "Platforming design".

## Decision

- Target: Commander Keen 4/5 style AdLib FM sound: 2-operator OPL2 instruments, 140 Hz note-step
  sound effects, bell-like pickup ladders, glassy sparkles, boingy sweeps.
- Rejected by the user: square-wave PC-speaker chiptune.
- Everything rendered offline into WAV by an in-repo FM synth; all instruments and melodies original.

## What the synth models (and why it matters for the sound)

- Modulator -> carrier phase modulation with OPL frequency multipliers, total level (0.75 dB
  steps), four waveforms, feedback; this is the "AdLib" timbre.
- OPL-rate ADSR in the attenuation domain, percussive vs sustained, key-scale level.
- id-style sound effects: one frequency number per 1/140 s tick, 0 = key off. Pitch stepping at
  140 Hz is the era's signature; smooth glides sound modern.
- Tremolo 3.7 Hz, vibrato 6.1 Hz; a 3-tap low-pass on output for analogue warmth.

## Sound set (about 40 effects)

- Pickups as staccato bell ladders (PING): candy 74 / 78 / 81; chocolate adds an 86; lollipop a
  fast GLASS run; golden an ORGAN glide 60 -> 84 then GLASS sparkle.
- Movement: jump (HOP glide 46 -> 40 -> 64), flap, bounce, land, ground pound, two footsteps.
- House events: doorbell (two inharmonic BELL notes), cleared, night bell, thunder (filtered noise).
- Combat, progress and menus, the ride-on car: each a short layered seq of the same 9 instruments.
- Music: 32 bars at 132 BPM, E minor (Em C D B7 / Am Em C D), FM lead with vibrato, oom-pah bass,
  16th bell arpeggio, counter-melody on the second pass, synth drums; loop-seamless by wrapping
  every event modulo the loop length.

## Feedback rule (from the platforming research)

- No per-pickup pitch climb: the user rejected pickup sounds rising with each candy. Fixed ladder
  per kind; a separate combo and run-complete chime rewards clean runs (feedback proportional to
  success).

## For future games

Keep the synth and instrument-register style; write new original instruments and tunes per game;
decide early between FM (warm, bell-like) and other period styles with the user before building a
full set.
