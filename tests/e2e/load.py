#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Load: K concurrent game sessions (default 30) through ttyd's WebSocket
behind Apache, each with its own form-login cookie. Every session opens its
practice world from the menu (a private copy of the template per account),
logs in to the game and keeps typing keys for a while (default 120 s).
Container memory and CPU are sampled with `docker stats`.

It reports numbers; it fails only when more than 5 % of the sessions had an
error or a timeout.

Usage (staging up, tests/e2e/.run.env sourced):
  python3 tests/e2e/load.py [--sessions 30] [--seconds 120]"""
import argparse
import asyncio
import json
import os
import random
import re
import ssl
import statistics
import subprocess
import sys
import threading
import time

import pyte
import requests
import websockets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2e_support import ROOT, Env  # noqa: E402

STATUS = re.compile(r"Conquer: [\d.]+\s+Turn\s+\d+")
KEYS = "hjklyubnhjklyubn p"        # moves of the cursor and "pick" (no q: the session stays in the game)


def host_root():
    return [] if os.geteuid() == 0 else ["sudo", "-n"]


def make_accounts(count, tag):
    """One account per session, each reading the same word (administrators open the menu's practice world)."""
    accounts = []
    for i in range(count):
        name, password = "load%s%02d" % (tag, i), "ld-%s-%02d-x" % (tag, i)
        run = subprocess.run(host_root() + ["./manage-players.sh", "add", name, "--admin", "--password-stdin"], cwd=ROOT,
                             input=password + "\n", capture_output=True, text=True)
        if run.returncode != 0:
            sys.exit("cannot create %s: %s%s" % (name, run.stdout[-300:], run.stderr[-300:]))
        accounts.append((name, password))
    return accounts


def drop_accounts(accounts):
    for name, _ in accounts:
        subprocess.run(host_root() + ["./manage-players.sh", "remove", name], cwd=ROOT, capture_output=True, text=True)


def login(name, password):
    s = requests.Session()
    s.verify = False
    r = s.post(Env.base + "/login/do", allow_redirects=False,
               data={"httpd_username": name, "httpd_password": password, "httpd_location": "/play/"}, timeout=30)
    cookie = s.cookies.get("conquer_session")
    if r.status_code != 302 or not cookie:
        raise RuntimeError("login of %s failed: %s" % (name, r.status_code))
    return cookie


class Sampler(threading.Thread):
    """docker stats for the game and Apache, every few seconds."""

    def __init__(self, names):
        super().__init__(daemon=True)
        self.names, self.rows, self.stop = names, [], threading.Event()

    @staticmethod
    def mib(text):
        m = re.match(r"([\d.]+)\s*([KMGkmg]i?)B", text.strip())
        if not m:
            return 0.0
        return float(m.group(1)) * {"K": 1 / 1024, "M": 1, "G": 1024}[m.group(2)[0].upper()]

    def run(self):
        while not self.stop.is_set():
            out = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{json .}}", *self.names], capture_output=True, text=True)
            for line in out.stdout.splitlines():
                try:
                    d = json.loads(line)
                    self.rows.append((d["Name"], float(d["CPUPerc"].rstrip("%")), self.mib(d["MemUsage"].split("/")[0]), int(d.get("PIDs") or 0)))
                except (ValueError, KeyError):
                    pass
            self.stop.wait(4)


