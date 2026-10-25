"""Origin: S:/Repos/trick-or-treat/art/tools/fm_synth.py (imported 2026-10-25).
Changed: none (no game paths).

Small OPL2-style two-operator FM synthesizer for the game's sound effects and music.

It models the parts of the Yamaha YM3812 that give early-90s AdLib game audio its character:
modulator -> carrier phase modulation, frequency multipliers, total level, the four waveforms,
attack/decay/sustain/release envelopes at OPL rates (percussive or sustained), tremolo and
vibrato, and "id style" sound-effect playback where one note value per 1/140 s tick sets the
frequency number (0 = key off).

Instruments use the familiar OPL register layout so they read like the classic format:
    Inst(m_char, c_char, m_scale, c_scale, m_ad, c_ad, m_sr, c_sr, m_wave, c_wave, feedback)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

RATE = 44100
OPL_CLOCK = 49716.0
TICK = 1.0 / 140.0
MULT = [0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 12, 12, 15, 15]
# Approximate OPL2 envelope timings (ms): attack 0->100%, decay/release over 96 dB.
ATTACK_MS = [math.inf, 2826.24, 1413.12, 706.56, 353.28, 176.76, 88.32, 44.16, 22.08, 11.04, 5.52, 2.76, 1.38, 0.69, 0.35, 0.0]
DECAY_MS = [math.inf] + [39280.64 / (2 ** (r - 1)) for r in range(1, 16)]


@dataclass
class Inst:
    m_char: int
    c_char: int
    m_scale: int
    c_scale: int
    m_ad: int
    c_ad: int
    m_sr: int
    c_sr: int
    m_wave: int = 0
    c_wave: int = 0
    feedback: int = 0  # 0..7


KSL_ROM = [0, 32, 40, 45, 48, 51, 53, 55, 56, 58, 59, 60, 61, 62, 63, 64]
KSL_SHIFT = [None, 1, 2, 0]  # register KSL bits 1: 3 dB/oct, 2: 1.5 dB/oct, 3: 6 dB/oct


def ksl_db(scale_reg: int, fnum10: np.ndarray, block: np.ndarray) -> np.ndarray:
    """OPL key-scale level attenuation (dB) from the top 4 bits of the 10-bit F-number."""
    ksl = (scale_reg >> 6) & 3
    if ksl == 0:
        return np.zeros_like(fnum10, dtype=np.float64)
    rom = np.array(KSL_ROM)[np.clip((fnum10.astype(int) >> 6), 0, 15)]
    val = np.maximum(rom * 4 - (8 - block.astype(int)) * 32, 0).astype(int)
    return (val >> KSL_SHIFT[ksl]) * 0.1875


def wave(kind: int, ph: np.ndarray) -> np.ndarray:
    s = np.sin(ph)
    if kind == 1:
        return np.maximum(s, 0.0)
    if kind == 2:
        return np.abs(s)
    if kind == 3:
        return np.where((np.mod(ph, math.pi) < math.pi / 2), np.abs(s), 0.0)
    return s


def envelope(gate: np.ndarray, ad: int, sr: int, sustain_mode: bool, retrigger: np.ndarray | None = None) -> np.ndarray:
    """Attenuation-domain ADSR in dB (0 = full), computed per key-on/off segment.
    gate is 1 while the key is on; retrigger marks samples where a new note restarts the attack
    without a key-off in between (music legato off)."""
    ar, dr = ad >> 4, ad & 15
    sl, rr = sr >> 4, sr & 15
    sl_db = 93.0 if sl == 15 else sl * 3.0
    a_rate = math.inf if ar == 15 else (96.0 / (ATTACK_MS[ar] * RATE / 1000.0) if ar else 0.0)
    d_rate = 96.0 / (DECAY_MS[dr] * RATE / 1000.0) if dr else 0.0
    r_rate = 96.0 / (DECAY_MS[rr] * RATE / 1000.0) if rr else 0.0
    n = len(gate)
    out = np.full(n, 96.0)
    edges = np.flatnonzero(np.diff(np.concatenate(([0], gate.astype(np.int8)))) != 0)
    starts = set(edges.tolist())
    if retrigger is not None:
        starts |= set(np.flatnonzero(retrigger).tolist())
    bounds = sorted(starts | {n})
    level = 96.0
    for k in range(len(bounds) - 1):
        a, b = bounds[k], bounds[k + 1]
        if a >= n:
            break
        idx = np.arange(b - a, dtype=np.float64)
        if gate[a]:
            # Attack from the current level, then decay toward the sustain level.
            t_att = 0.0 if a_rate == math.inf else (level / a_rate if a_rate > 0 else math.inf)
            att = np.maximum(level - idx * (a_rate if a_rate != math.inf else 1e9), 0.0)
            dec_t = np.maximum(idx - t_att, 0.0)
            dec = np.minimum(dec_t * d_rate, sl_db)
            seg = np.where(idx < t_att, att, dec)
            if not sustain_mode:
                # Percussive: after reaching the sustain level keep falling at the release rate.
                t_sl = t_att + (sl_db / d_rate if d_rate > 0 else math.inf)
                seg = np.where(idx > t_sl, np.minimum(sl_db + (idx - t_sl) * r_rate, 96.0), seg)
        else:
            seg = np.minimum(level + idx * r_rate, 96.0)
        out[a:b] = seg
        level = float(seg[-1])
    return out


def render_notes(inst: Inst, block: int, notes: list[int], tail: float = 0.4, fnum_high: int = 0) -> np.ndarray:
    """id-style sound effect: one OPL frequency-number low byte per 140 Hz tick, 0 = key off."""
    per = int(round(RATE * TICK))
    n = per * len(notes) + int(tail * RATE)
    fnum = np.zeros(n)
    gate = np.zeros(n, dtype=np.int8)
    for i, v in enumerate(notes):
        if v:
            fnum[i * per:(i + 1) * per] = v + (fnum_high << 8)
            gate[i * per:(i + 1) * per] = 1
    # Hold the last pitch through the release tail.
    last = next((v for v in reversed(notes) if v), 0)
    fnum[per * len(notes):] = last + (fnum_high << 8)
    freq = fnum * OPL_CLOCK / (2 ** (20 - block))
    return render_voice(inst, freq, gate)


def opl_split(freq: np.ndarray):
    """Best OPL (fnum10, block) for each frequency (used for key scaling)."""
    block = np.clip(np.ceil(np.log2(np.maximum(freq, 1.0) * (2 ** 20) / OPL_CLOCK / 1023.0)), 0, 7)
    fnum = freq * (2 ** (20 - block)) / OPL_CLOCK
    return fnum, block


def render_voice(inst: Inst, freq: np.ndarray, gate: np.ndarray, retrigger: np.ndarray | None = None) -> np.ndarray:
    n = len(freq)
    fnum10, blk = opl_split(freq)
    t = np.arange(n) / RATE
    vib_m = 1.0 + (0.004 * np.sin(2 * math.pi * 6.1 * t) if inst.m_char & 0x40 else 0.0)
    vib_c = 1.0 + (0.004 * np.sin(2 * math.pi * 6.1 * t) if inst.c_char & 0x40 else 0.0)
    m_freq = freq * MULT[inst.m_char & 15] * vib_m
    c_freq = freq * MULT[inst.c_char & 15] * vib_c
    m_ph = 2 * math.pi * np.cumsum(m_freq) / RATE
    c_ph = 2 * math.pi * np.cumsum(c_freq) / RATE
    m_env = envelope(gate, inst.m_ad, inst.m_sr, bool(inst.m_char & 0x20), retrigger)
    c_env = envelope(gate, inst.c_ad, inst.c_sr, bool(inst.c_char & 0x20), retrigger)
    trem = (1.0 - 0.5 * (1 + np.sin(2 * math.pi * 3.7 * t))) * 1.0  # dB, 0..-1
    m_db = m_env + (inst.m_scale & 63) * 0.75 + ksl_db(inst.m_scale, fnum10, blk) + (-trem if inst.m_char & 0x80 else 0.0)
    c_db = c_env + (inst.c_scale & 63) * 0.75 + ksl_db(inst.c_scale, fnum10, blk) + (-trem if inst.c_char & 0x80 else 0.0)
    m_amp = 10 ** (-m_db / 20.0)
    c_amp = 10 ** (-c_db / 20.0)
    if inst.feedback:
        # Modulator self-feedback, approximated with two fixed-point iterations (vectorized).
        fb = (2 ** inst.feedback) / 64.0 * math.pi
        y = wave(inst.m_wave, m_ph)
        y = wave(inst.m_wave, m_ph + fb * y)
        mod = wave(inst.m_wave, m_ph + fb * y) * m_amp
    else:
        mod = wave(inst.m_wave, m_ph) * m_amp
    return wave(inst.c_wave, c_ph + mod * 4.0 * math.pi) * c_amp


def note_freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def fnum_for(midi: float, block: int) -> int:
    return int(round(note_freq(midi) * (2 ** (20 - block)) / OPL_CLOCK))


def write_wav(path, samples: np.ndarray, rate: int = RATE, gain: float = 0.6) -> None:
    import wave as wv

    s = np.asarray(samples, dtype=np.float64)
    peak = max(np.max(np.abs(s)), 1e-6)
    s = s / peak * gain
    # A touch of the AdLib card's analogue warmth: gentle low-pass (3-tap smoothing).
    out = np.convolve(s, [0.25, 0.5, 0.25], mode="same")
    pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
    with wv.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm.tobytes())
