# FM synth audio (OPL2 / AdLib style sound effects and music)

## What it is

All sound effects and music are rendered offline in Python by a small two-operator FM synth that
models the parts of the Yamaha YM3812 (OPL2) that give early-90s AdLib game audio its character.
Effects are note sequences stepped at 140 Hz ("id style" sound-effect playback); music is a short
looping tune with lead, bass, arpeggio and simple synth drums.

## Why

The user's audio target is Commander Keen 4/5 era AdLib FM: 2-operator OPL instruments, pitch
stepped at 140 Hz, bell-like "ladder" pickups, glassy sparkles, boingy sweeps. Square-wave PC
speaker chiptune was tried and rejected. Rendering offline keeps audio original (no samples),
reproducible and tiny.

## How

tools/audio/fm_synth.py:

- `Inst(m_char, c_char, m_scale, c_scale, m_ad, c_ad, m_sr, c_sr, m_wave, c_wave, feedback)`
  uses the OPL register layout: characteristic byte (bit 7 tremolo, bit 6 vibrato, bit 5
  sustain, low nibble frequency multiplier from MULT table), scale byte (top 2 bits key-scale
  level, low 6 bits total level at 0.75 dB per step), attack/decay and sustain/release nibbles,
  waveforms 0-3 (sine, half sine, abs sine, quarter pulse), feedback 0-7.
- Envelopes in the attenuation domain (dB) at approximate OPL rates (attack table in ms, decay
  `39280.64 / 2^(r-1)` ms over 96 dB); percussive vs sustained mode; retrigger for music.
- Modulator -> carrier phase modulation (`carrier(phase + mod * 4 pi)`), modulator feedback via
  two fixed-point iterations, vibrato 6.1 Hz +/- 0.4%, tremolo 3.7 Hz about 1 dB, KSL from the
  F-number ROM.
- `render_notes(inst, block, notes)`: one F-number per 1/140 s tick, 0 = key off (exact id style).
- `write_wav`: normalise, gain, a 3-tap low-pass for "AdLib card warmth", 16-bit mono 44.1 kHz.

tools/audio/make_sfx.py: original instruments (PING bright bell, GLASS sparkle, ORGAN warm
sweep, BOING spring, HOP, THUMP, STEP, BELL inharmonic chime, CRUNCH feedback-6 noise) and a
`seq(inst, [(midi or 0, ticks)])` helper where consecutive notes keep the key down (pitch steps)
and 0 is a rest. `glide()` makes stepped sweeps, `mix()` sequences, `layer()` stacks. Examples:
candy = PING 74, rest, 78, rest, 81; jump = HOP glide 46 -> 40 -> 64; doorbell = two BELL notes.

tools/audio/make_music.py: 32 bars at 132 BPM in E minor (Em C D B7 / Am Em C D), FM lead with
vibrato and feedback 4, oom-pah bass (root, octave, fifth), 16th-note bell arpeggio, counter-melody
on the variation pass, synth kick/snare/hat; every event index wraps modulo the loop length so the
tail spills into the start and the loop is seamless.

## Gotchas

- Pickup feedback must scale with success, not climb per pickup: the user rejected candy sounds
  that rise in pitch with each piece (and candy wobble near the player). Plain candy has one fixed
  ladder; a clean full run earns a separate combo chime.
- Keep the 140 Hz stepping; smooth glides lose the era's character.
- Normalise per file but set a lower gain for rumbles (thunder 0.4 vs 0.55).
- Original instruments and melodies only; do not transcribe Keen tunes or patches.

## Source

trick-or-treat: art/tools/fm_synth.py, make_sfx.py, make_music.py, game/scripts/audio.gd,
README "Notes and deviations", user memory art-direction.md (audio target, rejections).
