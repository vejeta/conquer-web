#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the game's sound set to web/sound/*.ogg (Vorbis, 44.1 kHz, ~96 kbps).

Everything is played by a SoundFont (sf2.py, FluidR3_GM: see tools/sound/README.md)
through a long cathedral-like convolution reverb (music.py); there are no
oscillators or synthesised noise in the shipped files.

  build.py                  all files
  build.py map-human ui-tap only those (names without .ogg)
  build.py --keep DIR ...   also keep the 48 kHz WAVs in DIR (to inspect them)
  build.py --report         print level / spectrum / loop-seam figures of what it renders

The music is original: one modal theme of two eight-bar phrases in A aeolian,
6/8, slow (54 to 66 bpm), carried by a soprano "ah" (the SoundFont's choir),
with Celtic-harp arpeggios, a low strings drone and high strings. Each race
colours it: humans a low horn and a far brush snare, elves a flute, glockenspiel
and more strings, dwarves low brass, timpani and bell "anvil" strokes, orcs low
voices, taiko and heavy brass. The loops are seamless: the reverb and the notes
that ring past the end are folded onto the start (see fold()).
"""
import os
import subprocess
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import music as M        # noqa: E402
import score as SC       # noqa: E402
import sf2 as sf2mod     # noqa: E402

SR = M.SR
OUT = os.path.join(HERE, "..", "..", "web", "sound")

# (bank, program)
HARP, CEL, GLOCK, TUBE, MBOX = (0, 46), (0, 8), (0, 9), (0, 14), (0, 10)
VLN, VLA, VC, CB, SLOW, STR = (0, 40), (0, 41), (0, 42), (0, 43), (0, 49), (0, 48)
AH, OH = (0, 52), (0, 53)
HORN, TRPT, TBN, TUBA, BRASS = (0, 60), (0, 56), (0, 57), (0, 58), (0, 61)
FLUTE = (0, 73)
TIMP, TAIKO, WOOD = (0, 47), (0, 116), (0, 115)
KIT = (128, 48)

# ---- the theme: A aeolian, 6/8; (midi, eighths); a bar is 6 eighths -----------------
MEL_A = [[(69, 6)], [(72, 4), (74, 2)], [(76, 6)], [(74, 3), (72, 3)],
         [(69, 4), (72, 2)], [(71, 3), (67, 3)], [(69, 4), (71, 2)], [(69, 6)]]
MEL_B = [[(76, 4), (74, 2)], [(72, 6)], [(76, 3), (79, 3)], [(74, 6)],
         [(72, 4), (69, 2)], [(71, 4), (74, 2)], [(72, 3), (71, 3)], [(69, 6)]]
CH = {"Am": (57, 60, 64), "C": (60, 64, 67), "G": (55, 59, 62), "F": (53, 57, 60), "Em": (52, 55, 59)}
ROOT = {"Am": 45, "C": 48, "G": 43, "F": 41, "Em": 40}
PROG_A = ["Am", "Am", "C", "G", "F", "G", "Am", "Am"]
PROG_B = ["Am", "F", "C", "G", "Am", "G", "Am", "Am"]
ARP = [0, 1, 2, 3, 2, 1]            # chord tone indices of a harp bar (3 = the root an octave up)

# colour of each race: transposition, bpm, instrument of the melody's solo voice
RACES = {
    "human": dict(shift=0, bpm=60),
    "elf": dict(shift=2, bpm=62),
    "dwarf": dict(shift=-5, bpm=60),
    "orc": dict(shift=-4, bpm=66),
}
LEVEL = [0.62, 0.85, 1.0, 0.55]     # the loop breathes: quiet, rising, full, receding


def beat(bpm):
    return 60.0 / bpm


class Rng:
    r = np.random.default_rng(5)


def jit(x=0.012):
    return float(Rng.r.uniform(-x, x))


def phrase(S, t0, bpm, which, race, p, shift, lvl):
    """one eight-bar phrase of a map bed: p = 0..3 is its place in the loop"""
    b = beat(bpm)
    e = b / 3.0
    bar = 2 * b
    mel = MEL_A if which == "A" else MEL_B
    prog = PROG_A if which == "A" else PROG_B
    v = lambda x: int(np.clip(x * lvl, 1, 120))
    P = lambda m: m + shift
    # low strings drone on the tonic, for the whole phrase
    S.n("strings", CB, t0, 8 * bar + 1.0, P(33), v(34), att=3.0, rel=3.0, wet=0.4)
    S.n("strings", VC, t0 + 0.4, 8 * bar, P(45), v(30), att=3.0, rel=3.0, wet=0.4)
    for i, name in enumerate(prog):
        tb = t0 + i * bar
        c = [P(m) for m in CH[name]]
        # slow strings pad
        if i % 2 == 0 or race == "elf":
            for m in c:
                S.n("strings", SLOW, tb, bar * 1.6, m + (12 if race == "elf" else 0), v(26), att=1.4, rel=1.8, wet=0.8, big=True, ens=True)
        # the harp: a rolling arpeggio, a bar of six eighths
        if race != "orc" or p in (1, 2):
            tones = c + [c[0] + 12]
            for k, ix in enumerate(ARP):
                S.n("keys", HARP, tb + k * e + jit(0.006), 2.6, tones[ix] + 12, v(40 + (6 if k == 0 else 0) + 3 * (k % 3)),
                    wet=0.65, pan=-0.45 + 0.18 * k)
    # the melody
    for i, bar_notes in enumerate(mel):
        tb = t0 + i * bar
        te = 0.0
        for m, ne in bar_notes:
            t, d = tb + te * e, ne * e * 1.04
            te += ne
            soprano = (p in (1, 2) or (p == 3 and race == "elf"))
            if soprano:
                S.n("choir", AH, t, d, P(m), v(58 if p == 1 else 68), att=0.4, rel=1.0, vib=(5.2, 16, 0.5, 0), wet=0.9, big=True, ens=True, pan=0.1)
            if race == "human":
                S.n("brass", HORN, t, d, P(m) - 12, v(46 if p != 3 else 38), att=0.3, rel=0.7, vib=(4.8, 10, 0.6, 0), wet=0.8, big=True, pan=-0.25)
                if p == 2:
                    S.n("strings", VLN, t, d, P(m), v(34), att=0.5, rel=0.8, vib=(5.3, 18, 0.5, 0), wet=0.8, big=True, ens=True, pan=0.25)
            elif race == "elf":
                S.n("solo", FLUTE, t, d, P(m), v(34 if p != 3 else 28), att=0.25, rel=0.7, vib=(5.0, 14, 0.5, 0), wet=0.9, big=True, pan=-0.3)
                S.n("strings", VLN, t, d, P(m) + 12, v(26 if p else 18), att=0.7, rel=1.0, vib=(5.6, 16, 0.5, 0), wet=0.9, big=True, ens=True, pan=0.3)
                if i % 2 == 0 and p in (1, 2):
                    S.n("keys", GLOCK, t, 2.0, P(m) + 12, v(34), wet=0.9, big=True, pan=0.4)
            elif race == "dwarf":
                S.n("brass", TBN, t, d, P(m) - 12, v(46 if p != 3 else 36), att=0.35, rel=0.7, wet=0.7, big=True, pan=-0.2)
                S.n("brass", TUBA, t, d, P(m) - 24, v(38), att=0.4, rel=0.7, wet=0.6, pan=0.2)
            else:
                S.n("choir", OH, t, d, P(m) - 12, v(54), att=0.45, rel=1.0, wet=0.8, big=True, ens=True, pan=-0.15)
                S.n("brass", BRASS, t, d, P(m) - 24, v(42), att=0.35, rel=0.8, wet=0.6, big=True, pan=0.2)
    # the colour of the race
    if race == "human":
        if p == 2:      # a far brush of a snare under the third phrase
            for i in range(8):
                for k, x in enumerate((0, 3)):
                    S.n("perc", KIT, t0 + i * bar + x * e, 0.2, 38, v(20 + 8 * (k == 0)), wet=0.7, big=True)
        if p in (0, 2):  # the low horn call that ends the phrase
            for k, (m, dd) in enumerate([(45, 1.6), (52, 1.6), (45, 3.0)]):
                S.n("brass", HORN, t0 + 7 * bar - 0.2 + k * 1.1, dd, P(m), v(60), att=0.35, rel=1.4, wet=0.9, big=True, pan=-0.35)
    elif race == "dwarf":
        for i in range(8):
            if p >= 1 and i % 2 == 0:
                S.n("perc", TIMP, t0 + i * bar, 1.2, P(ROOT[prog[i]] + 12) - 12 + 12, v(46 + (10 if p == 2 else 0)), wet=0.8, big=True)
            if p in (1, 2) and i in (3, 7):
                S.n("keys", TUBE, t0 + i * bar + 0.0, 2.2, P(52), v(44), wet=0.9, big=True, pan=0.3)   # the anvil stroke
                S.n("keys", TUBE, t0 + i * bar + 2 * e, 2.2, P(52) + 7, v(30), wet=0.9, big=True, pan=0.35)
    elif race == "orc":
        for i in range(8):
            if p >= 1:
                S.n("perc", TAIKO, t0 + i * bar, 1.0, P(ROOT[prog[i]] + 12) - 12, v(52 + (16 if p == 2 else 0)), wet=0.7, big=True)
            if p == 2:
                S.n("perc", TAIKO, t0 + i * bar + 3 * e, 0.8, P(ROOT[prog[i]] + 12) - 7, v(48), wet=0.7, big=True)
        for m in (45, 52):
            S.n("brass", BRASS, t0 + 3 * bar, 4 * bar, P(m) - 12, v(30 if p != 2 else 44), att=2.5, rel=2.5, wet=0.7, big=True, ens=True)


def map_bed(race):
    cfg = RACES[race]
    bpm = cfg["bpm"]
    bar = 2 * beat(bpm)
    L = 32 * bar
    S = SC.Score()
    Rng.r = np.random.default_rng(sum(map(ord, race)) + 3)
    for p, which in enumerate(["A", "B", "A", "B"]):
        phrase(S, p * 8 * bar, bpm, which, race, p, cfg["shift"], LEVEL[p])
    return S, L


def builder_bed():
    """a lullaby: the theme on a music box and celesta, a hummed choir, harp, then plainer"""
    bpm = 62
    b = beat(bpm)
    e = b / 3
    bar = 2 * b
    S = SC.Score()
    Rng.r = np.random.default_rng(41)
    S.n("strings", CB, 0, 24 * bar + 1, 33, 28, att=4.0, rel=3.0, wet=0.4)
    lv = [0.7, 0.95, 0.6]
    for p, which in enumerate(["A", "B", "A"]):
        t0 = p * 8 * bar
        mel = MEL_A if which == "A" else MEL_B
        prog = PROG_A if which == "A" else PROG_B
        v = lambda x: int(np.clip(x * lv[p], 1, 120))
        for i, name in enumerate(prog):
            tb = t0 + i * bar
            c = CH[name]
            for m in c:
                S.n("strings", SLOW, tb, bar * 1.5, m, v(24), att=1.4, rel=1.8, wet=0.9, big=True, ens=True)
            tones = list(c) + [c[0] + 12]
            for k, ix in enumerate([0, 2, 1, 3, 1, 2]):
                S.n("keys", HARP, tb + k * e + jit(0.006), 2.4, tones[ix] + 12 + (12 if p == 1 else 0), v(36 + 2 * (k % 3)), wet=0.7, pan=-0.4 + 0.16 * k)
        for i, nb in enumerate(mel):
            te = 0.0
            for m, ne in nb:
                t, d = t0 + i * bar + te * e, ne * e * 1.04
                te += ne
                S.n("keys", MBOX if p != 1 else CEL, t, 2.2, m + (12 if p == 1 else 0), v(52), wet=0.85, big=True, pan=0.15)
                if p == 1:
                    S.n("choir", OH, t, d, m, v(40), att=0.5, rel=1.0, vib=(5.0, 14, 0.6, 0), wet=0.9, big=True, ens=True)
    return S, 24 * bar


def report_bed():
    """a quiet drone of strings and the odd far harp note"""
    bpm = 60
    bar = 2 * beat(bpm)
    S = SC.Score()
    Rng.r = np.random.default_rng(17)
    L = 24 * bar
    S.n("strings", CB, 0, L + 1, 33, 38, att=4.0, rel=4.0, wet=0.4)
    S.n("strings", VC, 0.5, L, 45, 30, att=4.0, rel=4.0, wet=0.4)
    prog = ["Am", "F", "C", "G", "Am", "Em", "F", "G"] * 1
    seq = prog * 3
    for i, name in enumerate(seq):
        tb = i * bar
        for k, m in enumerate(CH[name]):
            S.n("strings", SLOW, tb - 0.4 * (k > 0), bar * 1.9, m, 26 + 3 * (i % 3 == 1), att=2.2, rel=2.4, wet=0.9, big=True, ens=True)
        if i % 3 == 1:
            S.n("keys", HARP, tb + 0.5, 3.0, CH[name][2] + 12, 34, wet=0.9, big=True, pan=Rng.r.uniform(-0.5, 0.5))
        if i % 6 == 4:
            S.n("strings", VLN, tb, 2 * bar, CH[name][0] + 24, 22, att=2.0, rel=2.5, vib=(5.2, 14, 0.8, 0), wet=0.95, big=True, ens=True)
    return S, L


def combat_bed():
    """percussive: taiko and timpani in 6/8, low brass and voices, a bell struck like an anvil"""
    bpm = 84
    b = beat(bpm)
    e = b / 3
    bar = 2 * b
    S = SC.Score()
    Rng.r = np.random.default_rng(23)
    n = 28
    L = n * bar
    prog = (["Am", "Am", "F", "G"] * 7)
    S.n("strings", CB, 0, L + 1, 33, 56, att=2.0, rel=3.0, wet=0.3)
    swell = lambda i: 0.7 + 0.3 * np.sin(np.pi * i / n) ** 2
    for i in range(n):
        tb = i * bar
        k = swell(i)
        r = ROOT[prog[i]]
        S.n("perc", TAIKO, tb, 1.2, r - 12 + 12, int(100 * k), wet=0.5, big=True)
        S.n("perc", TIMP, tb, 1.4, r + 12 - 12, int(76 * k), wet=0.5, big=True)
        S.n("perc", TAIKO, tb + 3 * e, 0.8, r - 7 + 12 - 12, int(70 * k), wet=0.5, big=True)
        for q in (2, 5):
            S.n("perc", TIMP, tb + q * e, 0.6, r + 12 - 12 + 7, int(48 * k), wet=0.5, big=True)
        if i % 2 == 0:
            for m in CH[prog[i]]:
                S.n("brass", TBN, tb, bar * 1.2, m - 12, int(64 * k), att=0.15, rel=0.6, wet=0.6, big=True)
            S.n("brass", TUBA, tb, bar * 1.2, r - 12, int(70 * k), att=0.15, rel=0.6, wet=0.5)
        if i % 4 == 3:
            S.n("brass", HORN, tb + 3 * e, 3 * e, CH[prog[i]][2] + 12, int(80 * k), att=0.05, rel=0.6, wet=0.7, big=True)
            S.n("keys", TUBE, tb + 3 * e, 2.4, 55, int(60 * k), wet=0.9, big=True)   # the anvil stroke
        if i % 8 in (4, 5, 6, 7):
            for m in (45, 52, 57):
                S.n("choir", OH, tb, bar * 1.1, m, int(60 * k), att=0.3, rel=0.8, wet=0.7, big=True, ens=True)
    return S, L


def home_bed():
    """the app's home screen: the theme in strings and harp, 30 s exactly (16 bars at 64 bpm)"""
    bpm = 64
    b = beat(bpm)
    e = b / 3
    bar = 2 * b
    S = SC.Score()
    Rng.r = np.random.default_rng(29)
    S.n("strings", CB, 0, 16 * bar + 1, 33, 34, att=3.0, rel=3.0, wet=0.4)
    for p, which in enumerate(["A", "B"]):
        t0 = p * 8 * bar
        mel = MEL_A if which == "A" else MEL_B
        prog = PROG_A if which == "A" else PROG_B
        lv = [0.8, 1.0][p]
        for i, name in enumerate(prog):
            tb = t0 + i * bar
            c = CH[name]
            for m in c:
                S.n("strings", SLOW, tb, bar * 1.6, m, int(28 * lv), att=1.2, rel=1.8, wet=0.8, big=True, ens=True)
            tones = list(c) + [c[0] + 12]
            for k, ix in enumerate(ARP):
                S.n("keys", HARP, tb + k * e + jit(0.006), 2.6, tones[ix] + 12, int((42 + 3 * (k % 3)) * lv), wet=0.65, pan=-0.45 + 0.18 * k)
        for i, nb in enumerate(mel):
            te = 0.0
            for m, ne in nb:
                t, d = t0 + i * bar + te * e, ne * e * 1.04
                te += ne
                S.n("strings", VLN if p else VLA, t, d, m + (0 if p else 0), int(56 * lv), att=0.45, rel=0.9, vib=(5.3, 18, 0.5, 0), wet=0.9, big=True, ens=True, pan=0.15)
                S.n("strings", VC, t, d, m - 12, int(40 * lv), att=0.45, rel=0.9, vib=(4.9, 12, 0.5, 0), wet=0.8, big=True, pan=-0.2)
    return S, 16 * bar


BEDS = {
    "map-human": lambda: map_bed("human"), "map-elf": lambda: map_bed("elf"),
    "map-dwarf": lambda: map_bed("dwarf"), "map-orc": lambda: map_bed("orc"),
    "builder": builder_bed, "report": report_bed, "combat": combat_bed, "app-home": home_bed,
}
# integrated loudness offset of each bed (dB) from the common RMS of -24 dBFS
BED_DB = {"map-human": 0, "map-elf": 0, "map-dwarf": 0, "map-orc": 0, "builder": -1, "report": -4, "combat": 2, "app-home": 1}


# ---- the effects: (name, builder, length s, peak dBFS, channels) -----------------------
def fx(name):
    S = SC.Score()
    rt = (1.2, 2.4)
    Rng.r = np.random.default_rng(len(name))
    if name == "ui-tap":
        S.n("perc", WOOD, 0, 0.12, 79, 54, wet=0.12, rel=0.1)
        total, peak, ch = 0.35, -9, 1
    elif name == "move":
        S.n("perc", WOOD, 0, 0.1, 86, 34, wet=0.08, rel=0.08)
        total, peak, ch = 0.25, -15, 1
    elif name == "bump":
        S.n("perc", WOOD, 0, 0.2, 47, 100, wet=0.12, rel=0.25)
        S.n("perc", TAIKO, 0, 0.3, 43, 38, wet=0.1, rel=0.3)
        total, peak, ch = 0.7, -7, 1
    elif name == "open":                          # the scroll unrolls: a soft harp run up
        for k, m in enumerate((69, 72, 76, 79, 84)):
            S.n("keys", HARP, 0.07 * k, 1.5, m, 40 + 3 * k, wet=0.5, pan=-0.4 + 0.2 * k)
        S.n("keys", WOOD, 0, 0.1, 74, 30, wet=0.2)
        total, peak, ch = 1.6, -9, 2
    elif name == "close":
        for k, m in enumerate((84, 79, 76, 72, 69)):
            S.n("keys", HARP, 0.07 * k, 1.5, m, 46 - 3 * k, wet=0.5, pan=0.4 - 0.2 * k)
        S.n("perc", WOOD, 0.36, 0.1, 55, 40, wet=0.2)
        total, peak, ch = 1.6, -10, 2
    elif name == "news":                          # a teletype from woodblock ticks, a bell at the line's end
        t = 0.0
        for i in range(22):
            S.n("perc", WOOD, t, 0.06, 84 + (i % 3) * 2, 26 + int(Rng.r.integers(0, 14)), wet=0.05, rel=0.05, pan=float(Rng.r.uniform(-0.2, 0.2)))
            t += 0.055 + float(Rng.r.random()) * 0.04 + (0.12 if i % 8 == 7 else 0)
        S.n("keys", GLOCK, t + 0.1, 1.2, 96, 56, wet=0.4)
        total, peak, ch = t + 1.8, -9, 2
    elif name == "message":                       # a horn call
        S.n("brass", HORN, 0, 0.5, 57, 84, att=0.12, rel=0.5, wet=0.8, big=True)
        S.n("brass", HORN, 0.55, 1.0, 64, 92, att=0.12, rel=1.0, vib=(5.0, 10, 0.3, 0), wet=0.8, big=True)
        total, peak, ch, rt = 2.8, -6, 2, (2.0, 3.0)
    elif name == "turn":                          # a short fanfare
        for k, (m, d) in enumerate([(57, 0.35), (64, 0.35), (69, 0.35), (72, 0.3), (76, 1.2)]):
            t = 0.38 * k
            S.n("brass", TRPT, t, d, m, 84, att=0.04, rel=0.5, wet=0.6, big=True, pan=-0.1)
            S.n("brass", HORN, t, d, m - 12, 80, att=0.05, rel=0.5, wet=0.6, big=True, pan=0.1)
        S.n("perc", TIMP, 1.9, 1.0, 45, 80, wet=0.5, big=True)
        total, peak, ch, rt = 3.6, -6, 2, (2.0, 3.0)
    elif name == "combat-hit":                    # drums and an anvil stroke
        S.n("perc", TAIKO, 0, 0.8, 38, 120, wet=0.3, rel=0.8)
        S.n("perc", TIMP, 0.0, 1.0, 38, 110, wet=0.4, rel=1.0)
        S.n("perc", TAIKO, 0.22, 0.6, 45, 100, wet=0.3, rel=0.6)
        S.n("keys", TUBE, 0.05, 1.6, 55, 100, wet=0.5, rel=1.2)
        S.n("keys", TUBE, 0.3, 1.4, 62, 70, wet=0.5, rel=1.0)
        total, peak, ch, rt = 2.2, -5, 2, (1.6, 2.6)
    elif name == "found":                         # bells and brass: a nation is born
        for k, m in enumerate((57, 64, 69, 73, 76)):
            S.n("keys", TUBE, 0.2 * k, 3.0, m, 80, wet=0.6, big=True, pan=-0.3 + 0.15 * k)
            S.n("keys", GLOCK, 0.2 * k, 2.5, m + 12, 56, wet=0.6, big=True)
        for m in (45, 52, 57, 61, 64):
            S.n("brass", HORN, 1.0, 2.4, m, 88, att=0.5, rel=1.6, wet=0.8, big=True, ens=True)
        for m in (69, 73, 76):
            S.n("brass", TRPT, 1.2, 2.0, m, 72, att=0.4, rel=1.5, wet=0.8, big=True)
        total, peak, ch, rt = 5.0, -6, 2, (2.2, 3.4)
    elif name == "approved":
        for k, m in enumerate((69, 72, 76, 81)):
            S.n("keys", CEL, 0.16 * k, 2.4, m, 78, wet=0.7, big=True, pan=-0.3 + 0.2 * k)
            S.n("keys", TUBE, 0.16 * k, 2.4, m - 12, 52, wet=0.7, big=True)
        total, peak, ch, rt = 3.4, -7, 2, (2.0, 3.0)
    elif name == "app-doors-open":                # rune bells, the stone, a short brass swell: 3 s
        for k, m in enumerate((74, 77, 81, 86)):
            S.n("keys", CEL, 0.17 * k, 1.6, m, 84, wet=0.8, big=True, pan=-0.4 + 0.27 * k)
            S.n("keys", GLOCK, 0.17 * k, 1.6, m + 12, 50, wet=0.8, big=True, pan=-0.4 + 0.27 * k)
        for k in range(14):                       # the stone: a low roll that grows
            S.n("perc", TAIKO, 0.9 + 0.09 * k, 0.4, 33, 26 + 3 * k, wet=0.6, big=True, rel=0.4)
        S.n("strings", CB, 0.8, 1.9, 28, 72, att=0.5, rel=0.6, wet=0.5)
        S.n("strings", CB, 0.8, 1.9, 33, 60, att=0.5, rel=0.6, wet=0.5)
        S.n("perc", TIMP, 2.25, 0.8, 33, 96, wet=0.5, big=True)
        for m in (50, 57, 62, 66):
            S.n("brass", HORN, 1.7, 1.2, m, 88, att=0.7, rel=0.7, wet=0.8, big=True, ens=True)
        total, peak, ch, rt = 3.0, -6, 2, (2.0, 3.0)
    elif name == "app-doors-fail":                # the runes flicker out
        for k, m in enumerate((86, 81, 77, 74, 69)):
            S.n("keys", CEL, 0.13 * k, 0.5, m, 80 - 8 * k, wet=0.7, rel=0.4, pan=0.3 - 0.15 * k)
        S.n("perc", TAIKO, 0.7, 0.8, 31, 100, wet=0.4, rel=0.7)
        S.n("strings", CB, 0.7, 0.7, 28, 70, att=0.1, rel=0.5, wet=0.4)
        total, peak, ch, rt = 1.5, -7, 2, (1.4, 2.4)
    else:
        raise KeyError(name)
    return S, total, peak, ch, rt


EFFECTS = ["ui-tap", "move", "bump", "open", "close", "news", "message", "turn", "combat-hit", "found", "approved",
           "app-doors-open", "app-doors-fail"]


# ---- mixing ------------------------------------------------------------------------------
def fold(x, L):
    """the loop: the first L samples with everything past them (the ringing notes, the reverb) added
    back at the start, as if the music had been going round for ever"""
    out = x[:, :L].copy()
    rest = x[:, L:]
    while rest.shape[1]:
        seg = rest[:, :L]
        out[:, :seg.shape[1]] += seg
        rest = rest[:, L:]
    return out


def tone_filter(x, hi=6000, order=4):
    sos = signal.butter(2, 28, btype="high", fs=SR, output="sos")
    x = signal.sosfilt(sos, x, axis=1)
    sos = signal.butter(order, hi, btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=1).astype(np.float32)


def level(x, rms_db, peak_db=-3.0):
    r = float(np.sqrt((x ** 2).mean()))
    x = x * (10 ** (rms_db / 20.0) / max(r, 1e-9))
    pk = 10 ** (peak_db / 20.0)
    knee = pk * 0.7                                   # soft limiter above the knee
    ax = np.abs(x)
    x = np.where(ax > knee, np.sign(x) * (knee + (pk - knee) * np.tanh((ax - knee) / (pk - knee))), x)
    return x.astype(np.float32)


def render_score(S, total, sf, hall, big, tail):
    M.HALL_RT, M.BIG_RT = hall, big
    mix, n = M.render(S, total, sf, tail=tail, quiet=True)
    return mix


def bed(name, sf):
    S, L = BEDS[name]()
    M.HALL_SEND, M.BIG_SEND = 0.75, 0.9
    n_tail = 8.0
    mix = render_score(S, L / 1.0, sf, 3.6, 5.8, n_tail)
    x = tone_filter(mix)
    Ls = int(round(L * SR))
    y = fold(x, Ls)
    y = level(y, -24.0 + BED_DB[name])
    return y


def effect(name, sf):
    S, total, peak, ch, rt = fx(name)
    M.HALL_SEND, M.BIG_SEND = 0.5, 0.6
    mix = render_score(S, total, sf, rt[0], rt[1], 1.0)
    x = tone_filter(mix, hi=9000, order=2)
    n = int(total * SR)
    x = x[:, :n].copy()
    f = min(int(0.25 * SR), n // 3)
    x[:, -f:] *= np.linspace(1, 0, f) ** 1.5
    pk = float(np.abs(x).max())
    x *= 10 ** (peak / 20.0) / max(pk, 1e-9)
    if ch == 1:
        x = np.repeat(x.mean(axis=0, keepdims=True), 2, axis=0)
    return x, ch


def encode(wav, ogg, ch, kbps):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ar", "44100", "-ac", str(ch), "-c:a", "libvorbis", "-b:a", "%dk" % kbps, ogg], check=True)


def seam(y):
    """loop-seam figures: the jump between the last and the first sample against the typical step"""
    jump = float(np.abs(y[:, 0] - y[:, -1]).max())
    step = float(np.abs(np.diff(y, axis=1)).mean())
    return jump, step


def figures(name, y):
    sr = SR
    win = int(2 * sr)
    rms = [20 * np.log10(max(np.sqrt((y[:, i:i + win] ** 2).mean()), 1e-9)) for i in range(0, y.shape[1] - win + 1, win)]
    mono = y.mean(axis=0)
    sp = np.abs(np.fft.rfft(mono)) ** 2
    fr = np.fft.rfftfreq(len(mono), 1 / sr)
    hi = sp[fr > 6000].sum() / sp.sum()
    j, s = seam(y)
    print("%-16s %5.1fs  rms(2s) %s dB  >6k %.2e of energy  seam jump %.4f (mean step %.4f)" % (
        name, y.shape[1] / sr, " ".join("%.0f" % r for r in rms), hi, j, s))


def main():
    a = sys.argv[1:]
    keep = None
    rep = False
    if "--keep" in a:
        i = a.index("--keep")
        keep = a[i + 1]
        del a[i:i + 2]
        os.makedirs(keep, exist_ok=True)
    if "--report" in a:
        a.remove("--report")
        rep = True
    names = a or list(BEDS) + EFFECTS
    sf = M.load_sf()
    os.makedirs(OUT, exist_ok=True)
    tmp = keep or os.path.join(OUT, ".tmp")
    os.makedirs(tmp, exist_ok=True)
    for name in names:
        if name in BEDS:
            y, ch, kbps = bed(name, sf), 2, 96
        else:
            y, ch = effect(name, sf)
            kbps = 96
        wav = os.path.join(tmp, name + ".wav")
        M.write_wav(wav, y)
        encode(wav, os.path.join(OUT, name + ".ogg"), ch, kbps)
        if not keep:
            os.remove(wav)
        if rep and name in BEDS:
            figures(name, y)
        print("%-16s %6.1f KB" % (name, os.path.getsize(os.path.join(OUT, name + ".ogg")) / 1024.0), flush=True)
    if not keep:
        try:
            os.rmdir(tmp)
        except OSError:
            pass


if __name__ == "__main__":
    main()
