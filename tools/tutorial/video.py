#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the narrated first-turn videos (one per language).

Each narration segment (narration.json) becomes one shot: the recorded game
screen of that step (first-turn.screens.json) with its title and keys, held
for as long as the narrator speaks. The voice is Kokoro, a neural
text-to-speech model that runs offline.

Needs: python3 -m pip install kokoro-onnx soundfile; ffmpeg; node with
playwright (for the frames). The Kokoro model files (about 350 MB) are
downloaded to ~/.cache/conquer-tts on first use.

usage: video.py [en|es ...]     (default: en es)
Writes web/tutorial/first-turn.<lang>.mp4 and .vtt
"""
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "..", "web")
CACHE = os.path.expanduser("~/.cache/conquer-tts")
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FFMPEG = os.environ.get("FFMPEG", shutil.which("ffmpeg") or "ffmpeg")
GAP = 0.45          # silence after each sentence group, seconds
W, H = 1280, 720

TEXT = {
    "en": {"keys": "Keys", "look": "just look", "intro_title": "Your first turn",
           "intro_sub": "Usenet, 1987 · your browser, today", "outro_title": "Your nation is waiting",
           "outro_sub": "Ask for a nation · play your first turn tonight", "password": "password"},
    "es": {"keys": "Teclas", "look": "solo mira", "intro_title": "Tu primer turno",
           "intro_sub": "Usenet, 1987 · tu navegador, hoy", "outro_title": "Tu nación te espera",
           "outro_sub": "Pide una nación · juega tu primer turno esta noche", "password": "contraseña"},
}


def model_files():
    os.makedirs(CACHE, exist_ok=True)
    paths = []
    for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        path = os.path.join(CACHE, name)
        if not os.path.exists(path):
            print("downloading", name)
            urllib.request.urlretrieve(MODEL_URL + name, path + ".part")
            os.rename(path + ".part", path)
        paths.append(path)
    return paths


def screen_html(lines):
    rows = []
    for runs in lines:
        parts = []
        for text, attr in runs:
            t = html.escape(text)
            cls = " ".join(c for c, bit in (("rev", 1), ("b", 2)) if attr & bit)
            parts.append('<span class="%s">%s</span>' % (cls, t) if cls else t)
        rows.append("".join(parts).rstrip())
    return "\n".join(rows)


FRAME = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:%(w)dpx;height:%(h)dpx;background:#0d1117;color:#e6edf3;font-family:"DejaVu Sans",system-ui,sans-serif;overflow:hidden}
.wrap{display:grid;grid-template-columns:auto 1fr;gap:36px;align-items:center;height:100%%;padding:0 48px;box-sizing:border-box}
pre{margin:0;width:80ch;height:calc(24 * 1.3em);background:#1c1c1c;color:#d7d7d7;border:1px solid #30363d;border-radius:10px;padding:14px 16px;font:14.5px/1.3 "DejaVu Sans Mono",monospace;box-shadow:0 20px 60px rgba(0,0,0,.45)}
pre .rev{background:#d7d7d7;color:#1c1c1c} pre .b{font-weight:bold;color:#fff}
.side{display:flex;flex-direction:column;gap:18px}
.num{font:700 16px "DejaVu Sans Mono",monospace;color:#3fb950;letter-spacing:.1em}
h1{margin:0;font-size:34px;line-height:1.15}
.keys{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.label{color:#8b949e;font-size:15px;text-transform:uppercase;letter-spacing:.08em;margin-right:4px}
kbd{font:700 26px "DejaVu Sans Mono",monospace;border:2px solid #3fb950;border-bottom-width:5px;border-radius:8px;padding:4px 14px;color:#3fb950;background:#0f2417}
kbd.wide{font-size:20px;font-style:italic}
.none{color:#8b949e;font-style:italic;font-size:18px}
.brand{position:absolute;left:48px;bottom:22px;font:700 15px "DejaVu Sans Mono",monospace;letter-spacing:.35em;color:#3fb950;opacity:.8}
.card{display:flex;flex-direction:column;justify-content:center;align-items:flex-start;height:100%%;padding:0 110px;box-sizing:border-box}
.logo{font:700 110px/1 "DejaVu Sans Mono",monospace;letter-spacing:.3em;color:#3fb950;margin:0 0 26px}
.card h1{font-size:46px;margin:0 0 14px}.card p{font-size:24px;color:#8b949e;margin:0}
.boot{font:15px "DejaVu Sans Mono",monospace;color:#8b949e;margin-bottom:34px}
</style></head><body>%(body)s</body></html>"""


