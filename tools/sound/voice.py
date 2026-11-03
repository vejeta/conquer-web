# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""A soprano in numpy: additive source (harmonics of a vibrato'd f0) shaped by
vowel formants that move from vowel to vowel, a singer's formant near 3 kHz,
a little breath.  Soprano formants (Hz, bandwidth, gain) after the usual tables;
at high pitch F1 is tuned up to the fundamental, as real sopranos do."""
import numpy as np

SR = 48000
VOWELS = {                 # F1..F4
    "a": (850, 1220, 2810, 3900),
    "e": (600, 2350, 2900, 3900),
    "i": (330, 2600, 3200, 4000),
    "o": (560, 900, 2800, 3900),
    "u": (370, 950, 2670, 3900),
}
BW = (90, 110, 150, 200)
FG = (1.0, 0.55, 0.28, 0.12)


def note(midi, dur, vowels, vel=90, sr=SR, vib_rate=5.7, vib_cents=55, seed=0):
    rng = np.random.default_rng(seed + int(midi) * 131)
    tail = 0.5
    n = int((dur + tail) * sr)
    t = np.arange(n) / sr
    f0 = 440.0 * 2 ** ((midi - 69) / 12.0)
    # vibrato: late-onset, a little irregular, widening with the note
    onset = np.clip((t - 0.18) / 0.9, 0, 1)
    rate = vib_rate * (1 + 0.04 * np.sin(2 * np.pi * 0.31 * t + rng.uniform(0, 6)))
    cents = vib_cents * onset * (1 + 0.15 * np.sin(2 * np.pi * 0.7 * t + rng.uniform(0, 6)))
    phase_v = 2 * np.pi * np.cumsum(rate) / sr
    f = f0 * 2.0 ** (cents * np.sin(phase_v) / 1200.0)
    # a short scoop into the note
    f = f * 2.0 ** (-np.exp(-t / 0.05) * 0.4 / 12.0)
    ph = 2 * np.pi * np.cumsum(f) / sr
    # vowel path
    seq = vowels if len(vowels) > 1 else [vowels[0], vowels[0]]
    pts = np.linspace(0, dur, len(seq))
    F = np.zeros((4, n))
    for k in range(4):
        vals = [VOWELS[v][k] for v in seq]
        F[k] = np.interp(t, np.append(pts, pts[-1] + 5), vals + [vals[-1]])
    F[0] = np.maximum(F[0], f0 * 1.05)
    nh = int(min(60, 9000 / f0))
    out = np.zeros(n)
    amp_env = np.minimum(t / 0.09, 1.0) * np.clip(1 - (t - dur) / (tail * 0.9), 0, 1) ** 2
    for h in range(1, nh + 1):
        fh = f * h
        a = np.zeros(n)
        for k in range(4):
            a += FG[k] / (1 + ((fh - F[k]) / (BW[k] * 0.7)) ** 2)
        a += 0.32 / (1 + ((fh - 2900) / 380.0) ** 2)            # the singer's formant
        a *= 1.0 / h ** 0.9
        a[fh > 0.45 * sr] = 0
        out += a * np.sin(h * ph + 0.3 * h)
    # breath
    nz = rng.standard_normal(n)
    nz = np.convolve(nz, [1, -0.9], mode="same")
    out += 0.015 * nz * (1 + 0.5 * np.sin(phase_v))
    out *= amp_env
    out *= 0.9 * (vel / 127.0) ** 1.2 / (np.abs(out).max() + 1e-9) * 0.6
    return out.astype(np.float32)
