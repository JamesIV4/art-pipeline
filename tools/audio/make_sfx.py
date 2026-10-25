"""Origin: S:/Repos/trick-or-treat/art/tools/make_sfx.py (imported 2026-10-25).
Changed: game paths come from tools/pipeline_paths.py (ART_GAME_ROOT / art/pipeline.json); logic unchanged. Effect definitions are trick-or-treat's; treat as an example to edit.

Renders the game's sound effects with the FM synth (fm_synth.py) into game/assets/sfx/*.wav.

Style target: early-90s AdLib platformer collectibles (Commander Keen 4/5 era): two-operator FM
instruments, pitch stepped at 140 Hz, staccato "ladder" pickups that ring like bells, glassy
sparkles, boingy sweeps. All instruments and note patterns here are original.
Run: python art/tools/make_sfx.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fm_synth as F  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline_paths as P  # noqa: E402
OUT = P.path("sfx_out")
PER = int(round(F.RATE * F.TICK))

# ---------------------------------------------------------------- instruments (original)
PING = F.Inst(0x02, 0x41, 0xC4, 0x06, 0xD6, 0xF5, 0xE9, 0xF9)  # bright ringing bell
GLASS = F.Inst(0x45, 0xC2, 0x04, 0x02, 0xF8, 0xF7, 0xE8, 0xC9)  # glassy sparkle
ORGAN = F.Inst(0x22, 0x21, 0x14, 0x02, 0x96, 0xA6, 0x6F, 0x4F, feedback=3)  # warm sweep
BOING = F.Inst(0x01, 0x12, 0x26, 0x00, 0xE2, 0xF2, 0x84, 0xA6)  # springy body
HOP = F.Inst(0x03, 0x11, 0x1C, 0x00, 0xF5, 0xF3, 0x27, 0xF8)  # jump
THUMP = F.Inst(0x01, 0x01, 0x0C, 0x00, 0xFF, 0xF4, 0x0F, 0xF5, m_wave=1)
STEP = F.Inst(0x02, 0x12, 0x4A, 0x04, 0x92, 0x64, 0x54, 0x7C)
BELL = F.Inst(0x07, 0x02, 0x0E, 0x02, 0xF4, 0xF2, 0x55, 0x54)  # inharmonic door chime
CRUNCH = F.Inst(0x0F, 0x01, 0x00, 0x00, 0xFF, 0xF6, 0x0A, 0x08, m_wave=2, feedback=6)


def seq(inst, items, legato=True, tail=0.35):
    """items: list of (midi or 0 for a rest, ticks). Consecutive notes keep the key down (pitch
    steps like the 140 Hz sound-effect players); a rest is a key-off."""
    freq, gate = [], []
    last = 60.0
    for midi, ticks in items:
        f = F.note_freq(midi) if midi else F.note_freq(last)
        if midi:
            last = midi
        freq += [f] * (ticks * PER)
        gate += [1 if midi else 0] * (ticks * PER)
    freq += [F.note_freq(last)] * int(tail * F.RATE)
    gate += [0] * int(tail * F.RATE)
    return F.render_voice(inst, np.array(freq), np.array(gate, dtype=np.int8))


def glide(m0, m1, ticks):
    return [(m0 + (m1 - m0) * i / max(ticks - 1, 1), 1) for i in range(ticks)]


def mix(*parts, gap=0.0):
    out = np.zeros(0)
    for p in parts:
        out = np.concatenate([out, p, np.zeros(int(gap * F.RATE))])
    return out


def layer(*parts):
    """Plays parts at the same time (mix() plays them one after another)."""
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


def crackle(ticks, lo, hi, seed):
    rng = np.random.default_rng(seed)
    items = []
    for _ in range(ticks):
        items.append((int(rng.integers(lo, hi)), 1) if rng.random() < 0.6 else (0, 1))
    return items


def rumble(seconds=2.6):
    rng = np.random.default_rng(7)
    n = int(seconds * F.RATE)
    w = np.cumsum(rng.standard_normal(n))
    w -= np.convolve(w, np.ones(400) / 400, mode="same")
    t = np.linspace(0, 1, n)
    env = np.sin(np.pi * t) ** 1.5 * (0.7 + 0.3 * np.sin(t * 40))
    return w * env


SOUNDS = {
    # Pickups: staccato bell ladders.
    "candy": lambda: seq(PING, [(74, 3), (0, 1), (78, 3), (0, 2), (81, 5)]),
    "chocolate": lambda: seq(PING, [(74, 3), (0, 1), (78, 3), (0, 1), (81, 3), (0, 2), (86, 7)]),
    "lollipop": lambda: seq(GLASS, [(84, 1), (85, 1), (86, 1), (0, 1), (88, 1), (89, 1), (90, 2), (0, 1), (92, 2), (93, 3), (95, 6)]),
    "golden": lambda: mix(seq(ORGAN, glide(60, 84, 44), tail=0.05),
                          seq(GLASS, [(96, 2), (0, 2), (91, 2), (0, 2), (96, 2), (0, 2), (100, 8)])),
    "combo": lambda: seq(PING, [(74, 2), (78, 2), (81, 2), (86, 2), (90, 2), (93, 2), (98, 6)]),
    "treats": lambda: seq(GLASS, [(96, 2), (0, 1), (93, 2), (0, 1), (91, 2), (0, 1), (88, 2), (0, 1), (86, 2), (0, 1), (91, 2), (95, 2), (98, 6)]),
    # Movement.
    "jump": lambda: seq(HOP, glide(46, 40, 6) + glide(40, 64, 14), tail=0.15),
    "flap": lambda: seq(BOING, glide(57, 69, 4) + [(0, 1)] + glide(61, 74, 4) + [(0, 1)] + glide(65, 79, 5), tail=0.15),
    "bounce": lambda: seq(BOING, glide(62, 36, 11) + glide(36, 70, 13), tail=0.2),
    "land": lambda: seq(THUMP, glide(40, 24, 9), tail=0.1),
    "pound": lambda: mix(seq(CRUNCH, [(m, 1) for m in (52, 40, 47, 35, 44, 31, 38, 28, 33, 26)], tail=0.25)),
    "step_a": lambda: seq(STEP, [(55, 3)], tail=0.08),
    "step_b": lambda: seq(STEP, [(48, 4)], tail=0.08),
    # House events.
    "doorbell": lambda: mix(seq(BELL, [(81, 20)], tail=0.05), seq(BELL, [(77, 30)], tail=0.9)),
    "cleared": lambda: seq(ORGAN, [(72, 7), (0, 1), (76, 7), (0, 1), (79, 7), (0, 3), (76, 5), (0, 1), (79, 4), (84, 16)], tail=0.6),
    "night_bell": lambda: mix(*[seq(BELL, [(50, 50)], tail=0.4) for _ in range(3)]),
    "thunder": rumble,
    # Combat.
    "fire": lambda: layer(seq(HOP, glide(50, 78, 7), tail=0.08), seq(CRUNCH, [(m, 1) for m in (72, 68, 64, 61, 58, 55)], tail=0.1) * 0.5),
    "blast": lambda: layer(seq(THUMP, glide(38, 18, 16), tail=0.2), seq(CRUNCH, [(m, 1) for m in (56, 50, 46, 42, 38, 35, 32, 30, 28)], tail=0.3) * 0.7),
    "hit": lambda: seq(BOING, glide(72, 58, 4), tail=0.08),
    "hit_kill": lambda: layer(seq(BOING, glide(55, 82, 5), tail=0.05), seq(GLASS, [(0, 3), (91, 2), (96, 4)], tail=0.2)),
    "fizzle": lambda: seq(CRUNCH, [(62, 1), (57, 1), (53, 2)], tail=0.08),
    "hurt": lambda: layer(seq(ORGAN, glide(76, 50, 10), tail=0.1), seq(THUMP, [(36, 3)], tail=0.1) * 0.6),
    "spill": lambda: seq(GLASS, [(96, 1), (0, 1), (93, 1), (0, 1), (91, 1), (0, 1), (88, 1), (0, 1), (86, 1), (0, 1), (84, 1), (0, 1), (81, 2)], tail=0.2),
    "telegraph": lambda: seq(PING, [(86, 1), (0, 1), (86, 1)], tail=0.1),
    "monster_pop": lambda: layer(seq(BOING, glide(55, 80, 6), tail=0.05), seq(GLASS, [(0, 4), (91, 3)], tail=0.2)),
    "nest_break": lambda: layer(seq(CRUNCH, [(m, 1) for m in (60, 55, 58, 50, 53, 45, 48, 40, 43, 36, 38, 32)], tail=0.3),
                                seq(ORGAN, [(0, 6), (67, 3), (71, 3), (74, 8)], tail=0.4) * 0.8),
    "vine_burn": lambda: layer(seq(CRUNCH, crackle(22, 62, 84, 3), tail=0.15) * 0.8, seq(ORGAN, glide(55, 43, 18), tail=0.2) * 0.5),
    "throw": lambda: seq(HOP, glide(60, 74, 5), tail=0.06),
    "puff": lambda: layer(seq(GLASS, [(60, 2), (55, 3)], tail=0.15), seq(CRUNCH, [(70, 1), (66, 1), (62, 1)], tail=0.1) * 0.4),
    "spawn": lambda: seq(ORGAN, glide(40, 52, 6) + glide(52, 46, 4), tail=0.15),
    # Progress and menus.
    "freed": lambda: layer(seq(ORGAN, [(72, 5), (0, 1), (76, 5), (0, 1), (79, 5), (0, 1), (84, 8), (0, 2), (79, 4), (0, 1), (84, 16)], tail=0.6),
                           seq(GLASS, [(0, 30), (96, 2), (0, 2), (100, 2), (0, 2), (103, 6)], tail=0.4) * 0.7),
    "menu": lambda: seq(PING, [(79, 2), (86, 3)], tail=0.15),
    "denied": lambda: seq(THUMP, [(40, 4), (0, 1), (36, 6)], tail=0.1),
    "purchase": lambda: layer(seq(PING, [(86, 2), (0, 1), (91, 2), (0, 1), (98, 6)], tail=0.3), seq(GLASS, [(0, 6), (103, 6)], tail=0.3) * 0.6),
    "teleport": lambda: layer(seq(GLASS, glide(72, 108, 22), tail=0.2), seq(ORGAN, glide(48, 60, 22), tail=0.3) * 0.6),
    # The Pumpkin Cruiser.
    "car_summon": lambda: layer(seq(GLASS, glide(84, 100, 10), tail=0.1), seq(HOP, [(0, 10), (76, 3), (0, 2), (76, 3)], tail=0.15)),
    "car_on": lambda: layer(seq(HOP, [(64, 2), (71, 3)], tail=0.05), seq(ORGAN, glide(36, 50, 12), tail=0.2) * 0.7),
    "car_off": lambda: seq(ORGAN, glide(50, 32, 12), tail=0.15),
    "car_bump": lambda: seq(BOING, glide(52, 40, 4), tail=0.1),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, make in SOUNDS.items():
        y = make()
        F.write_wav(OUT / f"{name}.wav", y, gain=0.55 if name != "thunder" else 0.4)
        print(f"{name:10s} {len(y) / F.RATE:5.2f}s")


if __name__ == "__main__":
    main()
