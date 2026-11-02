#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Make the story video (web/story.html) in one language: 1920x1080 and
1080x1920 (vertical) H.264/AAC files.

  * The page is driven in Chromium with ?lang=<l>&render=1 (no narration,
    no sound: the driver advances the scenes) and recorded with Playwright.
  * Scene length = narration length + 1.2 s (at least 6 s).
  * The music is built with ffmpeg from web/sound/*.ogg following the cue
    mapping of the story (TL in web/story.js), beds crossfaded for 2.5 s,
    and put 12 dB under the narration (-16 LUFS); master -14 LUFS.
  * H.264 CRF 23, AAC 128k.

Writes web/story/conquer-story.<l>.mp4 and conquer-story.<l>.vertical.mp4.
Needs python playwright, Chrome (CHROMIUM=/path/to/chrome) and ffmpeg.

usage: render.py [--only landscape|vertical] LANGUAGE ...
"""
import functools
import http.server
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.abspath(os.path.join(HERE, "..", "..", "web"))
SOUND = os.path.join(WEB, "sound")
FFMPEG = os.environ.get("FFMPEG", shutil.which("ffmpeg") or "ffmpeg")
CHROMIUM = os.environ.get("CHROMIUM", "/usr/bin/google-chrome")
SIZES = {"": (1920, 1080), ".vertical": (1080, 1920)}
PAD, MINIMUM, XFADE = 1.2, 6.0, 2.5

# The story's cues as (scene, fraction of its narration, kind, name), in order.
# bed: the music bed that plays from there on; fx: an effect; off: silence.
CUES = [
    (1, 0.00, "bed", "report"),
    (2, 0.02, "fx", "news"), (2, 0.06, "bed", "app-home"),
    (3, 0.13, "bed", "map-human"), (3, 0.36, "bed", "map-elf"), (3, 0.59, "bed", "map-dwarf"), (3, 0.79, "bed", "map-orc"),
    (4, 0.02, "bed", "map-human"), (4, 0.04, "fx", "turn"),
    (5, 0.00, "off", ""),
    (6, 0.46, "fx", "app-doors-open"), (6, 0.56, "bed", "app-home"),
    (7, 0.00, "bed", "builder"), (7, 0.70, "fx", "found"),
    (8, 0.03, "fx", "turn"), (8, 0.14, "bed", "map-human"),
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=WEB))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d/" % server.server_address[1]


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def first_picture(path):
    """Seconds into the recording where the page first shows (it starts black)"""
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", path, "-vf", "blackdetect=d=0.04:pix_th=0.06", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"black_start:0(?:\.0+)?\s+black_end:([\d.]+)", out)
    return float(m.group(1)) if m else 0.0


def record(pw, base, lang, size, narr, starts, total, tmp):
    w, h = size
    browser = pw.chromium.launch(executable_path=CHROMIUM, args=["--no-proxy-server"])
    ctx = browser.new_context(viewport={"width": w, "height": h}, record_video_dir=tmp, record_video_size={"width": w, "height": h})
    t_page = time.monotonic()
    page = ctx.new_page()
    page.on("pageerror", lambda e: print("page error:", e))
    page.goto(base + "story.html?lang=%s&render=1&dur=%s" % (lang, ",".join("%.3f" % d for d in narr)))
    page.wait_for_function("() => window.conquerStory && document.fonts.status === 'loaded'")
    time.sleep(1.0)
    t0 = time.monotonic()
    page.evaluate("() => conquerStory.start()")
    for i in range(1, 8):
        time.sleep(max(0, t0 + starts[i] - time.monotonic()))
        page.evaluate("(k) => conquerStory.go(k)", i + 1)
    time.sleep(max(0, t0 + total - time.monotonic()))
    video = page.video
    ctx.close()
    path = video.path()
    browser.close()
    return path, t0 - t_page


def music(narr, starts, total, tmp):
    """The music track as a WAV: beds crossfaded by XFADE s, effects on top"""
    at = lambda scene, f: starts[scene - 1] + f * narr[scene - 1]
    beds, fx = [], []       # beds: [start, end, name]
    for scene, f, kind, name in CUES:
        t = at(scene, f)
        if kind == "fx":
            fx.append((t, name))
            continue
        if beds and beds[-1][1] is None:
            beds[-1][1] = t
        if kind == "bed":
            beds.append([t, None, name])
    if beds[-1][1] is None:
        beds[-1][1] = total
    cmd, parts, labels, idx = [FFMPEG, "-y", "-loglevel", "error"], [], [], 0
    for b, (s, e, name) in enumerate(beds):
        fade_in = 0.8 if b == 0 else XFADE
        last = b == len(beds) - 1
        end = min(total, e + (0 if last else XFADE))
        # a bed ends where the next one has faded in; the scene-5 silence is a bed ending without a successor
        length = end - s
        cmd += ["-stream_loop", "-1", "-i", os.path.join(SOUND, name + ".ogg")]
        out = XFADE if (not last or end >= total - 0.01) else XFADE
        parts.append("[%d:a]atrim=0:%.3f,asetpts=PTS-STARTPTS,aformat=sample_rates=44100:channel_layouts=stereo,"
                     "afade=t=in:d=%.2f,afade=t=out:st=%.3f:d=%.2f,adelay=%d|%d[b%d]"
                     % (idx, length, fade_in, max(0, length - out), out, int(s * 1000), int(s * 1000), idx))
        labels.append("[b%d]" % idx)
        idx += 1
    for t, name in fx:
        cmd += ["-i", os.path.join(SOUND, name + ".ogg")]
        parts.append("[%d:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay=%d|%d[b%d]" % (idx, int(t * 1000), int(t * 1000), idx))
        labels.append("[b%d]" % idx)
        idx += 1
    parts.append("%samix=inputs=%d:normalize=0,atrim=0:%.3f[m]" % ("".join(labels), len(labels), total))
    wav = os.path.join(tmp, "music.wav")
    subprocess.run(cmd + ["-filter_complex", ";".join(parts), "-map", "[m]", wav], check=True)
    return wav


def voice(lang, narr, starts, total, tmp):
    folder = os.path.join(WEB, "story", lang)
    cmd, parts = [FFMPEG, "-y", "-loglevel", "error"], []
    for i in range(8):
        cmd += ["-i", os.path.join(folder, "%d.mp3" % (i + 1))]
        ms = int(starts[i] * 1000)
        parts.append("[%d:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay=%d|%d[v%d]" % (i, ms, ms, i))
    parts.append("%samix=inputs=8:normalize=0,apad=whole_dur=%.3f,atrim=0:%.3f,loudnorm=I=-16:TP=-2:LRA=7[v]"
                 % ("".join("[v%d]" % i for i in range(8)), total, total))
    wav = os.path.join(tmp, "voice.wav")
    subprocess.run(cmd + ["-filter_complex", ";".join(parts), "-map", "[v]", "-ar", "44100", wav], check=True)
    return wav


def lufs(path):
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def render(pw, base, lang, suffix, size, cache):
    folder = os.path.join(WEB, "story", lang)
    narr = [probe(os.path.join(folder, "%d.mp3" % i)) for i in range(1, 9)]
    scene = [max(MINIMUM, n + PAD) for n in narr]
    starts = [sum(scene[:i]) for i in range(8)]
    total = sum(scene)
    tmp = tempfile.mkdtemp(prefix="conquer-story-")
    if "audio" not in cache:     # the sound is the same for both formats
        v = voice(lang, narr, starts, total, tmp)
        m = music(narr, starts, total, tmp)
        m2 = os.path.join(tmp, "music2.wav")      # 12 dB under the narration
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", m, "-af", "loudnorm=I=%.1f:TP=-3:LRA=11" % (lufs(v) - 12), m2], check=True)
        mix = os.path.join(tmp, "mix.wav")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", v, "-i", m2, "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1:LRA=9", mix], check=True)
        keep = os.path.join(tempfile.gettempdir(), "conquer-story-mix-%s.wav" % lang)
        shutil.copy(mix, keep)
        cache["audio"] = keep
        print("scene starts", ["%.1f" % s for s in starts], "total %.1f s; voice %.1f LUFS, music %.1f LUFS, master %.1f LUFS"
              % (total, lufs(v), lufs(m2), lufs(keep)))
    webm, lead = record(pw, base, lang, size, narr, starts, total, tmp)
    skip = first_picture(webm) + lead
    out = os.path.join(WEB, "story", "conquer-story.%s%s.mp4" % (lang, suffix))
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", "%.3f" % skip, "-t", "%.3f" % total, "-i", webm, "-i", cache["audio"],
                    "-vf", "fps=30,scale=%d:%d,format=yuv420p" % size, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out], check=True)
    shutil.rmtree(tmp)
    print("wrote %s (%.1f s, %.1f MB)" % (os.path.relpath(out), probe(out), os.path.getsize(out) / 1e6))


def main():
    args = sys.argv[1:]
    only = None
    if args[:1] == ["--only"]:
        only, args = args[1], args[2:]
    from playwright.sync_api import sync_playwright
    server, base = serve()
    with sync_playwright() as pw:
        for lang in args:
            cache = {}
            for suffix, size in SIZES.items():
                if only and (only == "vertical") != (suffix == ".vertical"):
                    continue
                render(pw, base, lang, suffix, size, cache)
    server.shutdown()


if __name__ == "__main__":
    main()
