# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The whole player journey, with several players at once, on the real stack
(real Apache, form login, the gate, ttyd and the game; see tests/e2e/README.md).

N players (E2E_PLAYERS, default 6) each run in their own thread and browser
context, with phone and desktop profiles and es/en/de pages:

  a. ask for a seat on the join page; the administrator approves through the
     admin API; the player reads the approval mail in the mail catcher
  b. log in through the Doors form
  c. found a nation in the game's builder (distinct races and classes; the
     2-7 characters hint of the nation password), by the touch layer's chips
     and by keyboard; the screen is read through the xterm buffer
  d. on the map: tap-to-move, d-pad and keys, reports (parchment), a message to
     another player's nation, end the session
  e. a turn update is forced; every player logs in again: the news tell the
     turn, the message arrived, the nation's numbers changed
  f. late join after turn 5 (the builder's -A) for one more player
  g. logout; the session cookie is gone

Every step asserts. On failure a trace, a video and a screenshot are kept under
test-results/e2e/."""
import os
import re
import secrets
import shutil
import threading
import time
import traceback
from urllib.parse import urlparse

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
pytest.importorskip("requests")

from e2e_support import (RESULTS, Admin, Env, Mailpit, Term, dexec, dump, env_ok, game_turn,  # noqa: E402
                         i18n_text, nations, run_turn, season_text)

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(not env_ok(), reason="no staging: tests/e2e/up.sh, then source tests/e2e/.run.env")]

# One row per player: race letter, class names to look for (first one on offer),
# alignment (orcs are always evil: no question), page language, device
SPECS = [
    dict(race="H", race_name="Human", klass=["king"], align="G", lang="es", profile="pixel7"),
    dict(race="E", race_name="Elf", klass=["wizard"], align="N", lang="en", profile="desktop"),
    dict(race="D", race_name="Dwarf", klass=["warlord"], align="E", lang="de", profile="iphone13"),
    dict(race="O", race_name="Orc", klass=["pirate"], align=None, lang="en", profile="pixel7"),
    dict(race="H", race_name="Human", klass=["trader"], align="G", lang="de", profile="desktop"),
    dict(race="E", race_name="Elf", klass=["trader"], align="G", lang="es", profile="iphone13"),
    dict(race="D", race_name="Dwarf", klass=["pirate"], align="N", lang="en", profile="desktop"),
    dict(race="O", race_name="Orc", klass=["warlord"], align=None, lang="de", profile="pixel7"),
]
LOCALES = {"es": "es-ES", "en": "en-US", "de": "de-DE"}
APPROVED_WORD = {"es": "aprobada", "en": "approved", "de": "freigegeben"}
DEVICES = {"pixel7": "Pixel 7", "iphone13": "iPhone 13"}
# Console messages that are not the page's fault
# ttyd 1.7.7 (and its main branch) may close the socket with 1006, a code that must never be
# sent, when the menu ends: it reads the exit code before it is known (-1, so "not 0") when the
# pty's end comes before the process's. The menu exits 0; the player sees nothing.
TTYD_1006 = "Received a broken close frame containing a reserved status code"


def benign(text):
    return "favicon" in text or ("/play/ws?arg=" in text and TTYD_1006 in text)

BUILDER_CHIP = {"y": "byes", "n": "bno", " ": "bbuy", "\r": "benter", "\x1b": "besc", "j": "bdown", "k": "bup"}


class Ctl:
    """What the players share: barriers, and the first error of each."""

    def __init__(self, n):
        self.n = n
        self.founded = threading.Barrier(n)       # every nation exists before anyone writes to another
        self.played = threading.Barrier(n + 1)    # first sessions over: the turn update runs (n players + the test)
        self.updated = threading.Barrier(n + 1)   # turn update over
        self.errors = {}
        self.lock = threading.Lock()

    def abort(self):
        for b in (self.founded, self.played, self.updated):
            b.abort()


class Player:
    def __init__(self, idx, ctl, run_id, late=False):
        self.idx, self.ctl, self.late = idx, ctl, late
        self.spec = SPECS[idx % len(SPECS)]
        self.lang = self.spec["lang"]
        self.account = "%s-%s%d" % (Env.prefix, run_id, idx)
        self.run_id = run_id
        self.nation = self.nation_of(idx)
        self.password = secrets.token_hex(6)
        self.nation_pw = ["ab", "tide", "x7k9q", "rune123", "dwarf", "gold42"][idx % 6]
        if Env.mailpit:
            self.email = "%s@e2e.test" % self.account
        elif Env.mail_to:
            user, _, domain = Env.mail_to.partition("@")
            self.email = "%s+%s@%s" % (user, self.account, domain)
        else:
            self.email = ""
        self.dir = RESULTS / self.account
        self.soft = []                  # failures that do not stop the journey
        self.console, self.bad = [], []
        self.saw_late = False
        self.treasury = None
        self.turn = None
        self.sector = None
        self.page = self.term = self.ctx = None

    # ---------------------------------------------------------------- helpers
    def nation_of(self, idx):
        return ("%s%s%d" % (Env.prefix, self.run_id[:3], idx))[:9]

    def name(self):
        return "%s(%s/%s/%s)" % (self.account, self.spec["race_name"], self.lang, self.spec["profile"])

    def check(self, cond, message):
        if not cond:
            self.soft.append(message)

    def use_chips(self):
        return self.idx % 2 == 0

    def key(self, k):
        """One key of the builder: a chip of the touch layer or the keyboard."""
        if self.use_chips() and k in BUILDER_CHIP and self.term.has_chip(BUILDER_CHIP[k]):
            self.term.chip(BUILDER_CHIP[k])
        elif k == "\r":
            self.term.press("Enter")
        elif k == "\x1b":
            self.term.press("Escape")
        else:
            self.term.type(k)

    def context_args(self, pw):
        args = dict(ignore_https_errors=True, locale=LOCALES[self.lang], record_video_dir=str(self.dir / "video"))
        if self.spec["profile"] == "desktop":
            args["viewport"] = {"width": 1280, "height": 800}
            args["record_video_size"] = {"width": 1280, "height": 800}
        else:
            dev = dict(pw.devices[DEVICES[self.spec["profile"]]])
            dev.pop("default_browser_type", None)
            args.update(dev)
        return args

    def watch(self, page):
        page.on("console", lambda m: self.console.append(m.text) if m.type == "error" and not benign(m.text) else None)
        page.on("pageerror", lambda e: self.console.append("pageerror: %s" % e))
        page.on("response", lambda r: self.bad.append("%s %s" % (r.status, r.url)) if r.status >= 400 and "favicon" not in r.url else None)

    # ------------------------------------------------------------------ steps
    def ask_for_a_seat(self):
        page = self.page
        page.goto("%s/signup.html?lang=%s" % (Env.base, self.lang))
        page.fill("#account", self.account)
        page.fill("#password", self.password)
        page.fill("#password2", self.password)
        if self.email:
            page.fill("#email", self.email)
        page.fill("#message", "rehearsal %s" % self.name())
        page.click("#submit")
        page.wait_for_selector("#done-pending:not([hidden])", timeout=30000)
        marks = dexec("cat", "/opt/conquer/lib/.players")
        assert re.search(r"^%s:\?$" % re.escape(self.account), marks, re.M), "no pending mark for %s:\n%s" % (self.account, marks)

    def approve_and_read_the_mail(self):
        admin = Admin()
        state = admin.state()
        assert any(r["account"] == self.account for r in state["requests"]), "request not listed in the admin state"
        out = admin.api("approve", account=self.account)
        assert out.get("ok"), out
        assert re.search(r"^%s:\+$" % re.escape(self.account), dexec("cat", "/opt/conquer/lib/.players"), re.M)
        link = Env.base + "/"
        if not self.email:
            return link
        if Env.mailpit:
            assert out.get("emailed") is True, "approval was not mailed: %s" % out
            mail = Mailpit()
            note = mail.wait_for("admin@e2e.test", subject_has=self.account)
            assert self.account in note["Text"] and "/admin/" in note["Text"], "mail to the administrator: %s" % note["Text"][:200]
            msg = mail.wait_for(self.email, subject_has=APPROVED_WORD[self.lang])
            body = msg["Text"]
            assert self.account in body, "the approval mail does not name the account:\n%s" % body
            urls = re.findall(r"https?://[^\s<>\"]+", body)
            assert urls, "no link in the approval mail:\n%s" % body
            if self.late:
                assert str(self.turn_at_join) in body, "late approval mail does not say the turn:\n%s" % body
            link = Env.base + (urlparse(urls[0]).path or "/")
        return link

    def sign_in(self, first):
        """The Doors form: login.html posts to /login/do."""
        page = self.page
        if first:
            page.wait_for_url(lambda url: urlparse(url).path.endswith("/login.html"), timeout=30000)
        else:
            page.goto("%s/login.html?lang=%s&next=/game.html" % (Env.base, self.lang))
        page.wait_for_selector("#account")
        if first and self.idx == 0:
            page.fill("#account", self.account)
            page.fill("#password", "wrong-" + self.password)
            page.click("#go")
            page.wait_for_selector("#failed:not([hidden])", timeout=15000)
        page.fill("#account", self.account)
        page.fill("#password", self.password)
        page.click("#go")
        # the path, not the whole URL: the login page itself says next=/game.html
        page.wait_for_url(lambda url: urlparse(url).path.endswith("/game.html"), timeout=30000)
        cookies = [c for c in self.ctx.cookies() if c["name"] == "conquer_session"]
        assert cookies, "no session cookie after the login"
        assert cookies[0]["httpOnly"] and cookies[0]["secure"], cookies[0]
        self.term = Term(page)
        self.term.attach()

    def sound_check(self):
        page = self.page
        try:
            page.click("#touch-gear", timeout=8000)
        except Exception:
            page.locator("#touch-gear").dispatch_event("click")
        page.check("#touch-opt-music")
        page.check("#touch-opt-effects")
        page.wait_for_function("() => conquerAudio._state() === 'running'", timeout=20000)
        page.wait_for_function("() => conquerAudio._loaded().length >= 13", timeout=40000)
        assert page.evaluate("conquerAudio._failed()") == [], "sound files that did not load"
        if not self.use_chips():
            page.uncheck("#touch-opt-music")
            page.uncheck("#touch-opt-effects")
            assert page.evaluate("conquerAudio.enabled()") is False
        page.keyboard.press("Escape")

    # the nation builder ---------------------------------------------------
    def class_number(self, text):
        rows = re.findall(r"^\s*(\d+)\)\s+(\w+)\s+([A-Z]+)\s", text, re.M)
        assert rows, "no class list:\n%s" % text
        mine = [(n, c) for n, c, races in rows if self.spec["race"] in races]
        for want in self.spec["klass"]:
            for n, c in mine:
                if c == want:
                    return n, c
        return mine[0] if mine else rows[0][:2]

    def pick_mark(self, text, tried):
        part = text.split("any of the following:", 1)[-1].split("Enter National Mark")[0]
        letters = [c for c in re.findall(r"\S", part) if c.isalpha() and c.isupper()] or re.findall(r"\S", part)
        assert letters, "no marks to choose from:\n%s" % text
        return letters[(self.idx * 3 + tried) % len(letters)]

    def builder(self):
        t = self.term
        done, tried_mark = set(), 0
        t.wait(r"Nation Builder", timeout=420)           # one builder at a time: the others wait their turn
        end = time.time() + 300
        while time.time() < end:
            text = t.text()
            step = None
            if "Added to the World" in text:
                self.key(" ")
                return
            elif "Save this nation" in text and "save" not in done:
                step = "save"; self.key("y")
            elif "Is the modification complete" in text and "complete" not in done:
                step = "complete"; self.key("y")
            elif "more civilians" in text and "civilians" not in done:
                step = "civilians"; self.key(" ")
            elif "remaining points for population" in text and "population" not in done:
                step = "population"; self.key("y")
            elif "Points Left:" in text and "points" not in done and "DONE=ESC" in text:
                step = "points"; self.buy_treasury(text); self.key("\x1b")
            elif "Enter National Mark" in text and tried_mark < 6:
                step = "mark%d" % tried_mark
                if step not in done:
                    t.type(self.pick_mark(text, tried_mark))
                    tried_mark += 1
            elif "Please Enter Alignment" in text and "alignment" not in done and self.spec["align"]:
                step = "alignment"; t.type(self.spec["align"])
            elif "points added for starting late" in text and "late" not in done:
                step = "late"; self.saw_late = True; self.key(" ")
            elif "Enter the number of your choice" in text and "class" not in done:
                step = "class"
                num, self.klass = self.class_number(text)
                t.type(num)
                self.key("\r")
            elif "Enter your Race" in text and "race" not in done:
                step = "race"; t.type(self.spec["race"])
            elif "name of your country's leader" in text and "leader" not in done:
                step = "leader"; t.type("Ruler%d" % self.idx); self.key("\r")
            elif re.search(r"^Reenter National Password", text, re.M) and "password2" not in done:
                step = "password2"; self.check_hint(); t.type(self.nation_pw); self.key("\r")
            elif re.search(r"^Enter National Password", text, re.M) and "password" not in done:
                step = "password"; self.password_step()
            elif "Enter a Name for your Country" in text and "name" not in done:
                step = "name"; t.type(self.nation); self.key("\r")
            if step is None:
                time.sleep(0.3)
                continue
            done.add(step)
            t.wait_change(text, 6)
        raise AssertionError("the builder did not finish (%s):\n%s" % (sorted(done), t.text()))

    def check_hint(self):
        """The 2-7 characters hint of the touch layer at the nation password."""
        page = self.page
        page.wait_for_function("() => !document.getElementById('touch-fieldhint').hidden", timeout=8000)
        shown = page.inner_text("#touch-fieldhint").strip()
        assert shown == i18n_text(self.lang, "hint_password"), "hint at the password prompt: %r" % shown
        if self.lang == "en":
            assert shown == "2–7 characters"

    def password_step(self):
        t = self.term
        self.check_hint()
        if self.idx == 0:
            t.type("a")                      # too short: the game says so and asks again
            self.key("\r")
            t.wait(r"Password Too Short", timeout=10)
            t.type(" ")
            t.wait(r"Enter National Password", timeout=10)
        elif self.idx == 1:
            t.type("abcdefghij")             # too long
            self.key("\r")
            t.wait(r"Password Too Long", timeout=10)
            t.type(" ")
            t.wait(r"Enter National Password", timeout=10)
        t.type(self.nation_pw)
        self.key("\r")

    def buy_treasury(self, text):
        before = int(re.search(r"Points Left:\s*(\d+)", text).group(1))
        self.key("j")
        self.key(" ")
        self.key(" ")
        self.term.wait(lambda s: re.search(r"Points Left:\s*%d\b" % (before - 2), s), timeout=15)

    def found_the_nation(self):
        t = self.term
        # the explanation of the nation builder, then any key
        t.wait(lambda s: len(s.strip()) > 40, timeout=90)
        time.sleep(1.5)
        if "Nation Builder" not in t.text():
            if self.use_chips() and t.has_chip("enter"):
                t.chip("enter")
            else:
                t.press("Enter")
        self.builder()
        # "Your nation was founded": any key, then the menu
        t.wait(lambda s: "Nation Builder" not in s and len(s.strip()) > 10, timeout=60)
        time.sleep(1)
        t.press("Enter")
        t.wait_where("menu", timeout=60)
        players = dexec("cat", "/opt/conquer/lib/.players")
        assert re.search(r"^%s:%s$" % (re.escape(self.account), re.escape(self.nation)), players, re.M), \
            "the account is not linked to its nation:\n%s" % players
        table = nations()
        assert self.nation in table, "%s is not in the world: %s" % (self.nation, sorted(table))
        race, klass = table[self.nation]
        assert race.lower().startswith(self.spec["race_name"].lower()[:3]), "race in the world: %s (wanted %s)" % (race, self.spec["race_name"])
        assert klass.lower().startswith(self.klass.lower()[:4]), "class in the world: %s (wanted %s)" % (klass, self.klass)

    # the game ---------------------------------------------------------------
    def enter_game(self):
        t = self.term
        t.wait_where("menu", timeout=60)
        if self.use_chips():
            t.chip("m1")
        else:
            t.type("1")
        typed, end = False, time.time() + 90
        while time.time() < end:
            text = t.text()
            if t.where() == "map" and re.search(r"Conquer: [\d.]+\s+Turn\s+\d+", text):
                break
            if not typed and re.search(r"Nation's Password", text):
                t.type(self.nation_pw)
                t.press("Enter")
                typed = True
            elif typed and (t.where() == "anykey" or "PRESS ANY KEY" in text):
                t.type(" ")
            elif not typed and re.search(r"\b\d+x\d+\b", text) and "Password" not in text:
                t.type("c")                 # "your terminal is too small": go on
            else:
                time.sleep(0.3)
                continue
            t.wait_change(text, 6)
        else:
            raise AssertionError("the map never showed:\n%s" % t.text())
        self.read_status()

    def read_status(self):
        text = self.term.text()
        m = re.search(r"Conquer: [\d.]+\s+Turn\s+(\d+)", text)
        self.turn = int(m.group(1)) if m else None
        m = re.search(r"treasury\.+(-?\d+)", text)
        self.treasury = int(m.group(1)) if m else None
        # the last panel on the screen (a wide terminal resized under the game shows the old one too,
        # until the layer's ^L redraw: keys_and_dpad checks that it comes)
        ms = re.findall(r"x is\s+(\d+)\s+y is\s+(\d+)", text)
        self.sector = (int(ms[-1][0]), int(ms[-1][1])) if ms else None
        return text

    def wait_sector_change(self, before, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            self.read_status()
            if self.sector and self.sector != before:
                return self.sector
            time.sleep(0.3)
        return self.sector

    def tap_to_move(self):
        page, t = self.page, self.term
        t.wait_where("map")
        time.sleep(1.5 if self.spec["profile"] != "desktop" else 0.5)    # a phone's view settles on the cursor
        self.read_status()
        before = self.sector
        assert before, "no sector coordinates on the map:\n%s" % t.text()
        cur = t.read()
        sx = 1 if cur["cx"] < 40 else -1
        sy = 1 if cur["cy"] < 10 else -1
        col, row = cur["cx"] + 4 * sx, cur["cy"] + 2 * sy
        x, y = page.evaluate("""([c, r]) => {
            const g = document.querySelector('.touch-grid').getBoundingClientRect();
            const t = document.getElementById('game').contentWindow.term;
            return [g.left + (c + 0.5) * g.width / t.cols, g.top + (r + 0.5) * g.height / t.rows];
        }""", [col, row])
        inside = page.evaluate("""([x, y]) => { const v = document.getElementById('touch-viewport').getBoundingClientRect();
            return x > v.left && x < v.right && y > v.top && y < v.bottom; }""", [x, y])
        if not inside:
            assert self.spec["profile"] != "desktop", "the tap point is outside the terminal on a desktop"
            return False                    # zoomed in on a phone: that cell is off the screen
        if self.spec["profile"] == "desktop":
            page.mouse.click(x, y)
        else:
            page.touchscreen.tap(x, y)
            page.wait_for_timeout(400)      # a phone waits for a possible double tap
        after = self.wait_sector_change(before)
        assert after != before, "tap-to-move did not move the cursor (still %s):\n%s" % (before, t.text())
        assert (after[0] - before[0]) * sx > 0 and (after[1] - before[1]) * sy > 0, "tap moved the wrong way: %s -> %s (wanted %+d,%+d)" % (before, after, sx, sy)
        return True

    def cursor(self):
        c = self.term.read()
        return (c["cx"], c["cy"])

    def settle_cursor(self, still=1.5, timeout=15):
        """The terminal's cursor, once it has not moved for a while (a refit redraws the map)."""
        end, last, since = time.time() + timeout, None, time.time()
        while time.time() < end:
            cur = self.cursor()
            if cur != last:
                last, since = cur, time.time()
            elif time.time() - since >= still:
                return cur
            time.sleep(0.2)
        return last

    def wait_cursor_change(self, before, timeout=6):
        end = time.time() + timeout
        while time.time() < end:
            cur = self.cursor()
            if cur != before:
                return self.settle_cursor(still=0.8)     # the game draws the panel after the cursor
            time.sleep(0.2)
        return before

    def keys_and_dpad(self):
        # The cursor of the terminal is the sector: the game shows no panel on a sector the nation
        # has not seen, and stale panels of a wide screen are not a reliable sign.
        page, t = self.page, self.term
        if page.evaluate("document.querySelector('.touch-dpad').hidden"):
            t.chip("move")
        page.wait_for_selector(".touch-dpad:not([hidden])", timeout=8000)
        before = self.settle_cursor()
        dirs = [("j", "ArrowDown"), ("k", "ArrowUp"), ("l", "ArrowRight"), ("h", "ArrowLeft")]
        opposite = {"j": "k", "k": "j", "l": "h", "h": "l"}
        arrow = dict(dirs)
        tried, after = [], None
        for key, _ in dirs:
            page.click(".touch-pb[data-key='%s']" % key)       # the d-pad: one sector that way
            after = self.wait_cursor_change(before)
            tried.append("%s: %s" % (key, after))
            if after != before:
                break
        else:
            raise AssertionError("the d-pad moved the cursor in no direction from %s (%s):\n%s" % (before, tried, t.text()))
        back = opposite[key]
        t.press(arrow[back])                                     # the keyboard: arrows move as h j k l
        again = self.wait_cursor_change(after)
        assert again == before, "arrow %s: %s -> %s (wanted %s)" % (arrow[back], after, again, before)
        t.type(key)                                              # the letter itself
        last = self.wait_cursor_change(again)
        assert last == after, "key %s: %s -> %s (wanted %s)" % (key, again, last, after)
        # the pad showed and the terminal was refitted: the layer redraws the game (^L), so no old panel is left
        t.wait(lambda s: len(re.findall(r"x is\s+\d+\s+y is\s+\d+", s)) <= 1, timeout=10)
        if not page.evaluate("document.querySelector('.touch-dpad').hidden") and t.has_chip("move"):
            t.chip("move")                                   # the Move chip hides it again

    def report(self, chip, expect):
        t = self.term
        t.chip(chip)
        t.wait(expect, timeout=15)
        t.wait_where("report", timeout=10)
        self.check(self.page.evaluate("document.getElementById('stone').classList.contains('parchment')"),
                   "%s: the report is not on parchment" % chip)
        self.page.wait_for_selector("#touch-back", state="visible", timeout=8000)
        assert self.page.locator("#touch-back:visible").count() == 1, "no Back button on the %s report" % chip
        self.page.click("#touch-back")
        t.wait_where("map", timeout=15)

    def send_message(self, to_nation):
        t = self.term
        t.type("W")
        t.wait(r"Send mail to what nation", timeout=15)
        t.type(to_nation)
        t.press("Enter")
        t.wait(r"Message to Nation", timeout=15)
        t.type("hello from %s" % self.nation)
        t.press("Enter")
        t.wait(r"hello from", timeout=10)
        t.send("\x04")                                        # Control-D on a new line ends the message
        t.wait_where("map", timeout=20)

    def end_session(self):
        t = self.term
        t.chip("quit")
        t.wait(r"\[[a-z]/N\]", timeout=30)                    # "Are your orders done? [y/N]" in the page's language
        text = t.text()
        # a touch player must be able to answer: the Yes chip, in every language
        self.check(t.where() == "prompt_yn" and t.has_chip("yes"), "no Yes/No chips at the orders question in %s: where=%s\n%s" % (self.lang, t.where(), text))
        if t.has_chip("yes"):
            t.chip("yes")
        else:
            t.type("y")
        t.wait(r"(?i)any key|tecla|taste|touche|klawisz", timeout=20)
        t.press("Enter")
        t.wait_where("menu", timeout=30)
        t.type("q")                                          # Log out of the menu
        time.sleep(1.5)

    def sign_out(self):
        page = self.page
        try:
            page.click("#logout", timeout=5000)
        except Exception:
            page.evaluate("document.getElementById('logout').click()")
        page.wait_for_url(re.compile(r"/login\.html\?loggedout=1"), timeout=20000)
        # the logout empties the session and the cookie lives one more second (SessionMaxAge 1)
        end = time.time() + 10
        while time.time() < end and [c for c in self.ctx.cookies() if c["name"] == "conquer_session"]:
            time.sleep(0.5)
        assert not [c for c in self.ctx.cookies() if c["name"] == "conquer_session"], "the session cookie is still there after signing out"
        r = self.ctx.request.get(Env.base + "/play/", max_redirects=0)
        assert r.status == 302, "/play/ after signing out answers %s" % r.status

    # ---------------------------------------------------------------- journeys
    def first_day(self):
        self.ask_for_a_seat()
        link = self.approve_and_read_the_mail()
        self.page.goto(link)
        self.page.locator('a.key-primary[href*="game.html"]').first.click()      # Play now: the Doors open
        self.sign_in(first=True)
        self.sound_check()
        self.found_the_nation()

    def play_first_turn(self, target):
        self.enter_game()
        self.tap_to_move()
        self.keys_and_dpad()
        self.report("budget", r"NEXT SEASON'S BUDGET")
        self.report("army", r"ARMY STATS SUMMARY")
        self.send_message(target)
        self.read_status()
        self.end_session()

    def run(self):
        with playwright_api.sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-proxy-server"])
            self.dir.mkdir(parents=True, exist_ok=True)
            self.ctx = browser.new_context(**self.context_args(pw))
            self.ctx.add_init_script("try { localStorage.setItem('conquer-lang', %r) } catch (e) {}" % self.lang)
            self.ctx.set_default_timeout(30000)
            self.ctx.tracing.start(screenshots=True, snapshots=True)
            self.page = self.ctx.new_page()
            self.watch(self.page)
            failed = False
            try:
                self.journey()
            except BaseException as exc:           # noqa: BLE001: keep the first error of this player
                failed = True
                self.ctl.abort()
                with self.ctl.lock:
                    self.ctl.errors[self.name()] = "".join(traceback.format_exception(exc))[-4000:]
                try:
                    self.page.screenshot(path=str(self.dir / "failure.png"))
                    (self.dir / "screen.txt").write_text(self.term.text() if self.term else "")
                except Exception:
                    pass
            finally:
                try:
                    self.ctx.tracing.stop(path=str(self.dir / "trace.zip") if (failed or self.soft) else None)
                    self.ctx.close()
                    browser.close()
                except Exception:
                    pass
            if not failed and not self.soft:
                shutil.rmtree(self.dir, ignore_errors=True)

    def journey(self):
        if self.late:
            self.turn_at_join = game_turn()
            self.first_day()
            assert self.saw_late, "past turn 5 the builder did not say it adds points for starting late"
            self.late_session()
            self.sign_out()
            self.finish_checks()
            return
        n = self.ctl.n
        target = self.nation_of((self.idx + 1) % n)
        self.first_day()
        self.ctl.founded.wait(timeout=900)
        self.play_first_turn(target)
        self.sign_out()
        # the turn update runs now
        before_treasury, before_turn = self.treasury, self.turn
        self.ctl.played.wait(timeout=900)
        self.ctl.updated.wait(timeout=900)
        self.sign_in_again()
        self.enter_game()
        assert self.turn == before_turn + 1, "turn after the update: %s (was %s)" % (self.turn, before_turn)
        self.check(self.treasury != before_treasury, "the treasury did not change over the turn: %s" % self.treasury)
        self.read_news(before_turn)
        sender = self.nation_of((self.idx - 1) % n)
        self.read_mail(sender)
        self.second_end()
        self.sign_out()
        self.finish_checks()

    def sign_in_again(self):
        self.sign_in(first=False)

    def read_news(self, old_turn):
        t = self.term
        t.type("N")
        t.wait(r"Read Which Newspaper", timeout=15)
        t.type("1")
        t.wait(r"CONQUER NEWS REPORT", timeout=15)
        text = t.text()
        assert season_text(old_turn) in text, "the newspaper does not mention %s:\n%s" % (season_text(old_turn), text)
        self.page.click("#touch-back")
        t.wait_where("map", timeout=15)

    def read_mail(self, sender):
        t = self.term
        t.type("R")
        found = False
        marker = r"Message from|HIT ANY KEY|HIT RETURN TO DELETE"
        t.wait(marker, timeout=20)
        for _ in range(40):                       # page by page; Space keeps the message
            text = t.text()
            if sender in text:
                found = True
            if not re.search(marker, text):
                break
            t.type(" ")
            t.wait_change(text, 6)
        assert found, "the message from %s never arrived" % sender
        t.wait_where("map", timeout=20)

    def second_end(self):
        t = self.term
        t.chip("quit")
        t.wait(r"\[[a-z]/N\]", timeout=30)
        t.type("n")
        t.wait_where("menu", timeout=30)
        t.type("q")
        time.sleep(1.5)

    def late_session(self):
        self.enter_game()
        self.tap_to_move()
        self.report("budget", r"NEXT SEASON'S BUDGET")
        self.end_session()

    def finish_checks(self):
        assert not self.console, "console errors:\n" + "\n".join(self.console[:10])
        assert not self.bad, "failed requests:\n" + "\n".join(self.bad[:10])
        assert not self.soft, "checks that failed:\n" + "\n\n".join(self.soft)


def test_journey():
    n = max(1, min(Env.players, 30))
    run_id = secrets.token_hex(2)
    ctl = Ctl(n)
    RESULTS.mkdir(parents=True, exist_ok=True)
    players = [Player(i, ctl, run_id) for i in range(n)]
    threads = [threading.Thread(target=p.run, name=p.account, daemon=True) for p in players]
    for th in threads:
        th.start()
    problems = []
    try:
        ctl.played.wait(timeout=1500)          # everyone finished the first session
        turn = run_turn()                       # forced, as the smoke job does
        assert turn >= 2
        ctl.updated.wait(timeout=60)
    except Exception as exc:                    # noqa: BLE001
        ctl.abort()
        problems.append("test thread: %r" % exc)
    for th in threads:
        th.join(timeout=900)
    # late join: the world gets past turn 5, then one more player asks for a seat
    if not ctl.errors and not problems:
        late = Player(n, ctl, run_id, late=True)
        try:
            while game_turn() <= 5:
                run_turn()
            late.run()
        except Exception as exc:                # noqa: BLE001
            problems.append("late player: %r" % exc)
    errors = dict(ctl.errors)
    if errors or problems:
        report = "\n\n".join("== %s\n%s" % (k, v) for k, v in errors.items()) + "\n" + "\n".join(problems)
        pytest.fail("the journey failed (artifacts in %s):\n%s" % (RESULTS, report), pytrace=False)
