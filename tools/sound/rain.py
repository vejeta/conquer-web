# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rain and wind beds for the story, in numpy; `rain(seconds)` is a seamless loop.

Layers: a broadband wash (pink-ish noise, low-passed, slowly moving), many
individual drops (about 70 a second: short high ticks on glass, softer hits on
leaves, and low "plops" whose pitch rises, like bubbles in a puddle), a low
rumble, the lot a little muffled (it is outside) and decorrelated left/right."""
import numpy as np
from scipy import signal

SR = 48000


def _pink(n, rng):
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1]
    X /= (f / 200.0) ** 0.25          # a tilt gentler than pink: rain is hissy
    return np.fft.irfft(X, n)


def _lp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, btype="low", fs=SR, output="sos"), x)


def _hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, btype="high", fs=SR, output="sos"), x)


def _slow(n, rng, rate, depth):
    """smooth random modulation around 1"""
    k = max(4, int(SR / rate))
    pts = rng.standard_normal(n // k + 3)
    m = np.interp(np.arange(n), np.arange(len(pts)) * k, pts)
    return 1.0 + depth * m / 2.0


def _loopable(x, fade):
    """make x repeat without a click: cross-fade its tail into its head"""
    n = len(x) - fade
    y = x[:n].copy()
    w = np.linspace(0, 1, fade)
    y[:fade] = x[:fade] * w + x[n:n + fade] * (1 - w)
    return y


def rain(seconds=20.0, seed=3, density=70.0, muffle=7000.0):
    rng = np.random.default_rng(seed)
    fade = SR // 2
    n = int(seconds * SR) + fade
    chans = []
    for c in range(2):
        wash = _lp(_hp(_pink(n, rng), 450), muffle) * _slow(n, rng, 0.25, 0.25)
        wash *= 0.42
        rumble = _lp(rng.standard_normal(n), 130, 3) * _slow(n, rng, 0.12, 0.4) * 0.8
        chans.append(wash + rumble)
    L, R = chans
    drops = int(density * seconds)
    for i in range(drops):
        t0 = int(rng.random() * (n - 3000))
        kind = rng.random()
        amp = float(np.exp(rng.normal(-3.4, 0.9)))
        pan = rng.uniform(-1, 1)
        if kind < 0.45:                      # glass: a short high tick, a little ringing
            m = 900
            tt = np.arange(m) / SR
            f = rng.uniform(2500, 8500)
            x = np.sin(2 * np.pi * f * tt) * np.exp(-tt / rng.uniform(0.002, 0.007)) + 0.7 * rng.standard_normal(m) * np.exp(-tt / 0.0012)
            x = _hp(x, 1500, 1)
        elif kind < 0.8:                     # leaves and ground: soft noise bursts
            m = 1800
            tt = np.arange(m) / SR
            x = rng.standard_normal(m) * np.exp(-tt / rng.uniform(0.004, 0.012))
            x = _lp(x, rng.uniform(1800, 5000), 1)
        else:                                # a puddle plop: a bubble rising in pitch
            m = 3200
            tt = np.arange(m) / SR
            f0 = rng.uniform(500, 1300)
            ph = np.cumsum(f0 * (1 + 6 * tt)) * 2 * np.pi / SR
            x = np.sin(ph) * np.exp(-tt / rng.uniform(0.012, 0.03)) * np.minimum(tt / 0.002, 1)
            amp *= 0.5
        gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        L[t0:t0 + len(x)] += x * amp * gl * 2.8
        R[t0:t0 + len(x)] += x * amp * gr * 2.8
    L, R = _lp(L, muffle, 1), _lp(R, muffle, 1)
    out = np.stack([_loopable(L, fade), _loopable(R, fade)]).astype(np.float32)
    out /= np.sqrt((out ** 2).mean()) * 1.0 + 1e-9        # RMS 1: the mixer sets the level
    return out


def wind(seconds=20.0, seed=5):
    rng = np.random.default_rng(seed)
    fade = SR // 2
    n = int(seconds * SR) + fade
    outs = []
    for c in range(2):
        x = rng.standard_normal(n)
        fc = 380 + 160 * _slow(n, rng, 0.15, 0.8)
        # time-varying band-pass by blending two fixed band-passes
        a = signal.sosfilt(signal.butter(2, [200, 600], btype="band", fs=SR, output="sos"), x)
        b = signal.sosfilt(signal.butter(2, [500, 1500], btype="band", fs=SR, output="sos"), x)
        w = np.clip((fc - 300) / 300, 0, 1)
        y = a * (1 - w) + b * w
        y *= np.clip(_slow(n, rng, 0.2, 0.9), 0.05, 2.5)
        outs.append(_loopable(y, fade))
    out = np.stack(outs).astype(np.float32)
    out /= np.sqrt((out ** 2).mean()) + 1e-9
    return out
