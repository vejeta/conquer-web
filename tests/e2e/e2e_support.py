# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared by the end-to-end rehearsal (journey, soak, load): the settings of
the run, the administrator's session, the mail catcher, the game container,
and a small driver for the game's terminal in the browser."""
import json
import os
import re
import subprocess
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "test-results" / "e2e"
WEB = ROOT / "web"


class Env:
    """Settings of the run, from the environment (tests/e2e/.run.env)."""

    base = os.environ.get("E2E_BASE_URL", "").rstrip("/")
    admin_user = os.environ.get("E2E_ADMIN_USER", "e2eadmin")
    admin_password = os.environ.get("E2E_ADMIN_PASSWORD", "")
    mailpit = os.environ.get("E2E_MAILPIT_URL", "").rstrip("/")
    container = os.environ.get("E2E_CONTAINER", "conquer-local")
    players = int(os.environ.get("E2E_PLAYERS", "6"))
    prefix = os.environ.get("E2E_PREFIX", "e2e")


def env_ok():
    return bool(Env.base and Env.admin_password)


def dexec(*args, user="conquer", check=True, input=None, timeout=300):
    """Run a command in the game container; returns stdout."""
    cmd = ["docker", "exec"]
    if input is not None:
        cmd.append("-i")
    if user:
        cmd += ["-u", user]
    cmd += [Env.container, *args]
    run = subprocess.run(cmd, capture_output=True, text=True, input=input, timeout=timeout)
    if check and run.returncode != 0:
        raise AssertionError("%s failed (%s): %s%s" % (" ".join(args), run.returncode, run.stdout[-1500:], run.stderr[-1500:]))
    return run.stdout


def game_turn(world=None):
    """The turn of the live world, from `conquer -s`."""
    cmd = ["conquer", "-s"] + (["-d", world] if world else [])
    out = dexec(*cmd)
    m = re.search(r"^Conquer .*, Turn (\d+)$", out, re.M)
    assert m, "no turn in: %s" % out[:300]
    return int(m.group(1))


def nations():
    """name -> (race, class) from conquer-status --nations (tab separated)."""
    out = dexec("conquer-status", "--nations")
    table = {}
    for line in out.splitlines():
        parts = line.split("\t")
        assert len(parts) == 3, "bad --nations line: %r" % line
        table[parts[0]] = (parts[1], parts[2])
    return table


def run_turn():
    """Force a turn update the way the smoke job does; returns the new turn."""
    before = game_turn()
    dexec("conquer-turn", "--now", timeout=600)
    after = game_turn()
    assert after == before + 1, "turn update: %d -> %d" % (before, after)
    return after


