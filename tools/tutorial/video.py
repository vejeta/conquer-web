#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the narrated first-turn videos (one per language).

Each narration segment (narration/<language>.json) becomes one shot: the
recorded game screen of that step (first-turn.screens.json) with its title
and keys, held for as long as the narrator speaks. The voices come from
offline neural text-to-speech models whose licenses allow publishing the
audio; each language's file says which one ("voice"):

  kokoro        Kokoro-82M (Apache-2.0): a built-in voice
  qwen-custom   Qwen3-TTS 1.7B CustomVoice (Apache-2.0): a built-in speaker,
                with an optional style instruction
  qwen-clone    Qwen3-TTS 1.7B Base (Apache-2.0) speaking with the voice of
                narration/voices/<language>.wav. That reference is designed
                once from a description with Qwen3-TTS VoiceDesign and kept
                in the repository, so the narrator stays the same.
  voxcpm        VoxCPM2 (Apache-2.0), for languages Qwen3-TTS does not
                speak (Polish...): a voice designed and kept the same way

Needs ffmpeg, node with playwright (for the frames) and, per engine:
  kokoro:  python3 -m pip install kokoro-onnx soundfile   (model files,
           about 350 MB, go to ~/.cache/conquer-tts on first use)
  qwen-*:  python3 -m pip install qwen-tts soundfile      (models, about
           4.5 GB each, go to ~/.cache/huggingface on first use; a GPU
           helps, on a 4-core CPU a video takes about 15 minutes)
  voxcpm:  python3 -m pip install voxcpm soundfile        (in its own
           virtual environment: its dependencies differ from qwen-tts)

usage: video.py [--video found-nation] [LANGUAGE ...]
  first-turn (the default): narration/<language>.json, every file there by
      default; writes web/tutorial/first-turn.<language>.mp4 and .vtt
  found-nation: the game's nation builder, narration/found-nation/<language>.json
      (spoken by the voice of narration/<language>.json); writes
      web/tutorial/found-nation.<language>.mp4 and .vtt
  trailer: 40 seconds on what Conquer is, over screens of the first turn,
      narration/trailer/<language>.json; writes web/tutorial/trailer.<language>.mp4
