# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The score of the story (about 90 s): eight scenes, D dorian, one theme.

The score is a list of events, built per scene in scene time and shifted to
where the scene starts in the video (or to 0 for a per-scene file):

  notes   sampled instruments (tools/story/sf2.py): stem, (bank, program),
          t, dur, midi key, velocity, options (att, rel, vib, wet, big, pan, ens, lp)
  voices  the soprano (tools/story/voice.py): t, dur, midi, vowels, velocity
  sfx     effects (tools/story/sfx.py): t, name, level
  auto    stem gain curves in dB: {stem: [(t, dB), ...]}
  rain, wind, hum   spans (t0, t1, level) of the beds

THE THEME (2/4, eight bars, quarter = beat): a fifth leap up, then stepwise
and falling; the first four bars end open (on E, over Am), the answer closes on D.

    Dm          G           C            Am
    D4 A4 | B4. A4 | G4 F4 E4 | F4 E4   ||
    Dm          C             G            Dm
    D4 A4 | B4 C5 D5 | B4 A4 G4 | F4 E4 D4

Scene by scene: 1 pedal + distant horn; 2 ostinato, the oboe states the theme;
3 four motifs; 4 march, the violas carry the theme; 5 one violin; 6 bells, then
the tutti with choir and soprano; 7 cello and harp, the answer in D major;
8 the closed theme, a fanfare, a held D major chord.
"""
import itertools

GAP = 0.6

# (bank, program) in FluidR3_GM
VLN, VLA, VC, CB = (0, 40), (0, 41), (0, 42), (0, 43)
STR, SLOW, TREM, PIZZ = (0, 48), (0, 49), (0, 44), (0, 45)
HARP, TIMP = (0, 46), (0, 47)
AH, OH = (0, 52), (0, 53)
TRPT, TBN, TUBA, HORN, BRASS = (0, 56), (0, 57), (0, 58), (0, 60), (0, 61)
OBOE, FLUTE = (0, 68), (0, 73)
CEL, GLOCK = (0, 8), (0, 9)
TAIKO = (0, 116)
KIT = (128, 48)          # the orchestra kit: 38 snare, 49 crash

# ---- the theme ---------------------------------------------------------------------
THEME = [[(62, 1), (69, 1)], [(71, 1.5), (69, .5)], [(67, 1), (65, .5), (64, .5)], [(65, 1), (64, 1)],
         [(62, 1), (69, 1)], [(71, 1), (72, .5), (74, .5)], [(71, 1), (69, .5), (67, .5)], [(65, .5), (64, .5), (62, 1)]]
CLOSED_4 = [(65, .5), (64, .5), (62, 1)]
DM, G, C, AM = (2, 5, 9), (7, 11, 2), (0, 4, 7), (9, 0, 4)
CHORDS = [DM, G, C, AM, DM, C, G, DM]
BASS = [38, 43, 36, 45, 38, 36, 43, 38]          # root of each bar (D2 G2 C2 A2 ...)


def major(m):
    return m + 1 if m % 12 in (5, 0) else m      # the answer in D major: F -> F#, C -> C#


def theme(t0, bpm, bars=range(8), closed=False, to_major=False):
    """[(t, dur, midi, bar)] for the chosen bars of the theme, back to back from t0"""
    b = 60.0 / bpm
    out, t = [], t0
    for i in bars:
        notes = CLOSED_4 if (closed and i == 3) else THEME[i]
        for m, d in notes:
            out.append((t, d * b, major(m) if to_major else m, i))
            t += d * b
    return out


def span(t0, bpm, nbars):
    return t0 + 2 * (60.0 / bpm) * nbars


def voicing(pcs, prev, lo, hi):
    """one pitch per voice (lowest first) from the chord tones, each inside [lo, hi],
    the least total motion from prev, every chord tone present"""
    cands = [sorted([m for m in range(lo[i], hi[i] + 1) if m % 12 in pcs], key=lambda m, p=p: abs(m - p))[:3] for i, p in enumerate(prev)]
    best, cost = None, 1e9
    for combo in itertools.product(*cands):
        if len({m % 12 for m in combo}) < len(pcs) or list(combo) != sorted(combo):
            continue
        k = sum(abs(a - b) for a, b in zip(combo, prev))
        if k < cost:
            best, cost = combo, k
    return list(best) if best else list(prev)


class Score:
    def __init__(self):
        self.notes, self.voices, self.sfx, self.auto = [], [], [], {}
        self.rain, self.wind, self.hum = [], [], []
        self.t0 = 0.0

    def n(self, stem, inst, t, dur, key, vel, **kw):          # t in scene time
        self.notes.append(dict(stem=stem, inst=inst, t=self.t0 + t, dur=dur, key=int(key), vel=vel, **kw))

    def v(self, t, dur, midi, vowels, vel, **kw):
        self.voices.append(dict(t=self.t0 + t, dur=dur, midi=midi, vowels=vowels, vel=vel, **kw))

    def fx(self, t, name, level=1.0):
        self.sfx.append(dict(t=self.t0 + t, name=name, level=level))

    def gain(self, stem, pts):
        self.auto.setdefault(stem, []).extend((self.t0 + t, db) for t, db in pts)

    def R(self, t0, t1, lv):
        self.rain.append((self.t0 + t0, self.t0 + t1, lv))

    def W(self, t0, t1, lv):
        self.wind.append((self.t0 + t0, self.t0 + t1, lv))

    def H(self, t0, t1, lv):
        self.hum.append((self.t0 + t0, self.t0 + t1, lv))


def tutti_theme(S, t, bpm, bars, closed, vel):
    """the theme in horns (octaves), violins an octave above and violas, with a trumpet"""
    for tn, d, m, bar in theme(t, bpm, bars=bars, closed=closed):
        S.n("brass", HORN, tn, d * 1.03, m, vel + 8, att=0.07, rel=0.5, vib=(5.0, 10, 0.4, 0), wet=0.6, big=True, ens=True, pan=-0.25)
        S.n("brass", HORN, tn, d * 1.03, m - 12, vel + 2, att=0.07, rel=0.5, wet=0.6, big=True, pan=0.25)
        S.n("strings", STR, tn, d * 1.03, m + 12, vel, att=0.09, rel=0.5, vib=(5.4, 16, 0.3, 0), wet=0.6, big=True, ens=True, pan=-0.2)
        S.n("strings", VLA, tn, d * 1.03, m, vel - 6, att=0.09, rel=0.5, wet=0.6, big=True, ens=True)
        S.n("brass", TRPT, tn, d * 1.03, m, vel - 28, att=0.06, rel=0.4, wet=0.6, big=True, pan=0.15)


# ---- the scenes ------------------------------------------------------------------------
def scene1(S, D, L):
    S.n("strings", CB, 0.2, L + 1.5, 26, 40, att=3.5, rel=2.5, wet=0.3)            # a low D pedal
    S.n("strings", VC, 0.8, L + 0.5, 38, 36, att=3.0, rel=2.5, wet=0.3)
    S.n("strings", VC, 4.6, L - 3.5, 45, 28, att=2.8, rel=2.5, wet=0.3)
    S.n("brass", HORN, 3.1, 3.0, 57, 52, att=0.5, rel=2.5, wet=1.0, big=True, lp=1700, pan=0.3)     # far away
    S.n("strings", STR, 6.4, 4.0, 74, 24, att=2.8, rel=3.0, wet=0.8, ens=True)
    S.R(0.0, L + 1.0, 1.0)
    S.H(0.0, L + 2.0, 0.35)
    S.gain("strings", [(0, -8), (L, -2)])


def scene2(S, D, L):
    bpm = 88.0
    b = 60.0 / bpm
    e = b / 2
    t0 = 0.5
    for bar in range(8):                  # the ostinato: root, fifth, third, fifth in eighths
        pcs = CHORDS[bar]
        root = BASS[bar] + 12
        third = [m for m in range(root, root + 12) if m % 12 == pcs[1]][0]
        for i, m in enumerate([root + 12, root + 19, third + 12, root + 19]):
            S.n("strings", STR, t0 + (bar * 4 + i) * e, e * 1.6, m, 36 + int(14 * bar / 7.0) + (4 if i == 0 else 0),
                att=0.03, rel=0.25, wet=0.45, ens=True, pan=-0.3 if i % 2 else 0.3)
        S.n("strings", PIZZ, t0 + bar * 4 * e, 1.0, BASS[bar], 54, wet=0.4)
        S.n("strings", VC, t0 + bar * 4 * e, 4 * e * 1.05, BASS[bar], 38 + bar * 2, att=0.35, rel=0.5, wet=0.4)
    S.n("strings", CB, 0.1, L, 26, 38, att=2.0, rel=2.0, wet=0.3)
    for t, d, m, bar in theme(t0 + 0.2, bpm):          # the theme: solo oboe, the flute joins for the answer
        S.n("solo", OBOE, t, d * 1.04, m, 76 + (6 if bar >= 4 else 0), att=0.06, rel=0.35, vib=(5.2, 18, 0.35, 0), wet=0.55, pan=0.15)
        if bar >= 4:
            S.n("solo", FLUTE, t, d * 1.04, m + 12, 46, att=0.07, rel=0.35, vib=(5.0, 14, 0.4, 1), wet=0.6, pan=-0.2)
    S.R(0.0, 2.8, 0.5)
    S.H(0.0, L + 0.5, 0.3)
    S.fx(0.02 * D, "teletype", 0.8)
    S.gain("strings", [(0, -9), (6, -6), (L, -5)])


def scene3(S, D, L):
    cue = lambda f: f * D
    S.n("strings", CB, 0.0, L + 1, 26, 40, att=1.2, rel=1.5, wet=0.3)               # D underneath all four
    S.n("strings", VC, 0.0, L + 1, 38, 38, att=1.2, rel=1.5, wet=0.3)
    S.n("strings", SLOW, 0.0, L, 57, 28, att=2.0, rel=2.0, wet=0.5, ens=True)
    # humans: horns call, snare answers
    t, b = cue(0.13) - 0.15, 0.5
    for dt, d, m, v in [(0, b, 62, 78), (b, b, 69, 84), (2 * b, 1.5 * b, 72, 90), (3.5 * b, 0.5 * b, 71, 86), (4 * b, 2 * b, 69, 92)]:
        S.n("brass", HORN, t + dt, d * 1.1, m, v, att=0.05, rel=0.4, wet=0.5, ens=True, pan=-0.3)
        S.n("brass", HORN, t + dt, d * 1.1, m - 12, v - 12, att=0.05, rel=0.4, wet=0.5, pan=0.3)
    for i in range(10):
        S.n("perc", KIT, t + i * 0.25, 0.2, 38, 50 + i * 4, wet=0.25)
    # elves: harp arpeggio, high strings, the soprano
    t = cue(0.36) - 0.15
    for i, m in enumerate([74, 77, 81, 84, 86, 89, 93, 89, 86]):
        S.n("keys", HARP, t + i * 0.13, 2.2, m if m <= 90 else m - 12, 66, wet=0.55, pan=-0.4 + 0.1 * i)
    for m, dd in [(81, 0), (84, 0.3)]:
        S.n("strings", VLN, t + 0.3 + dd, 2.4, m, 40, att=0.8, rel=1.2, wet=0.8, big=True, vib=(5.6, 14, 0.5, 0), ens=True)
    S.v(t + 0.5, 2.2, 88, ["a"], 70, wet=0.9)
    # dwarves: timpani, low brass, the anvil (the effect comes with the cue)
    t = cue(0.59) - 0.1
    for dt, m, v in [(0, 38, 105), (0.5, 33, 100), (1.4, 38, 80)]:
        S.n("perc", TIMP, t + dt, 1.0, m, v, wet=0.4)
    for dt, m, d in [(0, 38, 0.9), (0.5, 45, 0.8), (0.95, 38, 1.6)]:
        S.n("brass", TBN, t + dt, d, m, 88, att=0.08, rel=0.4, wet=0.35)
        S.n("brass", TUBA, t + dt, d, m - 12, 80, att=0.08, rel=0.4, wet=0.3)
    S.fx(cue(0.59) + 0.95, "anvil", 0.9)
    S.fx(cue(0.59) + 1.45, "anvil", 0.8)
    S.fx(cue(0.59) + 1.9, "anvil", 0.6)
    # orcs: taiko, low choir "oh", dissonant brass
    t = cue(0.79) - 0.1
    for i, dt in enumerate([0, 0.33, 0.66, 1.0, 1.33, 1.66, 2.0]):
        S.n("perc", TAIKO, t + dt, 0.6, 38 if i % 3 == 0 else 45, 95 - (i % 3) * 10, wet=0.4)
    for m in (38, 45, 50):
        S.n("choir", OH, t, 3.6, m, 84, att=0.3, rel=0.9, wet=0.5, ens=True)
    for m in (50, 56, 62):                      # D + Ab + D: a tritone over the pedal
        S.n("brass", BRASS, t + 0.2, 2.0, m, 100, att=0.05, rel=1.0, wet=0.4)
    S.n("brass", TBN, t + 0.2, 2.0, 51, 96, att=0.05, rel=1.0, wet=0.4)
    S.gain("strings", [(0, -7), (L, -7)])


def scene4(S, D, L):
    bpm = 108.0
    b = 60.0 / bpm
    e = b / 2
    t0 = 0.35
    for bar in range(int((L - t0) / (2 * b))):
        k = bar % 8
        pcs = CHORDS[k]
        root = BASS[k] + 12
        third = [m for m in range(root, root + 12) if m % 12 == pcs[1]][0]
        for i, m in enumerate([root + 12, root + 19, third + 12, root + 19]):
            S.n("strings", STR, t0 + (bar * 4 + i) * e, e * 0.9, m, 58 + (6 if i % 2 == 0 else 0), att=0.015, rel=0.12, wet=0.3, ens=True)
        S.n("strings", VC, t0 + bar * 2 * b, b * 1.4, BASS[k], 78, att=0.05, rel=0.2, wet=0.25)
        S.n("strings", CB, t0 + bar * 2 * b, b * 1.4, BASS[k] - 12, 76, att=0.05, rel=0.2, wet=0.25)
        for dt, v in [(0, 84), (b, 66), (b * 1.5, 50)]:      # march snare
            S.n("perc", KIT, t0 + bar * 2 * b + dt, 0.2, 38, v, wet=0.2)
        S.n("perc", TIMP, t0 + bar * 2 * b, 0.8, BASS[k], 86 if bar % 2 == 0 else 70, wet=0.3)
    for t, d, m, bar in theme(t0, bpm):                # the theme in the violas, the cellos an octave below
        if t > L - 0.5:
            break
        S.n("strings", VLA, t, d * 1.02, m, 80, att=0.08, rel=0.25, vib=(5.0, 14, 0.3, 0), wet=0.35, ens=True)
        S.n("strings", VC, t, d * 1.02, m - 12, 62, att=0.08, rel=0.25, vib=(4.8, 12, 0.3, 1), wet=0.35)
    d4, k = 4 * b, 0                                   # a brass swell for each "day"
    while 0.9 + k * d4 < L - 1.0:
        ts, r = 0.9 + k * d4, BASS[(k * 2) % 8]
        for m in (r + 12, r + 19):
            S.n("brass", HORN, ts, d4 * 0.8, m, 70 + 4 * k, att=d4 * 0.55, rel=0.35, wet=0.4, ens=True)
        S.n("brass", TBN, ts, d4 * 0.8, r, 66 + 4 * k, att=d4 * 0.55, rel=0.35, wet=0.35)
        k += 1
    S.fx(0.68 * D, "teletype", 0.7)
    S.gain("strings", [(0, -7), (L - 1.5, -4), (L, -9)])


def scene5(S, D, L):
    # everything thins: one violin, one flute, wind and a little rain
    for t, d, m, v in [(0.9, 4.0, 74, 56), (4.6, 3.0, 72, 48), (7.2, 2.2, 69, 40)]:
        S.n("solo", VLN, t, d, m, v, att=0.9, rel=1.5, vib=(5.3, 22, 0.6, 0), wet=0.85, big=True, pan=0.1)
    S.n("solo", FLUTE, 1.5, 3.6, 62, 36, att=1.0, rel=1.4, vib=(4.9, 12, 0.5, 0), wet=0.9, pan=-0.3)
    S.n("strings", CB, 0.0, 3.0, 26, 30, att=1.2, rel=2.0, wet=0.4)
    for f in (0.12, 0.25, 0.38, 0.5, 0.62, 0.8):
        S.fx(f * D, "off", 0.9)
    for m in (43, 50, 58):                               # a bare minor cadence: Gm, then Dm
        S.n("strings", VC, 5.5, 2.0, m, 36, att=0.5, rel=1.2, wet=0.7, big=True)
    for m in (38, 45, 53, 57):
        S.n("strings", VC if m < 55 else VLA, 7.4, 3.4, m, 34, att=0.6, rel=2.0, wet=0.7, big=True)
    S.R(0.0, L + 1.0, 0.28)
    S.W(0.0, L + 1.0, 1.0)


def scene6(S, D, L):
    for i, f in enumerate((0.04, 0.10, 0.16, 0.22)):      # the four rune bells
        t = f * D
        S.n("keys", CEL, t, 2.2, [74, 77, 81, 86][i], 82, wet=0.8, big=True, pan=-0.4 + 0.27 * i)
        S.n("keys", GLOCK, t, 2.5, [74, 77, 81, 86][i] + 12, 54, wet=0.8, big=True, pan=-0.4 + 0.27 * i)
    tt = 0.28 * D                                         # "speak, friend": the pedal, a tremolo, a timpani roll
    S.n("strings", CB, tt, L - tt + 1.0, 26, 70, att=2.0, rel=2.0, wet=0.3)
    S.n("strings", VC, tt, L - tt + 1.0, 38, 66, att=2.0, rel=2.0, wet=0.3)
    for m in (57, 62, 65, 69):
        S.n("strings", TREM, tt + 0.2, 3.1, m, 50, att=1.8, rel=0.3, wet=0.5, ens=True)
    t_stone, t_theme = 0.46 * D, 0.56 * D
    t = t_stone
    while t < t_theme + 0.05:
        S.n("perc", TIMP, t, 0.5, 38, int(48 + 56 * (t - t_stone) / (t_theme - t_stone)), wet=0.4, big=True)
        t += 0.11 - 0.05 * (t - t_stone) / (t_theme - t_stone)
    bpm, t = 100.0, t_theme                               # THE TUTTI: phrase A, then a held cadence
    b = 60.0 / bpm
    end = span(t, bpm, 4)
    S.fx(t - 0.05, "crash", 0.9)
    S.fx(t - 0.6, "swell", 0.8)
    tutti_theme(S, t, bpm, range(4), False, 96)
    prev_c, prev_t = [57, 62, 65, 69], [38, 45, 50, 53]
    for bar, pcs in enumerate([DM, G, C, AM]):
        t_b = t + bar * 2 * b
        prev_c = voicing(pcs, prev_c, [52, 57, 62, 66], [62, 69, 74, 79])
        for m in prev_c:
            S.n("choir", AH, t_b, 2 * b + 0.1, m, 92, att=0.12, rel=0.6, wet=0.7, big=True, ens=True)
        prev_t = voicing(pcs, prev_t, [34, 40, 45, 50], [46, 52, 57, 62])
        for m in prev_t:
            S.n("brass", TBN, t_b, 2 * b, m, 90, att=0.08, rel=0.5, wet=0.5, big=True)
        S.n("strings", CB, t_b, 2 * b, BASS[bar] - 12, 100, att=0.05, rel=0.4, wet=0.4)
        S.n("strings", VC, t_b, 2 * b, BASS[bar], 98, att=0.05, rel=0.4, wet=0.4)
        S.n("perc", TIMP, t_b, 1.4, BASS[bar], 112, wet=0.5, big=True)
        S.n("perc", TIMP, t_b + b, 1.0, BASS[bar], 90, wet=0.5, big=True)
    for m in (45, 52, 57, 60, 64, 69):                    # held: Am, open, fading into the next scene
        S.n("strings", SLOW, end, L - end + 1.2, m, 84, att=0.2, rel=2.2, wet=0.8, big=True, ens=True)
    for m in (57, 64, 69):
        S.n("choir", AH, end, L - end + 0.9, m, 80, att=0.2, rel=2.0, wet=0.8, big=True, ens=True)
    S.n("perc", TIMP, end, 2.5, 45, 108, wet=0.6, big=True)
    vows = [["i"], ["a"], ["i"], ["e"], ["e", "a"], ["i"], ["a"], ["a"]]       # "Dic a-mi-ce et in-tra"
    for idx, (tn, d, m, bar) in enumerate(theme(t, bpm, bars=range(4))):
        S.v(tn, d * 1.05, m + 12, vows[idx % len(vows)], 96, wet=0.7, big=True)
    S.v(end, L - end + 0.6, 88, ["a"], 90, wet=0.8, big=True)
    S.gain("strings", [(0, -2), (t_theme, 0), (L, -2)])


def scene7(S, D, L):
    bpm = 72.0
    b = 60.0 / bpm
    e = b / 2
    t0 = 1.0
    S.n("strings", CB, 0.0, 4.0, 26, 30, att=1.5, rel=2.5, wet=0.5)
    for bar, c in enumerate([(50, 57, 62, 66), (45, 52, 57, 61), (43, 50, 55, 59), (50, 57, 62, 66)]):
        for rep in range(2):                              # harp arpeggios, over D, A, G, D major
            for i, m in enumerate(c):
                S.n("keys", HARP, t0 + bar * 2 * b + rep * b + i * e / 2 * 1.0, 1.8, m + (12 if i == 3 else 0), 52 - i * 2 + rep * 3, wet=0.55, pan=-0.2 + 0.1 * i)
    for t, d, m, bar in theme(t0, bpm, bars=range(4, 8), to_major=True):   # the cello sings the answer
        S.n("solo", VC, t, d * 1.05, m - 12, 74, att=0.1, rel=0.5, vib=(5.0, 20, 0.35, 0), wet=0.6, pan=-0.15)
    for m in (50, 57, 62, 66, 69):
        S.n("strings", SLOW, 5.2, L - 3.8, m, 30, att=2.5, rel=2.5, wet=0.8, big=True, ens=True)
    S.fx(0.04 * D, "quill", 0.8)
    S.fx(0.26 * D, "quill", 0.8)
    S.fx(0.7 * D, "seal", 0.8)
    S.gain("strings", [(0, -4), (L, -2)])


def scene8(S, D, L):
    bpm = 112.0
    b = 60.0 / bpm
    t = 0.2
    tutti_theme(S, t, bpm, range(4), True, 88)             # the closed theme
    prev_c = [57, 62, 65, 69]
    for bar, pcs in enumerate([DM, G, C, DM]):
        t_b = t + bar * 2 * b
        prev_c = voicing(pcs, prev_c, [52, 57, 62, 66], [62, 69, 74, 79])
        for m in prev_c:
            S.n("choir", AH, t_b, 2 * b + 0.1, m, 86, att=0.12, rel=0.5, wet=0.7, big=True, ens=True)
        r = [38, 43, 36, 38][bar]
        S.n("strings", CB, t_b, 2 * b, r - 12, 96, att=0.05, rel=0.4, wet=0.4)
        S.n("strings", VC, t_b, 2 * b, r, 94, att=0.05, rel=0.4, wet=0.4)
        S.n("perc", TIMP, t_b, 1.2, r, 100, wet=0.5, big=True)
    tf = 0.62 * D                                         # the short fanfare, then the held chord in D major
    for i, m in enumerate((62, 69, 74)):
        S.n("brass", TRPT, tf - 0.1 + i * 0.16, 0.6, m, 100, att=0.03, rel=0.3, wet=0.6, big=True)
        S.n("brass", HORN, tf - 0.1 + i * 0.16, 0.6, m - 12, 96, att=0.03, rel=0.3, wet=0.6, big=True)
    th = tf + 0.45
    hold = L + 2.0 - th
    for m in (38, 45, 50, 57, 62, 66, 69):
        S.n("strings", SLOW, th, hold, m, 90, att=0.12, rel=3.0, wet=0.9, big=True, ens=True)
    for m in (50, 57, 62, 66):
        S.n("brass", HORN, th, hold - 1.0, m, 96, att=0.15, rel=2.5, wet=0.8, big=True, ens=True)
    for m in (62, 66, 69, 74):
        S.n("brass", TRPT, th, hold - 2.5, m, 70, att=0.12, rel=1.8, wet=0.8, big=True)
    for m in (57, 62, 66, 69):
        S.n("choir", AH, th, hold, m, 84, att=0.2, rel=3.0, wet=0.9, big=True, ens=True)
    S.n("perc", TIMP, th, 3.0, 38, 112, wet=0.6, big=True)
    S.n("perc", TIMP, th + 0.3, 3.0, 45, 100, wet=0.6, big=True)
    S.fx(th, "crash", 0.6)
    S.v(th, hold - 0.5, 86, ["a"], 90, wet=0.9, big=True)
    S.v(th + 0.4, hold - 1.5, 93, ["a"], 70, wet=0.95, big=True)
    S.H(0.82 * D, 40.0, 0.5)
    for stem, lv in (("strings", 0), ("brass", 0), ("choir", 0)):
        S.gain(stem, [(0, -3), (th, lv), (th + 2.5, -8), (th + 6, -18)])
    S.gain("perc", [(th, 0), (th + 4, -10)])


SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8]


def build(durations, starts=None, only=None):
    """The score for the video (starts: when each scene begins; default one after another)
    or, with only=k, scene k alone at time 0"""
    S = Score()
    if starts is None:
        starts, t = [], 0.0
        for d in durations:
            starts.append(t)
            t += d + GAP
    for i, fn in enumerate(SCENES):
        if only is not None and i + 1 != only:
            continue
        S.t0 = 0.0 if only is not None else starts[i]
        fn(S, durations[i], durations[i] + GAP)
    S.t0 = 0.0
    return S
