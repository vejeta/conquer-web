# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""A small SoundFont 2 sampler in numpy (no fluidsynth needed).

Parses a .sf2 (samples, key and velocity zones, loops, volume envelopes,
pan, tuning), and renders notes: pitch-shifted by interpolation, looped,
with the zone's ADSR (optionally overridden), vibrato and constant-power pan.
Used by tools/story/music.py with FluidR3_GM.sf2 (see tools/story/README.md).
"""
import struct

import numpy as np

SR = 48000


class SF2:
    def __init__(self, path):
        data = open(path, "rb").read()
        assert data[:4] == b"RIFF" and data[8:12] == b"sfbk"
        chunks = {}
        pos = 12
        while pos < len(data):
            tag, size = struct.unpack("<4sI", data[pos:pos + 8])
            if tag == b"LIST":
                kind = data[pos + 8:pos + 12]
                p = pos + 12
                while p < pos + 8 + size:
                    t2, s2 = struct.unpack("<4sI", data[p:p + 8])
                    chunks[(kind, t2)] = data[p + 8:p + 8 + s2]
                    p += 8 + s2 + (s2 & 1)
            pos += 8 + size + (size & 1)
        self.smpl = np.frombuffer(chunks[(b"sdta", b"smpl")], dtype="<i2")
        pd = lambda n: chunks[(b"pdta", n)]
        self.phdr = [struct.unpack("<20sHHHIII", pd(b"phdr")[i:i + 38]) for i in range(0, len(pd(b"phdr")), 38)]
        self.pbag = np.frombuffer(pd(b"pbag"), dtype="<u2").reshape(-1, 2)
        self.pgen = self._gens(pd(b"pgen"))
        self.inst = [struct.unpack("<20sH", pd(b"inst")[i:i + 22]) for i in range(0, len(pd(b"inst")), 22)]
        self.ibag = np.frombuffer(pd(b"ibag"), dtype="<u2").reshape(-1, 2)
        self.igen = self._gens(pd(b"igen"))
        self.shdr = [struct.unpack("<20sIIIIIBbHH", pd(b"shdr")[i:i + 46]) for i in range(0, len(pd(b"shdr")), 46)]
        self._cache = {}
        self._zones = {}

    @staticmethod
    def _gens(raw):
        return [struct.unpack("<Hh", raw[i:i + 4]) for i in range(0, len(raw), 4)]

    def presets(self):
        return [(p[0].split(b"\0")[0].decode("latin1"), p[2], p[1]) for p in self.phdr[:-1]]

    def find(self, bank, program):
        for i, p in enumerate(self.phdr[:-1]):
            if p[2] == bank and p[1] == program:
                return i
        raise KeyError((bank, program))

    @staticmethod
    def _range(v):
        return (v & 0xFF, (v >> 8) & 0xFF)

    def _zone_list(self, bags, gens, first, last):
        """[(generators dict)] for bag indices first..last-1; the first one is global if it has no terminal generator"""
        out = []
        for b in range(first, last):
            g0, g1 = bags[b][0], bags[b + 1][0]
            d = {}
            for op, amt in gens[g0:g1]:
                if op in (43, 44):
                    d[op] = self._range(amt & 0xFFFF)
                else:
                    d[op] = amt
            out.append(d)
        return out

    def zones(self, bank, program):
        """list of dicts: key range, vel range and the merged generators of each sample zone of the preset"""
        k = (bank, program)
        if k in self._zones:
            return self._zones[k]
        pi = self.find(bank, program)
        p0, p1 = self.phdr[pi][3], self.phdr[pi + 1][3]
        pz = self._zone_list(self.pbag, self.pgen, p0, p1)
        pglobal = pz[0] if pz and 41 not in pz[0] else {}
        res = []
        for z in pz:
            if 41 not in z:
                continue
            merged_p = dict(pglobal)
            merged_p.update(z)
            inst = z[41]
            i0, i1 = self.inst[inst][1], self.inst[inst + 1][1]
            iz = self._zone_list(self.ibag, self.igen, i0, i1)
            iglobal = iz[0] if iz and 53 not in iz[0] else {}
            for q in iz:
                if 53 not in q:
                    continue
                g = dict(iglobal)
                g.update(q)
                for op, v in merged_p.items():        # preset generators add to instrument ones (not ranges)
                    if op in (41, 43, 44, 53, 54, 58, 57):
                        continue
                    g[op] = g.get(op, 0) + v
                kr = g.get(43, (0, 127))
                vr = g.get(44, (0, 127))
                pk, pv = merged_p.get(43, (0, 127)), merged_p.get(44, (0, 127))
                kr = (max(kr[0], pk[0]), min(kr[1], pk[1]))
                vr = (max(vr[0], pv[0]), min(vr[1], pv[1]))
                res.append({"kr": kr, "vr": vr, "g": g})
        self._zones[k] = res
        return res

    def sample(self, sid):
        if sid not in self._cache:
            h = self.shdr[sid]
            self._cache[sid] = self.smpl[h[1]:h[2]].astype(np.float32) / 32768.0
        return self._cache[sid], self.shdr[sid]


def tc(x):
    return 2.0 ** (x / 1200.0)


def render_note(sf, bank, program, key, vel, dur, att=None, rel=None, vib=None, tune=0.0, sr=SR, gain=1.0):
    """One note: returns (left, right) float32 arrays, `dur` s held plus the release tail.
    vib = (rate Hz, depth cents, delay s, phase) or None."""
    outs = []
    for z in sf.zones(bank, program):
        if not (z["kr"][0] <= key <= z["kr"][1] and z["vr"][0] <= vel <= z["vr"][1]):
            continue
        g = z["g"]
        s, h = sf.sample(g[53])
        start, end, ls, le = h[1], h[2], h[3], h[4]
        base = h[1]
        ofs = g.get(0, 0) + 32768 * g.get(4, 0)
        eofs = g.get(1, 0) + 32768 * g.get(12, 0)
        lso = g.get(2, 0) + 32768 * g.get(45, 0)
        leo = g.get(3, 0) + 32768 * g.get(50, 0)
        a0 = ofs
        a1 = len(s) + eofs
        l0 = ls - base + lso
        l1 = le - base + leo
        mode = g.get(54, 0) & 3
        looped = mode in (1, 3) and l1 - l0 > 8
        root = g.get(58, -1)
        if root < 0:
            root = h[6]
        semis = (key - root) * (g.get(56, 100) / 100.0) + g.get(51, 0) + g.get(52, 0) / 100.0 + h[7] / 100.0 + tune / 100.0
        ratio = tc(semis * 100.0) * h[5] / sr
        # envelope
        e_att = att if att is not None else tc(g.get(34, -12000))
        e_hold = tc(g.get(35, -12000))
        e_dec = tc(g.get(36, -12000))
        e_sus = 10 ** (-max(0, g.get(37, 0)) / 200.0)
        e_rel = rel if rel is not None else min(tc(g.get(38, -12000)), 6.0)
        if rel is not None:
            e_rel = rel
        e_att = max(e_att, 0.004)
        e_rel = max(e_rel, 0.03)
        n_hold = int((dur) * sr)
        n_tot = n_hold + int(e_rel * sr * 1.0)
        t = np.arange(n_tot) / sr
        inc = np.full(n_tot, ratio, dtype=np.float64)
        if vib:
            rate, depth, delay, ph = vib
            amt = np.clip((t - delay) / 1.2, 0, 1) * depth
            inc = inc * 2.0 ** ((amt * np.sin(2 * np.pi * rate * t + ph)) / 1200.0)
        pos = a0 + np.concatenate(([0.0], np.cumsum(inc[:-1])))
        if looped:
            over = pos >= l1
            pos = np.where(over, l0 + np.mod(pos - l0, l1 - l0), pos)
        alive = pos < a1 - 2
        if not alive.all():
            n_alive = int(np.argmin(alive))
            if n_alive == 0:
                continue
            pos = pos[:n_alive]
            t = t[:n_alive]
            n_tot = n_alive
        i0 = np.floor(pos).astype(np.int64)
        fr = (pos - i0).astype(np.float32)
        i1 = np.minimum(i0 + 1, len(s) - 1)
        y = s[i0] * (1 - fr) + s[i1] * fr
        # volume envelope
        env = np.ones(n_tot, dtype=np.float32)
        ta = e_att
        env = np.minimum(t / ta, 1.0).astype(np.float32)
        td = t - ta - e_hold
        decay = np.maximum(e_sus, np.exp(-np.clip(td, 0, None) * (6.9 / max(e_dec, 1e-3))))
        if g.get(37, 0) <= 0 and mode in (1, 3):
            decay = np.ones_like(env)
        env = env * decay.astype(np.float32)
        # release
        rt = t - dur
        relg = np.where(rt > 0, np.clip(1 - rt / e_rel, 0, 1) ** 2, 1.0).astype(np.float32)
        env = env * relg
        att_db = g.get(48, 0) / 10.0 * 0.4          # initial attenuation (softened, the soundfont is loud)
        amp = 10 ** (-att_db / 20.0) * (vel / 127.0) ** 1.3 * gain
        y = y * env * amp
        pan = np.clip(g.get(17, 0) / 500.0, -1, 1) * 0.5 + 0.5
        l, r = np.cos(pan * np.pi / 2), np.sin(pan * np.pi / 2)
        outs.append((y * l * 1.414, y * r * 1.414))
    if not outs:
        return None
    n = max(len(o[0]) for o in outs)
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    for l, r in outs:
        L[:len(l)] += l
        R[:len(r)] += r
    return L, R
