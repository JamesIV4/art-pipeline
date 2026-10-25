"""Origin: S:/Repos/trick-or-treat/art/tools/make_music.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. The song is trick-or-treat's; treat as an example to edit.

Renders the neighborhood background music with the FM synth into game/assets/music/.

An original bouncy, spooky-but-cute tune in the style of early-90s AdLib platformer soundtracks:
FM lead with vibrato, oom-pah plucked bass, 16th-note bell arpeggios and simple synth drums.
32 bars at 132 BPM, looping seamlessly.  Run: python art/tools/make_music.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fm_synth as F  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline_paths as P  # noqa: E402
OUT = P.path("music_out")
BPM = 132.0
BEAT = 60.0 / BPM
BARS = 32
TOTAL = BARS * 4 * BEAT
N = int(round(TOTAL * F.RATE))

LEAD = F.Inst(0x61, 0x21, 0x1C, 0x02, 0xE5, 0xF4, 0x34, 0x27, c_wave=0, feedback=4)
BASS = F.Inst(0x21, 0x01, 0x14, 0x00, 0xF8, 0xF6, 0x47, 0x68, feedback=5)
ARP = F.Inst(0x02, 0x41, 0xC8, 0x10, 0xD6, 0xF5, 0xE9, 0xF9)
COUNTER = F.Inst(0x22, 0x61, 0x22, 0x08, 0xA4, 0xB4, 0x46, 0x46, feedback=2)

CHORDS = {
    "Em": (40, [64, 67, 71]), "C": (36, [60, 64, 67]), "D": (38, [62, 66, 69]),
    "B7": (35, [63, 66, 69]), "Am": (33, [57, 60, 64]),
}
A_CHORDS = ["Em", "C", "D", "B7", "Em", "C", "Am", "B7"]
B_CHORDS = ["Am", "Em", "C", "D", "Am", "Em", "C", "B7"]
T = None  # tie: hold the previous note
A_MEL = [
    [76, T, 71, T, 74, 76, 79, T], [79, 76, 72, T, 71, T, 0, 0],
    [74, T, 69, T, 72, 74, 78, T], [78, 76, 75, T, 71, T, 0, 0],
    [76, T, 79, T, 83, T, 81, 79], [79, 76, 72, T, 76, T, 79, T],
    [81, T, 79, 76, 74, 72, 71, 69], [71, T, 75, T, 78, T, 71, 0],
]
B_MEL = [
    [69, 72, 76, 72, 69, 72, 76, 81], [79, 76, 71, 76, 79, T, 76, 0],
    [72, 76, 79, 76, 72, 76, 79, 84], [83, T, 81, T, 78, T, 74, 0],
    [69, 72, 76, 81, 79, 76, 72, 69], [71, T, 76, T, 79, T, 83, T],
    [84, T, 83, 81, 79, T, 78, T], [75, T, 78, T, 71, T, 0, 0],
]
SONG = [("A", 0), ("B", 0), ("A", 1), ("B", 1)]


def part(inst, events, gate_frac=0.85):
    """events: (start_beat, length_beats, midi). Every note retriggers the envelope."""
    freq = np.full(N, F.note_freq(60))
    gate = np.zeros(N, dtype=np.int8)
    retrig = np.zeros(N, dtype=np.int8)
    for start, length, midi in events:
        a = int(start * BEAT * F.RATE) % N
        b = a + int(length * BEAT * F.RATE)
        g = a + int(length * gate_frac * BEAT * F.RATE)
        idx = np.arange(a, b) % N
        freq[idx] = F.note_freq(midi)
        gidx = np.arange(a, g) % N
        gate[gidx] = 1
        retrig[a] = 1
    return F.render_voice(inst, freq, gate, retrig)


def drums():
    out = np.zeros(N)
    rng = np.random.default_rng(3)

    def add(beat, sig):
        a = int(beat * BEAT * F.RATE)
        for i, v in enumerate(sig):
            out[(a + i) % N] += v

    t_k = np.arange(int(0.16 * F.RATE)) / F.RATE
    kick = np.sin(2 * np.pi * np.cumsum(np.linspace(130, 42, len(t_k))) / F.RATE) * np.exp(-t_k * 22)
    t_s = np.arange(int(0.13 * F.RATE)) / F.RATE
    snare = (rng.standard_normal(len(t_s)) * 0.6 + np.sin(2 * np.pi * 190 * t_s) * 0.5) * np.exp(-t_s * 28)
    t_h = np.arange(int(0.035 * F.RATE)) / F.RATE
    hat_noise = rng.standard_normal(len(t_h))
    hat = (hat_noise - np.convolve(hat_noise, np.ones(4) / 4, mode="same")) * np.exp(-t_h * 90) * 0.5
    for bar in range(BARS):
        b0 = bar * 4
        fill = bar % 8 == 7
        add(b0, kick)
        add(b0 + 2, kick)
        if bar % 2 == 1:
            add(b0 + 3.5, kick * 0.8)
        add(b0 + 1, snare)
        if fill:
            for k in range(4):
                add(b0 + 2 + k * 0.25 + (0.0 if k < 3 else 0.0), snare * (0.6 + 0.12 * k))
            add(b0 + 3, snare)
        else:
            add(b0 + 3, snare)
        for k in range(8):
            add(b0 + k * 0.5, hat * (1.0 if k % 2 else 0.6))
    return out


def main():
    lead, bass, arp, counter = [], [], [], []
    bar = 0
    for section, variation in SONG:
        chords = A_CHORDS if section == "A" else B_CHORDS
        mel = A_MEL if section == "A" else B_MEL
        for i in range(8):
            root, tones = CHORDS[chords[i]]
            b0 = bar * 4
            # Lead: eighths with ties.
            k = 0
            notes = mel[i]
            while k < 8:
                m = notes[k]
                if m is None or m == 0:
                    k += 1
                    continue
                length = 1
                while k + length < 8 and notes[k + length] is None:
                    length += 1
                lead.append((b0 + k * 0.5, length * 0.5, m + (12 if variation and section == "B" and i % 4 == 3 else 0)))
                k += length
            # Bass: oom-pah with a fifth.
            pattern = [0, 12, 7, 12, 0, 12, 7, 12]
            for s, iv in enumerate(pattern):
                bass.append((b0 + s * 0.5, 0.5, root + iv))
            # Arp: 16ths over the chord, up and back.
            cyc = tones + [tones[0] + 12] + tones[::-1][1:]
            for s in range(16):
                arp.append((b0 + s * 0.25, 0.25, cyc[s % len(cyc)] + 12))
            # Counter-melody on the variation pass: sustained chord thirds.
            if variation:
                counter.append((b0, 2.0, tones[1]))
                counter.append((b0 + 2, 2.0, tones[2]))
            bar += 1
    mixd = (part(LEAD, lead, 0.88) * 1.0 + part(BASS, bass, 0.7) * 0.85 + part(ARP, arp, 0.5) * 0.28 +
            part(COUNTER, counter, 0.95) * 0.3 + drums() * 0.55)
    OUT.mkdir(parents=True, exist_ok=True)
    F.write_wav(OUT / "neighborhood.wav", mixd, gain=0.7)
    print(f"neighborhood.wav {TOTAL:.1f}s")


if __name__ == "__main__":
    main()