async def session(idx, cookie, seconds, results, ctx):
    """One player: menu, practice game, keys until the time is up."""
    rec = {"idx": idx, "ok": False, "error": "", "to_map": None, "keys": 0, "bytes": 0}
    results.append(rec)
    screen = pyte.Screen(80, 24)
    stream = pyte.Stream(screen)
    t0 = time.time()
    url = Env.base.replace("https://", "wss://").replace("http://", "ws://") + "/play/ws?arg=en"
    headers = {"Cookie": "conquer_session=" + cookie, "Origin": Env.base}
    try:
        try:
            ws = await websockets.connect(url, subprotocols=["tty"], additional_headers=headers, ssl=ctx, max_size=None, open_timeout=30)
        except TypeError:
            ws = await websockets.connect(url, subprotocols=["tty"], extra_headers=headers, ssl=ctx, max_size=None, open_timeout=30)
        async with ws:
            await ws.send(json.dumps({"AuthToken": "", "columns": 80, "rows": 24}))

            async def pump(wait):
                """Read whatever arrives within `wait` seconds into the screen."""
                end = time.time() + wait
                while True:
                    left = end - time.time()
                    if left <= 0:
                        return True
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=left)
                    except asyncio.TimeoutError:
                        return True
                    data = msg if isinstance(msg, bytes) else msg.encode()
                    rec["bytes"] += len(data)
                    if data[:1] == b"0":
                        stream.feed(data[1:].decode("utf-8", "replace"))

            def text():
                return "\n".join(screen.display)

            async def send(s):
                await ws.send(b"0" + s.encode())

            async def wait_for(rx, timeout):
                end = time.time() + timeout
                while time.time() < end:
                    await pump(0.3)
                    if re.search(rx, text()):
                        return True
                return False

            if not await wait_for(r"q\)", 40):
                raise RuntimeError("no menu: %r" % text()[-300:])
            await send("7")                                  # the practice world
            if not await wait_for(r"(?i)practice", 30):
                raise RuntimeError("no practice menu: %r" % text()[-300:])
            await send("1")
            typed = False
            end = time.time() + 60
            while time.time() < end:
                await pump(0.3)
                t = text()
                if STATUS.search("\n".join(t.split("\n")[-6:])):
                    break
                if not typed and re.search(r"Nation's Password", t):
                    await send("train1\r")
                    typed = True
                elif typed and "PRESS ANY KEY" in t:
                    await send(" ")
            else:
                raise RuntimeError("no map: %r" % text()[-300:])
            rec["to_map"] = time.time() - t0
            stop = time.time() + seconds
            rng = random.Random(idx)
            while time.time() < stop:
                await send(rng.choice(KEYS))
                rec["keys"] += 1
                await pump(rng.uniform(0.3, 1.2))
            if not STATUS.search("\n".join(text().split("\n")[-6:])):
                # a key may have opened a prompt: the game still has to be answering
                await send("\x1b")
                if not await wait_for(r"Conquer: [\d.]+\s+Turn", 10):
                    raise RuntimeError("the game stopped answering: %r" % text()[-300:])
            await send("q")
            await pump(2)
            rec["ok"] = True
    except Exception as exc:                                  # noqa: BLE001
        rec["error"] = "%s: %s" % (type(exc).__name__, exc)


async def run(accounts, seconds):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    cookies = [login(n, p) for n, p in accounts]
    results = []
    tasks = []
    for i, cookie in enumerate(cookies):
        tasks.append(asyncio.create_task(session(i, cookie, seconds, results, ctx)))
        await asyncio.sleep(0.25)
    await asyncio.gather(*tasks)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=int(os.environ.get("E2E_LOAD_SESSIONS", "30")))
    ap.add_argument("--seconds", type=int, default=int(os.environ.get("E2E_LOAD_SECONDS", "120")))
    args = ap.parse_args()
    if not Env.base:
        sys.exit("E2E_BASE_URL is not set: source tests/e2e/.run.env")
    tag = "%x" % (int(time.time()) % 4096)
    accounts = make_accounts(args.sessions, tag)
    names = [Env.container, os.environ.get("E2E_APACHE", "apache-local")]
    sampler = Sampler(names)
    sampler.start()
    try:
        results = asyncio.run(run(accounts, args.seconds))
    finally:
        sampler.stop.set()
        sampler.join(timeout=15)
        drop_accounts(accounts)

    bad = [r for r in results if not r["ok"]]
    to_map = sorted(r["to_map"] for r in results if r["to_map"])
    print("\n%-22s %s" % ("sessions", "%d (%d seconds of keys each)" % (len(results), args.seconds)))
    print("%-22s %d (%.1f%%)" % ("errors or timeouts", len(bad), 100.0 * len(bad) / max(1, len(results))))
    if to_map:
        print("%-22s median %.1fs, slowest %.1fs" % ("time to the map", statistics.median(to_map), to_map[-1]))
    print("%-22s %d keys sent, %.1f MB received" % ("traffic", sum(r["keys"] for r in results), sum(r["bytes"] for r in results) / 1e6))
    print("\n%-14s %10s %10s %10s %10s %6s" % ("container", "cpu avg %", "cpu max %", "mem avg MiB", "mem max MiB", "pids"))
    for name in names:
        rows = [r for r in sampler.rows if r[0] == name]
        if rows:
            print("%-14s %10.1f %10.1f %10.0f %10.0f %6d" % (name, statistics.mean(r[1] for r in rows), max(r[1] for r in rows),
                                                              statistics.mean(r[2] for r in rows), max(r[2] for r in rows), max(r[3] for r in rows)))
    for r in bad[:10]:
        print("  session %d: %s" % (r["idx"], r["error"][:400]))
    if len(bad) > 0.05 * len(results):
        print("\nLOAD FAILED: more than 5% of the sessions failed")
        sys.exit(1)
    print("\nLOAD OK")


if __name__ == "__main__":
    main()