def frames(lang, content, screens, segments, outdir):
    t = TEXT[lang]
    steps = {s["id"]: (i, s) for i, s in enumerate(content["steps"], 1)}
    pages = []
    for n, seg in enumerate(segments):
        sid = seg["screen"]
        if sid in ("intro", "outro"):
            title, sub = (t["intro_title"], t["intro_sub"]) if sid == "intro" else (t["outro_title"], t["outro_sub"])
            boot = ('<div class="boot">conquer 4.12: Copyright (c) 1988 Edward M Barlow<br>'
                    'GPL v3 licensed version (c) 2025</div>') if sid == "intro" else ""
            body = '<div class="card">%s<div class="logo">CONQUER</div><h1>%s</h1><p>%s</p></div>' % (
                boot, html.escape(title), html.escape(sub))
        else:
            i, step = steps[sid]
            keys = "".join('<kbd class="wide">%s</kbd>' % t["password"] if k == "password"
                           else "<kbd>%s</kbd>" % html.escape(k) for k in step["keys"])
            keys = keys or '<span class="none">%s</span>' % t["look"]
            title = seg.get("title_" + lang, step["title"])
            body = ('<div class="wrap"><pre>%s</pre><div class="side"><div class="num">%02d / %02d</div>'
                    '<h1>%s</h1><div class="keys"><span class="label">%s</span>%s</div></div></div>'
                    '<div class="brand">CONQUER</div>') % (
                screen_html(screens[sid]), i, len(content["steps"]), html.escape(title), t["keys"], keys)
        path = os.path.join(outdir, "frame%02d.html" % n)
        with open(path, "w") as f:
            f.write(FRAME % {"w": W, "h": H, "body": body})
        pages.append(path)
    subprocess.run(["node", os.path.join(HERE, "frames.js"), str(W), str(H)] + pages, check=True)
    return [p[:-5] + ".png" for p in pages]


def vtt_time(s):
    return "%02d:%02d:%06.3f" % (s // 3600, s % 3600 // 60, s % 60)


def render(lang, kokoro):
    import soundfile as sf
    import numpy as np
    content = json.load(open(os.path.join(HERE, "first-turn.content.json")))
    screens = {s["id"]: s["screen"] for s in json.load(open(os.path.join(HERE, "first-turn.screens.json")))}
    narration = json.load(open(os.path.join(HERE, "narration.json")))
    voice = narration["voices"][lang]
    segments = narration["segments"]
    tmp = tempfile.mkdtemp(prefix="conquer-video-")
    images = frames(lang, content, screens, segments, tmp)

    audio, cues, t0, sr = [], [], 0.0, 24000
    for seg in segments:
        samples, sr = kokoro.create(seg[lang], voice=voice["voice"], speed=voice["speed"], lang=voice["lang"])
        dur = len(samples) / sr + GAP
        audio.append(np.concatenate([samples, np.zeros(int(GAP * sr), dtype=samples.dtype)]))
        cues.append((t0, t0 + dur - GAP / 2, seg[lang], dur))
        t0 += dur
    wav = os.path.join(tmp, "voice.wav")
    sf.write(wav, np.concatenate(audio), sr)

    concat = os.path.join(tmp, "frames.txt")
    with open(concat, "w") as f:
        for img, cue in zip(images, cues):
            f.write("file '%s'\nduration %.3f\n" % (img, cue[3]))
        f.write("file '%s'\n" % images[-1])
    out = os.path.join(WEB, "tutorial", "first-turn.%s.mp4" % lang)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat, "-i", wav,
                    "-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
                    "-tune", "stillimage", "-c:a", "aac", "-b:a", "96k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    with open(os.path.join(WEB, "tutorial", "first-turn.%s.vtt" % lang), "w") as f:
        f.write("WEBVTT\n\n")
        for n, (a, b, text, _) in enumerate(cues, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (n, vtt_time(a), vtt_time(b), text))
    shutil.rmtree(tmp)
    print("wrote %s (%.0f s)" % (out, t0))


def main():
    from kokoro_onnx import Kokoro
    kokoro = Kokoro(*model_files())
    for lang in sys.argv[1:] or ["en", "es"]:
        render(lang, kokoro)


if __name__ == "__main__":
    main()