def season_text(turn):
    """What the game's newspaper prints for a turn: 'Summer of Year 1'."""
    return "%s of Year %d" % (["Winter", "Spring", "Summer", "Fall"][turn % 4], (turn + 3) // 4)


class Admin:
    """The administrator's session of the site (form login), and its API."""

    def __init__(self):
        self.s = requests.Session()
        self.s.verify = False
        r = self.s.post(Env.base + "/login/do", allow_redirects=False, data={
            "httpd_username": Env.admin_user, "httpd_password": Env.admin_password, "httpd_location": "/play/"})
        assert r.status_code == 302 and "conquer_session" in self.s.cookies, "administrator login failed (%s)" % r.status_code

    def api(self, name, **body):
        r = self.s.post(Env.base + "/admin/api/" + name, json=body, timeout=60)
        assert r.status_code == 200, "%s: %s %s" % (name, r.status_code, r.text[:300])
        return r.json()

    def state(self):
        r = self.s.get(Env.base + "/admin/api/state", timeout=60)
        assert r.status_code == 200, r.text[:300]
        return r.json()


class Mailpit:
    """The mail catcher's API."""

    def __init__(self):
        self.url = Env.mailpit

    def messages(self):
        r = requests.get(self.url + "/api/v1/messages", params={"limit": 500}, timeout=20)
        r.raise_for_status()
        return r.json()["messages"]

    def wait_for(self, to, subject_has=None, timeout=60):
        """The first message to an address (optionally with a word in the subject)."""
        end = time.time() + timeout
        while time.time() < end:
            for m in self.messages():
                if any(a["Address"].lower() == to.lower() for a in m["To"]) and (not subject_has or subject_has.lower() in m["Subject"].lower()):
                    full = requests.get("%s/api/v1/message/%s" % (self.url, m["ID"]), timeout=20)
                    full.raise_for_status()
                    return full.json()
            time.sleep(1)
        raise AssertionError("no mail to %s%s within %ds" % (to, " about '%s'" % subject_has if subject_has else "", timeout))


def i18n_text(lang, key):
    """A text of web/i18n/LANG.json by its last key, English if missing."""
    def find(node):
        if isinstance(node, dict):
            if key in node and isinstance(node[key], str):
                return node[key]
            for v in node.values():
                got = find(v)
                if got:
                    return got
        return None
    for code in (lang, "en"):
        got = find(json.loads((WEB / "i18n" / ("%s.json" % code)).read_text(encoding="utf-8")))
        if got:
            return got
    raise KeyError(key)


# JavaScript run in the terminal's frame (ttyd exposes xterm.js as window.term)
READ_SCREEN = """() => {
    const t = window.term, b = t.buffer.active, lines = [];
    for (let y = 0; y < t.rows; y++) {
        const l = b.getLine(b.viewportY + y);
        lines.push(l ? l.translateToString(true) : '');
    }
    return { lines: lines, cx: b.cursorX, cy: b.cursorY };
}"""


class Term:
    """The game's terminal in the page (game.html: an iframe with ttyd).
    The screen is read through the xterm buffer, as the touch layer does;
    keys go in by the keyboard or by the touch layer's chips."""

    def __init__(self, page):
        self.page = page

    @property
    def frame(self):
        return next(f for f in self.page.frames if "/play" in f.url)

    def attach(self, timeout=60):
        self.page.wait_for_function(
            "() => { try { return !!document.getElementById('game').contentWindow.term } catch (e) { return false } }",
            timeout=timeout * 1000)
        self.page.wait_for_function("() => !!window.touchLayer", timeout=timeout * 1000)

    def read(self):
        try:
            return self.frame.evaluate(READ_SCREEN)
        except Exception:
            return {"lines": [], "cx": 0, "cy": 0}

    def text(self):
        return "\n".join(l.rstrip() for l in self.read()["lines"]).rstrip("\n")

    def where(self):
        try:
            return self.page.evaluate("window.touchLayer ? touchLayer.where() : ''")
        except Exception:
            return ""

    def wait(self, pattern, timeout=30, flags=0):
        """Wait for a regex (or a callable on the screen's text) to show."""
        test = pattern if callable(pattern) else (lambda t, rx=re.compile(pattern, flags): rx.search(t))
        end = time.time() + timeout
        text = ""
        while time.time() < end:
            text = self.text()
            if test(text):
                return text
            time.sleep(0.25)
        raise AssertionError("not on the terminal screen within %ds: %r\n%s" % (timeout, getattr(pattern, "pattern", pattern) if not callable(pattern) else "callable", text))

    def wait_where(self, where, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            if self.where() == where:
                return self.text()
            time.sleep(0.25)
        raise AssertionError("the touch layer never said %r (it says %r):\n%s" % (where, self.where(), self.text()))

    def wait_change(self, before, timeout=8):
        """Wait until the screen is not `before` any more (True), or time runs out (False)."""
        end = time.time() + timeout
        while time.time() < end:
            if self.text() != before:
                return True
            time.sleep(0.2)
        return False

    def focus(self):
        try:
            self.frame.focus("textarea.xterm-helper-textarea", timeout=5000)
        except Exception:
            self.page.evaluate("() => { try { document.getElementById('game').contentWindow.term.focus() } catch (e) {} }")

    def type(self, text, delay=40):
        """Type with the keyboard (printable characters)."""
        self.focus()
        self.page.keyboard.type(text, delay=delay)

    def press(self, key):
        self.focus()
        self.page.keyboard.press(key)

    def send(self, data):
        """Raw input as the touch layer sends it (control keys)."""
        self.frame.evaluate("d => window.term.input(d, true)", data)

    def chip(self, chip_id, timeout=8000):
        """Tap a chip of the touch layer's bar by its id (data-chip)."""
        loc = self.page.locator('[data-chip="%s"]:visible' % chip_id).first
        try:
            loc.click(timeout=timeout)
        except Exception:
            loc.dispatch_event("click")

    def has_chip(self, chip_id):
        return self.page.locator('[data-chip="%s"]:visible' % chip_id).count() > 0


def dump(text, title="screen"):
    return "---- %s ----\n%s\n----" % (title, text)
