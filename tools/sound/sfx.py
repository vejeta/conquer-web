# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sound effects for the story, in numpy: typewriter, power-off thunk, stone door,
quill, wax seal, anvil, cymbal crash and swell, monitor hum."""
import numpy as np
from scipy import signal

SR = 48000
rng = np.random.default_rng(7)


def _bp(x, lo, hi, order=2, sr=SR):
    sos = signal.butter(order, [lo, hi], btype="band", fs=sr, output="sos")
    return signal.sosfilt(sos, x)


def _lp(x, fc, order=2, sr=SR):
    return signal.sosfilt(signal.butter(order, fc, btype="low", fs=sr, output="sos"), x)


def _hp(x, fc, order=2, sr=SR):
    return signal.sosfilt(signal.butter(order, fc, btype="high", fs=sr, output="sos"), x)


def _t(d):
    return np.arange(int(d * SR)) / SR


def stereo(x, pan=0.0):
    a = (pan + 1) * np.pi / 4
    return np.cos(a) * x, np.sin(a) * x


def place(buf, x, t, pan=0.0):
    i = int(t * SR)
    if i >= buf[0].shape[0]:
        return
    l, r = stereo(x, pan)
    n = min(len(x), buf[0].shape[0] - i)
    buf[0][i:i + n] += l[:n]
    buf[1][i:i + n] += r[:n]


def key_clack(pan):
    t = _t(0.06)
    body = _bp(rng.standard_normal(len(t)), 1800, 5200) * np.exp(-t / 0.006) * 0.9
    thump = np.sin(2 * np.pi * (140 - 400 * t) * t) * np.exp(-t / 0.012) * 0.6
    return (body + thump).astype(np.float32)


def teletype(level):
    out = [np.zeros(int(3.0 * SR), np.float32), np.zeros(int(3.0 * SR), np.float32)]
    tt = 0.0
    for i in range(30):
        place(out, key_clack(0) * (0.6 + 0.4 * rng.random()), tt, pan=rng.uniform(-0.2, 0.2))
        tt += 0.055 + rng.random() * 0.045 + (0.12 if i % 9 == 8 else 0)
    t = _t(1.0)                                    # carriage bell
    bell = (np.sin(2 * np.pi * 2300 * t) + 0.4 * np.sin(2 * np.pi * 5650 * t)) * np.exp(-t / 0.35) * 0.18
    place(out, bell.astype(np.float32), 2.15)
    return out, level * 0.8


def off(level):
    t = _t(0.7)
    thunk = np.sin(2 * np.pi * np.cumsum(80 * np.exp(-t / 0.08) + 28) / SR) * np.exp(-t / 0.18)
    rumble = _lp(rng.standard_normal(len(t)), 300) * np.exp(-t / 0.15) * 1.5
    click = _hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.004) * 0.4
    x = (0.8 * thunk + rumble + click).astype(np.float32)
    return [x * 0.7, x * 0.7], level


def stone(level):
    d = 4.4
    t = _t(d)
    n = rng.standard_normal(len(t))
    g = _lp(n, 180, 3) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.3 * t + 1)) * 3
    scrape = _bp(n, 400, 1400) * 0.25 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * t))
    low = signal.sosfilt(signal.butter(2, 160, fs=SR, output="sos"), signal.sawtooth(2 * np.pi * 44 * t)) * 0.8
    env = np.minimum(t / 0.8, 1) * np.clip(1 - (t - 3.3) / 0.9, 0, 1)
    x = (g + scrape + low) * env
    k = _t(1.0)
    thud = np.sin(2 * np.pi * np.cumsum(62 * np.exp(-k / 0.25) + 26) / SR) * np.exp(-k / 0.3) + _lp(rng.standard_normal(len(k)), 300) * np.exp(-k / 0.08) * 0.6
    x = np.concatenate([x, np.zeros(SR)])
    x[int(3.3 * SR):int(3.3 * SR) + len(k)] += thud * 1.1
    x = x.astype(np.float32)
    return [x * 0.55, x * 0.55], level


def quill(level):
    out = [np.zeros(int(2.4 * SR), np.float32), np.zeros(int(2.4 * SR), np.float32)]
    tt = 0.0
    for i in range(18):
        d = 0.05 + rng.random() * 0.06
        t = _t(d)
        x = _bp(rng.standard_normal(len(t)), 2800 + rng.random() * 1200, 6500) * np.sin(np.pi * t / d) ** 1.5 * 0.25
        place(out, x.astype(np.float32), tt, pan=0.15)
        tt += 0.09 + rng.random() * 0.06 + (0.15 if i % 6 == 5 else 0)
    return out, level


def seal(level):
    t = _t(0.5)
    x = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t / 0.05) + 42) / SR) * np.exp(-t / 0.1)
    x += _lp(rng.standard_normal(len(t)), 700) * np.exp(-t / 0.05) * 0.5
    x += _bp(rng.standard_normal(len(t)), 2000, 4000) * np.exp(-t / 0.02) * 0.06
    return [(x * 0.6).astype(np.float32)] * 2, level


def anvil(level):
    t = _t(2.2)
    x = np.zeros(len(t))
    for f, a, dk in [(1320, 1.0, 0.5), (1790, 0.7, 0.4), (2480, 0.5, 0.3), (3650, 0.3, 0.2), (560, 0.5, 0.7)]:
        x += a * np.sin(2 * np.pi * f * t * (1 + 0.0003 * np.sin(11 * t))) * np.exp(-t / dk)
    x += _hp(rng.standard_normal(len(t)), 4500) * np.exp(-t / 0.012) * 0.6
    x += _bp(rng.standard_normal(len(t)), 800, 3000) * np.exp(-t / 0.03) * 0.5
    return [(x * 0.25).astype(np.float32)] * 2, level


def crash(level):
    t = _t(3.5)
    n = _hp(rng.standard_normal(len(t)), 2500)
    x = n * (np.exp(-t / 0.9) * 0.8 + 0.2 * np.exp(-t / 2.0))
    x += _bp(rng.standard_normal(len(t)), 5000, 9000) * np.exp(-t / 1.4) * 0.5
    y = np.convolve(x, np.ones(3) / 3, mode="same")
    return [(x * 0.22).astype(np.float32), (y * 0.22).astype(np.float32)], level


def swell(level):
    t = _t(0.7)
    n = _bp(rng.standard_normal(len(t)), 3000, 9000)
    x = n * (t / 0.7) ** 2.5 * 0.2
    return [x.astype(np.float32)] * 2, level


def hum(dur, level):
    t = _t(dur)
    x = 0.6 * np.sin(2 * np.pi * 50 * t) + 0.3 * np.sin(2 * np.pi * 100 * t + 1) + 0.12 * np.sin(2 * np.pi * 150 * t + 2) + 0.05 * np.sin(2 * np.pi * 15734 * t)
    x += 0.05 * _bp(rng.standard_normal(len(t)), 60, 400)
    x *= (1 + 0.04 * np.sin(2 * np.pi * 0.2 * t))
    return (x * 0.2 * level).astype(np.float32)


EFFECTS = {"teletype": teletype, "off": off, "stone": stone, "quill": quill, "seal": seal, "anvil": anvil, "crash": crash, "swell": swell}
