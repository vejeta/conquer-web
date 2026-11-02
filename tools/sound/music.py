#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the story's music: tools/story/score.py played by a SoundFont sampler
(sf2.py, FluidR3_GM), the soprano (voice.py), effects (sfx.py), rain and wind
(rain.py) and a convolution reverb, mixed to a 48 kHz stereo WAV.

  music.py video DURATIONS_JSON OUT.wav     the whole video (render.py calls render_video)
  music.py scenes DURATIONS_JSON OUTDIR     web/story/music/<n>.ogg, one per scene (the page plays them)
  music.py test OUT.wav                     with the narration lengths of the Spanish version

The SoundFont is looked up in $CONQUER_SF2, then ~/.cache/conquer-sf2/FluidR3_GM.sf2
(see tools/story/README.md: it is not in the repository).
Needs numpy and scipy."""
import json
import os
import subprocess
import sys
import wave

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rain as rainmod   # noqa: E402
import score as scoremod  # noqa: E402
import sf2 as sf2mod      # noqa: E402
import sfx as sfxmod      # noqa: E402
import voice as voicemod  # noqa: E402

SR = 48000
STEM_DB = {"strings": 0.0, "brass": -2.0, "perc": -1.0, "choir": -2.5, "solo": 0.0, "keys": -2.0, "voice": -1.0}
HALL_RT, BIG_RT = 2.4, 3.9
HALL_SEND, BIG_SEND = 0.55, 0.65
RAIN_LEVEL, WIND_LEVEL = 0.040, 0.030
# the page plays the scenes under a narration that is not ducked: the quiet scenes are lifted (dB)
PAGE_TRIM_DB = [9, 5, 4, 3, 7, 0, 4, 0]
HERE = os.path.dirname(os.path.abspath(__file__))
SF2_PATH = os.environ.get("CONQUER_SF2") or os.path.expanduser("~/.cache/conquer-sf2/FluidR3_GM.sf2")


def impulse(rt60, seed, sr=SR):
    """a hall: pre-delay, early reflections, then noise decaying faster in the highs than in the lows"""
    rng = np.random.default_rng(seed)
    n = int(rt60 * 1.15 * sr)
    t = np.arange(n) / sr
    out = []
    for c in range(2):
        x = rng.standard_normal(n)
        bands = []
        for (lo, hi, k) in [(30, 500, 1.2), (500, 3000, 1.0), (3000, 9000, 0.5), (9000, 16000, 0.25)]:
            sos = signal.butter(2, [lo, hi], btype="band", fs=sr, output="sos")
            bands.append(signal.sosfilt(sos, x) * np.exp(-t * 6.9 / (rt60 * k)))
        ir = sum(bands)
        ir *= np.minimum(t / 0.012, 1.0)
        pre = int(0.022 * sr)
        ir = np.concatenate([np.zeros(pre), ir])
        for d, a in [(0.031, 0.5), (0.047, 0.4), (0.067, 0.33), (0.089, 0.28)]:      # early reflections
            ir[int((d + 0.004 * c) * sr)] += a * 3
        out.append(ir)
    m = max(len(o) for o in out)
    ir = np.stack([np.pad(o, (0, m - len(o))) for o in out])
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    return ir.astype(np.float32)


def onepole_lp(x, fc, sr=SR):
    a = 1 - np.exp(-2 * np.pi * fc / sr)
    return signal.lfilter([a], [1, -(1 - a)], x).astype(np.float32)


class Bus:
    def __init__(self, n):
        self.dry = np.zeros((2, n), np.float32)
        self.hall = np.zeros((2, n), np.float32)
        self.big = np.zeros((2, n), np.float32)


def add(buf, l, r, i, gain, pan=0.0):
    a = (pan + 1) * np.pi / 4
    gl, gr = np.cos(a) * 1.414 * gain, np.sin(a) * 1.414 * gain
    n = min(len(l), buf.shape[1] - i)
    if n <= 0:
        return
    buf[0, i:i + n] += l[:n] * gl
    buf[1, i:i + n] += r[:n] * gr


def span_env(spans, n, fin=0.6, fout=1.5):
    env = np.zeros(n, np.float32)
    for t0, t1, lv in spans:
        i0, i1 = int(max(t0, 0) * SR), min(int(t1 * SR), n)
        if i1 <= i0:
            continue
        e = np.full(i1 - i0, lv, np.float32)
        a, b = min(int(fin * SR), len(e) // 2), min(int(fout * SR), len(e) // 2)
        if a:
            e[:a] *= np.linspace(0, 1, a)
        if b:
            e[-b:] *= np.linspace(1, 0, b)
        env[i0:i1] = np.maximum(env[i0:i1], e)
    return env


def tile(bed, n):
    reps = -(-n // bed.shape[1])
    return np.tile(bed, (1, reps))[:, :n]


def render(S, total, sf, sr=SR, tail=4.0, quiet=False):
    """the stereo mix of score S, `total` seconds long (the reverb tail past it is cut with a fade)"""
    end = total
    for nt in S.notes:
        end = max(end, nt["t"] + nt["dur"] + 0.5)
    n = int((max(end, total) + tail) * sr)
    buses = {}
    rng = np.random.default_rng(11)
    bus = lambda stem: buses.setdefault(stem, Bus(n))
    count = 0
    for nt in S.notes:
        stem = nt["stem"]
        kw = nt
        copies = [(0.0, 0.0, 0.0, 1.0)]
        if nt.get("ens"):
            copies = [(-7.0, -0.35, 0.0, 0.62), (7.0, 0.35, 0.011, 0.62)]
        for k, (det, pan_off, dly, g) in enumerate(copies):
            vib = nt.get("vib")
            if vib:
                vib = (vib[0] * (1 + 0.03 * k), vib[1], vib[2], vib[3] + 1.7 * k + rng.uniform(0, 3))
            out = sf2mod.render_note(sf, nt["inst"][0], nt["inst"][1], nt["key"], int(np.clip(nt["vel"], 1, 127)), nt["dur"],
                                     att=nt.get("att"), rel=nt.get("rel"), vib=vib, tune=det + rng.uniform(-3, 3), gain=g)
            if out is None:
                continue
            l, r = out
            if nt.get("lp"):
                l, r = onepole_lp(l, nt["lp"]), onepole_lp(r, nt["lp"])
            i = int((nt["t"] + dly + (rng.uniform(-0.008, 0.008) if nt["stem"] in ("strings", "choir", "brass", "solo") else 0)) * sr)
            i = max(i, 0)
            pan = float(np.clip(nt.get("pan", 0.0) + pan_off, -1, 1))
            b = bus(stem)
            add(b.dry, l, r, i, 1.0, pan)
            w = nt.get("wet", 0.4)
            add(b.big if nt.get("big") else b.hall, l, r, i, w, pan)
            count += 1
    for v in S.voices:
        x = voicemod.note(v["midi"], v["dur"], v["vowels"], v["vel"], sr=sr, seed=int(v["t"] * 10))
        b = bus("voice")
        add(b.dry, x, x, max(int(v["t"] * sr), 0), 0.9, 0.0)
        add(b.big if v.get("big") else b.hall, x, x, max(int(v["t"] * sr), 0), v.get("wet", 0.7), 0.0)
        count += 1
    for f in S.sfx:
        l, r = sfxmod.EFFECTS[f["name"]](f["level"])[0]
        b = bus("sfx")
        i = max(int(f["t"] * sr), 0)
        add(b.dry, l, r, i, f["level"], 0.0)
        add(b.hall, l, r, i, 0.25 * f["level"], 0.0)
    if not quiet:
        print("rendered %d notes/voices, %d effects" % (count, len(S.sfx)))

    def stem_gain(stem):
        pts = sorted(S.auto.get(stem, []))
        g = 10 ** (STEM_DB.get(stem, 0.0) / 20.0)
        if not pts:
            return np.full(n, g, np.float32)
        ts = np.array([p[0] for p in pts])
        db = np.array([p[1] for p in pts])
        # points of scenes that follow each other are joined; the curve is held at both ends
        return (g * 10 ** (np.interp(np.arange(n) / sr, ts, db) / 20.0)).astype(np.float32)

    dry = np.zeros((2, n), np.float32)
    hall = np.zeros((2, n), np.float32)
    big = np.zeros((2, n), np.float32)
    for stem, b in buses.items():
        g = stem_gain(stem)
        dry += b.dry * g
        hall += b.hall * g
        big += b.big * g
    ir_h, ir_b = impulse(HALL_RT, 1), impulse(BIG_RT, 2)
    wet = np.zeros((2, n), np.float32)
    for src, ir, send in ((hall, ir_h, HALL_SEND), (big, ir_b, BIG_SEND)):
        if np.abs(src).max() > 0:
            for c in range(2):
                wet[c] += signal.oaconvolve(src[c], ir[c], mode="full")[:n].astype(np.float32) * send
    mix = dry + wet
    # beds: rain, wind, monitor hum
    if S.rain:
        mix += tile(rainmod.rain(20.0), n) * span_env(S.rain, n) * RAIN_LEVEL
    if S.wind:
        mix += tile(rainmod.wind(20.0), n) * span_env(S.wind, n) * WIND_LEVEL
    for t0, t1, lv in S.hum:
        d = min(t1, end + tail) - t0
        if d > 0:
            h = sfxmod.hum(d, lv)
            e = span_env([(0, d, 1.0)], len(h), 1.0, 1.5)
            add(mix, h * e, h * e, int(t0 * sr), 1.0)
    return mix, n


def finish(mix, total, sr=SR, tail_fade=2.0, ref_peak=None):
    """DC/rumble filter, a soft limiter, the fade at `total`, peak at -3 dBFS
    (ref_peak: the peak to normalise by, to keep the levels of several files in proportion)"""
    sos = signal.butter(2, 28, btype="high", fs=sr, output="sos")
    x = signal.sosfilt(sos, mix, axis=1).astype(np.float32)
    air = signal.sosfilt(signal.butter(2, 3500, btype='high', fs=sr, output='sos'), x, axis=1)
    x = (x + 0.55 * air).astype(np.float32)           # a little air: the sampled strings are dull
    n = int(total * sr)
    x = x[:, :n].copy()
    f = int(tail_fade * sr)
    x[:, -f:] *= np.linspace(1, 0, f) ** 1.5
    peak = ref_peak or np.abs(x).max()
    x /= peak                                      # 1.0
    knee = 0.45                                    # soft limiter: above the knee, tanh towards 1
    ax = np.abs(x)
    over = ax > knee
    x = np.where(over, np.sign(x) * (knee + (1 - knee) * np.tanh((ax - knee) / (1 - knee))), x)
    x *= 10 ** (-3.0 / 20) / (min(np.abs(x).max(), 1.0) if ref_peak is None else 1.0)
    return x


def write_wav(path, x, sr=SR):
    pcm = (np.clip(x, -1, 1).T * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def load_sf():
    if not os.path.exists(SF2_PATH):
        sys.exit("SoundFont not found: %s (see tools/story/README.md)" % SF2_PATH)
    return sf2mod.SF2(SF2_PATH)


def render_video(durations, starts, total, out):
    """whole-video music: scene starts and total length as recorded by render.py"""
    sf = load_sf()
    S = scoremod.build(durations, starts)
    mix, n = render(S, total, sf)
    x = finish(mix, total)
    write_wav(out, x)
    return x


def render_scenes(durations, outdir):
    sf = load_sf()
    os.makedirs(outdir, exist_ok=True)
    mixes = []
    for k in range(1, 9):
        S = scoremod.build(durations, only=k)
        total = durations[k - 1] + scoremod.GAP + 3.0
        mix, n = render(S, total, sf, quiet=True)
        mixes.append((total, mix))
    ref = max(np.abs(m[:, :int(t * SR)]).max() for t, m in mixes)     # one gain for all, the scenes keep their proportions
    for k, (total, mix) in enumerate(mixes, 1):
        x = finish(mix, total, tail_fade=1.8, ref_peak=ref) * 10 ** (PAGE_TRIM_DB[k - 1] / 20.0)
        wav = os.path.join(outdir, "%d.wav" % k)
        write_wav(wav, x)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "4", os.path.join(outdir, "%d.ogg" % k)], check=True)
        os.remove(wav)
        print("scene %d: %.1f s" % (k, total))


def narration(path=None):
    path = path or os.path.join(HERE, "..", "..", "web", "story", "es", "durations.json")
    s = json.load(open(path))["seconds"]
    d = [s[str(i)] for i in range(1, 9)]
    d[7] = max(d[7], 7.0)
    return d


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["test"]:
        d = narration()
        starts, t = [], 0.0
        for x in d:
            starts.append(t)
            t += x + scoremod.GAP
        render_video(d, starts, starts[-1] + d[-1] + 3.0, a[1])
    elif a[:1] == ["video"]:
        render_video(narration(a[1]), None, sum(narration(a[1])) + 8 * scoremod.GAP + 3.0, a[2])
    elif a[:1] == ["scenes"]:
        render_scenes(narration(a[1]), a[2])
    else:
        sys.exit(__doc__)
