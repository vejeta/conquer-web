"""Record a scripted Conquer session: an asciicast v2 file with chapter
markers, and the 80x24 screen (text + reverse/bold runs) after each step.

usage: cqrec.py STEPS.json OUT.cast OUT-screens.json
STEPS.json: {"cmd": "conquer -n x", "steps": [{"id","keys":[...],"caption","wait"}]}"""
import os, pty, time, select, sys, json, fcntl, termios, struct, subprocess
import pyte
spec = json.load(open(sys.argv[1])); cast_out, screens_out = sys.argv[2], sys.argv[3]
COLS, ROWS = 80, 24
pid, fd = pty.fork()
if pid == 0:
    os.execvp("docker", ["docker", "exec", "-it", "-u", "conquer", "-e", "TERM=xterm-256color",
                         "conquer-local", "bash", "-c", "stty rows 24 cols 80; cd /opt/conquer/lib; exec " + spec["cmd"]])
fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
screen = pyte.Screen(COLS, ROWS); stream = pyte.ByteStream(screen)
events = []; t0 = time.time(); clock = [0.0]
def now(): return round(time.time() - t0, 3)
def pump(t):
    end = time.time() + t
    while time.time() < end:
        if select.select([fd], [], [], 0.05)[0]:
            try: data = os.read(fd, 65536)
            except OSError: return
            if not data: return
            events.append([now(), "o", data.decode("utf-8", "replace")])
            stream.feed(data)
def snapshot():
    lines = []
    for y in range(ROWS):
        row = screen.buffer[y]; runs = []; cur = None
        for x in range(COLS):
            ch = row[x]; attr = (bool(ch.reverse), bool(ch.bold))
            if cur and cur[1] == attr: cur[0] += ch.data
            else:
                cur = [ch.data, attr]; runs.append(cur)
        lines.append([[t, int(a[0]) | (int(a[1]) << 1)] for t, a in runs])
    return lines
pump(float(spec.get("start_wait", 3)))
out = []
for st in spec["steps"]:
    if st.get("caption"): events.append([now(), "m", st["caption"]])
    for k in st.get("keys", []):
        pause = float(st.get("key_pause", 0.35))
        for ch in k.encode().decode("unicode_escape").encode("latin-1"):
            os.write(fd, bytes([ch])); pump(0.08)
        pump(pause)
    pump(float(st.get("wait", 1.8)))
    text = "\n".join(l.rstrip() for l in screen.display)
    for must in st.get("expect", []):
        if must not in text:
            print("STEP %s: expected %r not on screen:\n%s" % (st["id"], must, text), file=sys.stderr)
            sys.exit(1)
    out.append({"id": st["id"], "keys": st.get("keys", []), "screen": snapshot()})
    print("--- %s ---\n%s" % (st["id"], "\n".join(l for l in text.split("\n") if l.strip())))
with open(cast_out, "w") as f:
    f.write(json.dumps({"version": 2, "width": COLS, "height": ROWS, "timestamp": int(t0),
                        "env": {"TERM": "xterm-256color"}, "title": spec.get("title", "Conquer")}) + "\n")
    for e in events: f.write(json.dumps(e, ensure_ascii=False) + "\n")
json.dump(out, open(screens_out, "w"))
os.kill(pid, 9)
subprocess.run(["docker", "exec", "conquer-local", "sh", "-c",
    'for p in /proc/[0-9]*; do c=$(cat $p/comm 2>/dev/null); case "$c" in conquer|conqrun) kill -TERM ${p#/proc/};; esac; done; sleep 1'])
