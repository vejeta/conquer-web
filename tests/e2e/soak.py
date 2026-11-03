#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Game soak: bots play the game through `docker exec` and a pseudo terminal
(pexpect), no browser. Ten nations for N turns (default 25): each turn every
bot logs in to the terminal game, makes a few random moves (move an army,
draft, build, look at a report), quits; then the real turn update runs
(conquer-turn --now: backup, update, status).

Checked: no crash or core file, the world files are intact (the game's own
listing reads them), conquer-status and status.json are valid each turn, the
season can be closed at the end (season-end.sh) and a world backup restores
(restore-world.sh) to the same nations and the same turn.

Usage (staging up, tests/e2e/.run.env sourced):
  python3 tests/e2e/soak.py [--turns 25] [--nations 10] [--seed 1] [--no-restore]
Exit status 0: everything held."""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pexpect
import pyte
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2e_support import ROOT, Env, dexec, game_turn, nations, run_turn  # noqa: E402

COLS, ROWS = 80, 24
STATUS = re.compile(r"Conquer: [\d.]+\s+Turn\s+(\d+)")
RACES = ["H", "E", "D", "O", "H", "E", "D", "O", "H", "E", "D", "O"]
CLASSES = [["king"], ["wizard"], ["warlord"], ["pirate"], ["trader"], ["king"], ["pirate"], ["warlord"], ["priest"], ["trader"], ["emperor"], ["warlord"]]
ALIGN = ["G", "N", "E"]


class Screen:
    """A game session in a pseudo terminal, rendered with pyte."""

    def __init__(self, shell_cmd):
        self.screen = pyte.Screen(COLS, ROWS)
        self.stream = pyte.ByteStream(self.screen)
        self.child = pexpect.spawn("docker", ["exec", "-it", "-u", "conquer", "-e", "TERM=xterm-256color", Env.container,
                                              "bash", "-c", "stty rows %d cols %d; cd /opt/conquer/lib; exec %s" % (ROWS, COLS, shell_cmd)],
                                   dimensions=(ROWS, COLS), encoding=None, timeout=5)
        self.raw = b""

    def pump(self, seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            try:
                data = self.child.read_nonblocking(65536, timeout=0.05)
            except pexpect.TIMEOUT:
                continue
            except pexpect.EOF:
                return False
            self.raw += data
            self.stream.feed(data)
        return True

    def text(self):
        return "\n".join(l.rstrip() for l in self.screen.display).rstrip("\n")

    def send(self, keys, pause=0.12):
        for ch in keys:
            self.child.send(ch.encode("latin-1") if ord(ch) < 256 else ch.encode())
            self.pump(pause)

    def wait(self, pattern, timeout=30):
        rx = re.compile(pattern)
        end = time.time() + timeout
        while time.time() < end:
            self.pump(0.25)
            if rx.search(self.text()):
                return True
            if not self.child.isalive():
                return bool(rx.search(self.text()))
        return False

    def at_map(self):
        return bool(STATUS.search("\n".join(self.text().split("\n")[-6:])))

    def close(self):
        """Wait for the game to end; returns its exit status (None if it had to be killed)."""
        end = time.time() + 20
        while self.child.isalive() and time.time() < end:
            self.pump(0.3)
        if self.child.isalive():
            self.child.terminate(force=True)
            return None
        self.child.close()
        return self.child.exitstatus if self.child.exitstatus is not None else (128 + self.child.signalstatus if self.child.signalstatus else 0)


# ----------------------------------------------------------------- the nations
def found_nation(idx, name, password, flag):
    """The game's nation builder on a pseudo terminal: the same screens the
    journey drives in the browser."""
    race, klasses, align = RACES[idx % len(RACES)], CLASSES[idx % len(CLASSES)], ALIGN[idx % 3]
    s = Screen("conqrun %s -d /opt/conquer/lib" % flag)
    done = set()
    marks = 0
    end = time.time() + 240
    try:
        while time.time() < end:
            s.pump(0.3)
            text = s.text()
            step = None
            if "Added to the World" in text:
                s.send(" ")
                break
            elif "Save this nation" in text and "save" not in done:
                step = "save"; s.send("y")
            elif "Is the modification complete" in text and "complete" not in done:
                step = "complete"; s.send("y")
            elif "more civilians" in text and "civilians" not in done:
                step = "civilians"; s.send(" ")
            elif "remaining points for population" in text and "population" not in done:
                step = "population"; s.send("y")
            elif "Points Left:" in text and "DONE=ESC" in text and "points" not in done:
                step = "points"; s.send("j  "); s.pump(0.5); s.send("\x1b")
            elif "Enter National Mark" in text and marks < 8:
                if ("mark%d" % marks) not in done:
                    part = text.split("any of the following:", 1)[-1].split("Enter National Mark")[0]
                    letters = [c for c in re.findall(r"\S", part) if c.isalpha() and c.isupper()] or re.findall(r"\S", part)
                    step = "mark%d" % marks
                    s.send(letters[(idx * 3 + marks) % len(letters)])
                    marks += 1
            elif "Please Enter Alignment" in text and "alignment" not in done:
                step = "alignment"; s.send(align)
            elif "points added for starting late" in text and "late" not in done:
                step = "late"; s.send(" ")
            elif "Enter the number of your choice" in text and "class" not in done:
                step = "class"
                rows = re.findall(r"^\s*(\d+)\)\s+(\w+)\s+([A-Z]+)\s", text, re.M)
                mine = [(n, c) for n, c, r in rows if race in r]
                pick = next(((n, c) for want in klasses for n, c in mine if c == want), mine[0] if mine else rows[0][:2])
                s.send(pick[0] + "\r")
            elif "Enter your Race" in text and "race" not in done:
                step = "race"; s.send(race)
            elif "name of your country's leader" in text and "leader" not in done:
                step = "leader"; s.send("Bot%d\r" % idx)
            elif re.search(r"^Reenter National Password", text, re.M) and "password2" not in done:
                step = "password2"; s.send(password + "\r")
            elif re.search(r"^Enter National Password", text, re.M) and "password" not in done:
                step = "password"; s.send(password + "\r")
            elif "Enter a Name for your Country" in text and "name" not in done:
                step = "name"; s.send(name + "\r")
            elif "super user password" in text:
                raise AssertionError("the builder asks for god's password (flag %s):\n%s" % (flag, text))
            if step:
                done.add(step)
                before = text
                for _ in range(20):
                    s.pump(0.3)
                    if s.text() != before:
                        break
        else:
            raise AssertionError("builder did not finish (%s):\n%s" % (sorted(done), s.text()))
    finally:
        status = s.close()
    return status


# --------------------------------------------------------------------- the bots
def recover(s):
    for key in (" ", "\x1b", "n", "\r", " ", "\x1b"):
        if s.at_map():
            return True
        s.send(key)
        s.pump(0.5)
    return s.at_map()


ACTIONS = {
    "move": lambda rng: ["o", "o", "m", rng.choice("hjklyubn"), rng.choice("hjklyubn"), " "],
    "draft": lambda rng: ["X", "D", "I", "5\r", "y"],
    "build": lambda rng: ["X", "C", "f"],
    "look": lambda rng: [rng.choice("Bas"), " "],
    "walk": lambda rng: [rng.choice("hjklyubn") for _ in range(4)],
}


def play_turn(bot, rng):
    """One session of one bot. Returns (ok, notes, exit status)."""
    name, password = bot["name"], bot["password"]
    notes = []
    s = Screen("conquer -n %s" % name)
    try:
        if not s.wait(r"Nation's Password", 40):
            return False, ["no password prompt:\n" + s.text()], s.close()
        s.send(password + "\r")
        for _ in range(20):
            s.pump(0.4)
            if s.at_map():
                break
            if "PRESS ANY KEY" in s.text():
                s.send(" ")
        if not s.at_map():
            return False, ["no map after login:\n" + s.text()], s.close()
        for _ in range(rng.randint(2, 4)):
            kind = rng.choice(list(ACTIONS))
            for key in ACTIONS[kind](rng):
                s.send(key, 0.2)
                s.pump(0.2)
            if not recover(s):
                notes.append("stuck after %s:\n%s" % (kind, s.text()))
                s.send("\x1b\x1b")
        s.send("q")
        status = s.close()
        text = s.raw.decode("latin-1")
        if re.search(r"Segmentation|core dumped|Bus error|Aborted|Assertion", text):
            notes.append("crash text in the session")
        return status in (0, None) or status == 0, notes, status
    except Exception as exc:                       # noqa: BLE001
        return False, ["bot %s: %r" % (name, exc)], s.close()


# ---------------------------------------------------------------------- checks
def host_root():
    return [] if os.geteuid() == 0 else (["sudo", "-n"] if subprocess.run(["which", "sudo"], capture_output=True).returncode == 0 else [])


def check_world(expected_turn, bots, problems):
    turn = game_turn()
    if turn != expected_turn:
        problems.append("turn is %d, expected %d" % (turn, expected_turn))
    table = nations()                                      # conquer-status --nations: tab separated, 3 columns
    alive = [b["name"] for b in bots if b["name"] in table]
    out = dexec("sh", "-c", "find /opt/conquer/lib /tmp -maxdepth 2 -name 'core*' 2>/dev/null")
    if out.strip():
        problems.append("core files: %s" % out.strip())
    out = dexec("sh", "-c", "test -s /opt/conquer/lib/data && test -s /opt/conquer/lib/nations && echo ok")
    if out.strip() != "ok":
        problems.append("world files missing or empty")
    dexec("conquer-status")                                # publish status.json
    r = requests.get(Env.base + "/status/status.json", verify=False, timeout=20)
    try:
        status = r.json()
        if status.get("turn") != turn:
            problems.append("status.json says turn %s, the game %s" % (status.get("turn"), turn))
    except ValueError:
        problems.append("status.json is not valid JSON: %r" % r.text[:200])
    logs = subprocess.run(["docker", "logs", Env.container], capture_output=True, text=True)
    bad = re.findall(r"^.*(?:Segmentation|core dumped|panic:|Traceback).*$", logs.stdout + logs.stderr, re.M)
    if bad:
        problems.append("container log: %s" % bad[:3])
    return alive


def backup_and_restore(bots, problems):
    """sudo ./backup-world.sh, one more turn, then ./restore-world.sh: the world is as it was."""
    sudo = host_root()
    turn, table = game_turn(), nations()
    before = dexec("conquer-status", "--nations")
    out = subprocess.run(sudo + ["./backup-world.sh"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        problems.append("backup-world.sh failed: %s%s" % (out.stdout[-500:], out.stderr[-500:]))
        return
    found = subprocess.run(sudo + ["sh", "-c", "ls -t backups/world_backup_*.tar.gz | head -1"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not found:
        problems.append("no backup file made")
        return
    run_turn()                                             # the world moves on; the backup keeps this moment
    subprocess.run(["docker", "stop", Env.container], capture_output=True, check=True)
    restore = subprocess.run(sudo + ["./restore-world.sh", os.path.join(ROOT, found)], cwd=ROOT, input="y\n", capture_output=True, text=True)
    subprocess.run(["docker", "start", Env.container], capture_output=True, check=True)
    for _ in range(80):
        health = subprocess.run(["docker", "inspect", "-f", "{{.State.Health.Status}}", Env.container], capture_output=True, text=True).stdout.strip()
        if health == "healthy":
            break
        time.sleep(3)
    if restore.returncode != 0:
        problems.append("restore-world.sh failed: %s%s" % (restore.stdout[-500:], restore.stderr[-500:]))
        return
    if health != "healthy":
        problems.append("the game container is not healthy after the restore")
        return
    if game_turn() != turn:
        problems.append("after the restore the turn is %d, the backup was at %d" % (game_turn(), turn))
    after = dexec("conquer-status", "--nations")
    if after != before:
        problems.append("the nation list differs after the restore:\n%s\n---\n%s" % (before, after))
    if nations() != table:
        problems.append("the nations differ after the restore")
    run_turn()                                             # and the restored world still plays


def close_season(problems):
    name = "Soak %d" % int(time.time())
    out = subprocess.run(host_root() + ["./season-end.sh", name], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        problems.append("season-end.sh failed: %s%s" % (out.stdout[-400:], out.stderr[-400:]))
        return
    r = requests.get(Env.base + "/status/seasons/index.json", verify=False, timeout=20)
    if r.status_code != 200 or not any(s.get("name") == name for s in r.json()):
        problems.append("the closed season is not in the hall of fame index: %s %s" % (r.status_code, r.text[:200]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=int(os.environ.get("E2E_SOAK_TURNS", "25")))
    ap.add_argument("--nations", type=int, default=int(os.environ.get("E2E_SOAK_NATIONS", "10")))
    ap.add_argument("--seed", type=int, default=int(os.environ.get("E2E_SOAK_SEED", "1")))
    ap.add_argument("--no-restore", action="store_true")
    args = ap.parse_args()
    if not Env.base:
        sys.exit("E2E_BASE_URL is not set: source tests/e2e/.run.env")
    rng = random.Random(args.seed)
    problems, notes = [], []
    t0 = time.time()

    flag = "-a" if game_turn() <= 5 else "-A"
    bots = [{"name": "soak%d" % i, "password": "bot%02d" % i} for i in range(args.nations)]
    print("founding %d nations with conqrun %s" % (len(bots), flag), flush=True)
    for i, bot in enumerate(bots):
        status = found_nation(i, bot["name"], bot["password"], flag)
        if status not in (0, None):
            problems.append("conqrun for %s ended with status %s" % (bot["name"], status))
    present = [b["name"] for b in bots if b["name"] in nations()]
    if len(present) != len(bots):
        sys.exit("only %d of %d nations exist: %s" % (len(present), len(bots), present))

    failures = 0
    for n in range(args.turns):
        turn = game_turn()
        with ThreadPoolExecutor(max_workers=len(bots)) as pool:
            results = list(pool.map(lambda b: play_turn(b, random.Random(rng.random())), bots))
        for bot, (ok, extra, status) in zip(bots, results):
            if not ok:
                failures += 1
                notes.append("turn %d %s: exit %s %s" % (turn, bot["name"], status, "; ".join(extra)[:600]))
            if status in (134, 135, 139):
                problems.append("turn %d: %s crashed (exit %s)" % (turn, bot["name"], status))
            for e in extra:
                if "crash" in e:
                    problems.append("turn %d: %s: %s" % (turn, bot["name"], e))
        run_turn()
        alive = check_world(turn + 1, bots, problems)
        print("turn %d -> %d: %d/%d bots played, %d nations alive (%.0fs)" % (
            turn, turn + 1, sum(1 for r in results if r[0]), len(bots), len(alive), time.time() - t0), flush=True)
        if problems:
            break

    if not problems:
        close_season(problems)
        if not args.no_restore:
            backup_and_restore(bots, problems)
    rate = failures / float(max(1, args.turns * len(bots)))
    print("\nbot sessions that did not go through: %d (%.1f%%)" % (failures, 100 * rate))
    for note in notes[:15]:
        print("  note:", note)
    if rate > 0.2:
        problems.append("more than 20%% of the bot sessions failed (%.0f%%)" % (100 * rate))
    if problems:
        print("\nSOAK FAILED:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("SOAK OK: %d nations, %d turns, %.0fs" % (len(bots), args.turns, time.time() - t0))


if __name__ == "__main__":
    main()