"""
import glob
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
html,body{margin:0;width:%(w)dpx;height:%(h)dpx;background:#0d1117;color:#e6edf3;font-family:"DejaVu Sans","WenQuanYi Zen Hei",system-ui,sans-serif;overflow:hidden}
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


def tutorial_steps(lang, content, key="steps"):
    """The tutorial's steps with their titles in this language (English
    where the tutorial is not translated)."""
    path = os.path.join(HERE, "i18n", lang + ".json")
    translated = json.load(open(path)).get(key, {}) if os.path.exists(path) else {}
    return [dict(s, **{k: v for k, v in translated.get(s["id"], {}).items() if k == "title"}) for s in content["steps"]]


def frames(t, steps_list, screens, segments, outdir):
    steps = {s["id"]: (i, s) for i, s in enumerate(steps_list, 1)}
    pages = []
    for n, seg in enumerate(segments):
        sid = seg["screen"]
        if sid in ("intro", "outro"):
            title, sub = (t["intro_title"], t["intro_sub"]) if sid == "intro" else (t["outro_title"], t["outro_sub"])
            boot = ('<div class="boot">conquer 4.12: Copyright (c) 1988 Edward M Barlow<br>'
                    'GPL v3 licensed version (c) 2025</div>') if sid == "intro" else ""
            body = '<div class="card">%s<div class="logo">CONQUER</div><h1>%s</h1><p>%s</p></div>' % (
                boot, html.escape(title), html.escape(sub))
        elif "caption" in seg:
            # A shot of the game with a title only (the trailer: no steps, no keys)
            body = ('<div class="wrap"><pre>%s</pre><div class="side"><h1>%s</h1></div></div>'
                    '<div class="brand">CONQUER</div>') % (screen_html(screens[sid]), html.escape(seg["caption"]))
        else:
            i, step = steps[seg.get("step", sid)]
            keys = "".join('<kbd class="wide">%s</kbd>' % t["password"] if k == "password"
                           else "<kbd>%s</kbd>" % html.escape(t.get("space", k) if k == "Space" else k)
                           for k in seg.get("keys", step["keys"]))
            keys = keys or '<span class="none">%s</span>' % t["look"]
            title = seg.get("title", step["title"])
            body = ('<div class="wrap"><pre>%s</pre><div class="side"><div class="num">%02d / %02d</div>'
                    '<h1>%s</h1><div class="keys"><span class="label">%s</span>%s</div></div></div>'
                    '<div class="brand">CONQUER</div>') % (
                screen_html(screens[sid]), i, len(steps_list), html.escape(title), t["keys"], keys)
        path = os.path.join(outdir, "frame%02d.html" % n)
        with open(path, "w") as f:
            f.write(FRAME % {"w": W, "h": H, "body": body})
        pages.append(path)
    subprocess.run(["node", os.path.join(HERE, "frames.js"), str(W), str(H)] + pages, check=True)
    return [p[:-5] + ".png" for p in pages]


def vtt_time(s):
    return "%02d:%02d:%06.3f" % (s // 3600, s % 3600 // 60, s % 60)


class Kokoro:
    def __init__(self):
        from kokoro_onnx import Kokoro as Model
        self.model = Model(*model_files())

    def speak(self, text, voice):
        return self.model.create(text, voice=voice["voice"], speed=voice["speed"], lang=voice["lang"])


def qwen_model(name):
    import torch
    from qwen_tts import Qwen3TTSModel
    torch.set_num_threads(os.cpu_count() or 4)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    return Qwen3TTSModel.from_pretrained(name, device_map=device, dtype=torch.bfloat16 if device != "cpu" else torch.float32)


class QwenCustom:
    def __init__(self):
        self.model = qwen_model("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")

    def speak(self, text, voice):
        wavs, sr = self.model.generate_custom_voice(text=text, speaker=voice["speaker"], language=voice["language"],
                                                    instruct=voice.get("instruct"))
        return wavs[0], sr


class QwenClone:
    """The voice of narration/voices/<language>.wav, designed on first use."""
    def __init__(self, lang, voice):
        import soundfile as sf
        self.ref = os.path.join(HERE, "narration", "voices", lang + ".wav")
        if not os.path.exists(self.ref):
            design = qwen_model("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
            wavs, sr = design.generate_voice_design(text=voice["reference"], instruct=voice["design"],
                                                    language=voice["language"])
            os.makedirs(os.path.dirname(self.ref), exist_ok=True)
            sf.write(self.ref, wavs[0], sr)
            print("designed the voice in", os.path.relpath(self.ref, HERE))
            del design
        self.model = qwen_model("Qwen/Qwen3-TTS-12Hz-1.7B-Base")
        self.prompt = self.model.create_voice_clone_prompt(ref_audio=self.ref, ref_text=voice["reference"])

    def speak(self, text, voice):
        wavs, sr = self.model.generate_voice_clone(text=text, language=voice["language"], voice_clone_prompt=self.prompt)
        return wavs[0], sr


class VoxCPM:
    """VoxCPM2 (Apache-2.0, 30 languages) with the voice of
    narration/voices/<language>.wav, designed on first use."""
    def __init__(self, lang, voice):
        import soundfile as sf
        from voxcpm import VoxCPM as Model
        self.model = Model.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
        self.sr = self.model.tts_model.sample_rate
        self.ref = os.path.join(HERE, "narration", "voices", lang + ".wav")
        if not os.path.exists(self.ref):
            wav = self.model.generate(text="(%s)%s" % (voice["design"], voice["reference"]))
            os.makedirs(os.path.dirname(self.ref), exist_ok=True)
            sf.write(self.ref, wav, self.sr)
            print("designed the voice in", os.path.relpath(self.ref, HERE))

    def speak(self, text, voice):
        return self.model.generate(text=text, prompt_wav_path=self.ref, prompt_text=voice["reference"]), self.sr


def engine(lang, voice):
    kind = voice["engine"]
    if kind == "kokoro":
        return Kokoro()
    if kind == "qwen-custom":
        return QwenCustom()
    if kind == "qwen-clone":
        return QwenClone(lang, voice)
    if kind == "voxcpm":
        return VoxCPM(lang, voice)
    raise SystemExit("unknown voice engine %r in narration/%s.json" % (kind, lang))


def trim(samples, sr, threshold=0.01, margin=0.08):
    """Cut the silence some voices leave before and after a sentence, so
    every pause between shots is GAP long."""
    import numpy as np
    loud = np.flatnonzero(np.abs(samples) > threshold)
    if not len(loud):
        return samples
    pad = int(margin * sr)
    return samples[max(0, loud[0] - pad):min(len(samples), loud[-1] + pad)]


def render(lang, video="first-turn"):
    import soundfile as sf
    import numpy as np
    narration = json.load(open(os.path.join(HERE, "narration", lang + ".json")))
    voice = narration["voice"]
    if video != "first-turn":
        # Another video in the same language: its own words, the same narrator
        narration = json.load(open(os.path.join(HERE, "narration", video, lang + ".json")))
    # The trailer shows screens of the first turn
    source = "first-turn" if video == "trailer" else video
    content = json.load(open(os.path.join(HERE, source + ".content.json")))
    screens = {s["id"]: s["screen"] for s in json.load(open(os.path.join(HERE, source + ".screens.json")))}
    segments = narration["segments"]
    tmp = tempfile.mkdtemp(prefix="conquer-video-")
    key = "found_steps" if video == "found-nation" else "steps"
    images = frames(narration["captions"], tutorial_steps(lang, content, key), screens, segments, tmp)

    tts = engine(lang, voice)
    audio, cues, t0, sr = [], [], 0.0, 24000
    for n, seg in enumerate(segments, 1):
        samples, sr = tts.speak(seg["text"], voice)
        samples = trim(np.asarray(samples, dtype=np.float32), sr)
        dur = len(samples) / sr + GAP
        audio.append(np.concatenate([samples, np.zeros(int(GAP * sr), dtype=np.float32)]))
        cues.append((t0, t0 + dur - GAP / 2, seg["text"], dur))
        t0 += dur
        print("  %s %d/%d: %.1f s" % (lang, n, len(segments), dur), flush=True)
    wav = os.path.join(tmp, "voice.wav")
    sf.write(wav, np.concatenate(audio), sr)

    concat = os.path.join(tmp, "frames.txt")
    with open(concat, "w") as f:
        for img, cue in zip(images, cues):
            f.write("file '%s'\nduration %.3f\n" % (img, cue[3]))
        f.write("file '%s'\n" % images[-1])
    out = os.path.join(WEB, "tutorial", "%s.%s.mp4" % (video, lang))
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat, "-i", wav,
                    "-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
                    "-tune", "stillimage", "-c:a", "aac", "-b:a", "96k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    with open(os.path.join(WEB, "tutorial", "%s.%s.vtt" % (video, lang)), "w") as f:
        f.write("WEBVTT\n\n")
        for n, (a, b, text, _) in enumerate(cues, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (n, vtt_time(a), vtt_time(b), text))
    shutil.rmtree(tmp)
    print("wrote %s (%.0f s)" % (out, t0))


def main():
    args, video = sys.argv[1:], "first-turn"
    if args[:1] == ["--video"]:
        video, args = args[1], args[2:]
    folder = os.path.join(HERE, "narration", *([] if video == "first-turn" else [video]))
    langs = args or sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(folder, "*.json")))
    for lang in langs:
        render(lang, video)


if __name__ == "__main__":
    main()
