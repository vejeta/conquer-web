# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The game page replays the nation builder recording in Chromium: the
coach follows it and the phone key bar switches to the builder's keys.
The sign-up page offers the builder video.

Needs the Python playwright module and Chromium (python3 -m playwright
install chromium, or CHROMIUM=/path/to/chrome)."""
import functools
import http.server
import json
import os
import threading

import pytest

from conftest import ROOT, WEB, load, recorded_screens, steps_file

pytestmark = pytest.mark.browser
playwright = pytest.importorskip("playwright.sync_api")


def site_policy():
    """The Content Security Policy the VPS sends (vps/virtualhost.conf.template)"""
    for line in (ROOT / "vps" / "virtualhost.conf.template").read_text().splitlines():
        if "Content-Security-Policy" in line:
            return line.split('"')[1]
    raise AssertionError("no Content-Security-Policy in the virtual host template")


class Site(http.server.SimpleHTTPRequestHandler):
    """web/, with the stand-in for ttyd at /play/, and the VPS's security policy"""

    def end_headers(self):
        self.send_header("Content-Security-Policy", site_policy())
        super().end_headers()

    status_file = None   # a fixture for status/status.json, when a test sets one

    def translate_path(self, path):
        if self.status_file and path.split("?")[0] == "/status/status.json":
            return str(self.status_file)
        if path.split("?")[0].rstrip("/") == "/play":
            return str(ROOT / "tests" / "fake" / "play.html")
        return super().translate_path(path)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def site():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Site, directory=str(WEB)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d/" % server.server_address[1]
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None, args=["--no-proxy-server"])
        yield b
        b.close()


def coach_state(page):
    return page.evaluate("""() => ({
        open: !document.getElementById('coach').hidden,
        title: document.getElementById('coach-title').innerText,
        builderKeys: !document.getElementById('builder-keys').hidden,
    })""")


@pytest.mark.parametrize("lang,phone", [("en", False), ("es", True)])
def test_coach_follows_the_builder(site, browser, lang, phone):
    ctx = browser.new_context(viewport={"width": 390, "height": 844} if phone else {"width": 1280, "height": 800},
                              has_touch=phone, is_mobile=phone)
    page = ctx.new_page()
    page.goto(site + "game.html?lang=" + lang)
    page.wait_for_function("() => { try { return document.getElementById('game').contentWindow.ready } catch (e) { return false } }")
    game = next(f for f in page.frames if "/play" in f.url)
    titles = {s["id"]: s["title"] for s in load(steps_file("builder", lang))["steps"]}
    screens = recorded_screens("found-nation")
    # The recording: the builder's first screen, then one chapter per step
    game.evaluate("playTo(2)")
    for n, (sid, _) in enumerate(screens):
        if n:
            game.evaluate("playTo(1)")
        want = titles["points" if sid == "treasury" else sid]
        # The coach opens by itself the first time the builder shows, at
        # the step on screen, and the key bar shows the builder's keys
        expect = {"open": True, "title": want, "builderKeys": True}
        try:
            page.wait_for_function("""want => {
                const c = document.getElementById('coach'), k = document.getElementById('builder-keys');
                return !c.hidden && !k.hidden && document.getElementById('coach-title').innerText === want;
            }""", arg=want, timeout=5000)
        except playwright.TimeoutError:
            pass
        assert coach_state(page) == expect, sid
    # A builder key on the bar reaches the game (on a computer the bar
    # starts folded)
    if not phone:
        page.click("#toggle")
    page.locator("#builder-keys button[data-key='j']").click()
    assert game.evaluate("sent") == "j"
    ctx.close()


@pytest.mark.parametrize("lang", ["es", "de"])
def test_signup_offers_the_builder_video(site, browser, lang):
    video = WEB / "tutorial" / ("found-nation.%s.mp4" % lang)
    english = WEB / "tutorial" / "found-nation.en.mp4"
    page = browser.new_page()
    page.route("**/join/api/**", lambda r: r.abort())
    page.goto(site + "signup.html?lang=" + lang)
    page.wait_for_timeout(1500)
    src = page.evaluate("document.getElementById('howto-video').getAttribute('src')")
    hidden = page.evaluate("document.getElementById('howto').hidden")
    if video.exists():
        assert src == "tutorial/found-nation.%s.mp4" % lang and not hidden
    elif english.exists():
        assert src == "tutorial/found-nation.en.mp4" and not hidden
    else:
        assert hidden
    page.close()


def test_resizing_keeps_the_game_screen(site, browser):
    """Turning a phone, or the coach and key bar changing size, refits the
    terminal without ever making it smaller than 80x24: text the game draws
    meanwhile is not cut."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    page = ctx.new_page()
    page.goto(site + "game.html")
    page.wait_for_function("() => { try { return document.getElementById('game').contentWindow.ready } catch (e) { return false } }")
    game = next(f for f in page.frames if "/play" in f.url)
    game.evaluate("playTo(10)")    # the points screen
    page.wait_for_timeout(1500)
    sizes = []
    game.evaluate("window.sizes = []; term.onResize(e => sizes.push([e.cols, e.rows]))")
    for viewport in ({"width": 844, "height": 390}, {"width": 390, "height": 844}):
        page.set_viewport_size(viewport)
        page.wait_for_timeout(1200)
        page.click("#coach-toggle") if page.locator("#coach-toggle").count() else None
        page.wait_for_timeout(800)
    sizes = game.evaluate("sizes")
    assert all(c >= 80 and r >= 24 for c, r in sizes), sizes
    ctx.close()


def test_arrow_keys_move(site, browser):
    """The game knows only y k u / h l / b j n: arrows are sent as those."""
    page = browser.new_page()
    page.goto(site + "game.html")
    page.wait_for_function("() => { try { return document.getElementById('game').contentWindow.ready } catch (e) { return false } }")
    game = next(f for f in page.frames if "/play" in f.url)
    page.wait_for_timeout(1000)
    game.click("#t")
    for key in ("ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "PageUp", "End", "PageDown", "x"):
        page.keyboard.press(key)
    assert game.evaluate("sent") == "kjhlyubnx"
    page.close()


def test_practice_game_runs(site, browser):
    """/try/ runs the game in WebAssembly under the site's security policy,
    and moves with the arrow keys."""
    page = browser.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site + "try/")
    page.wait_for_timeout(1500)
    page.click("#terminal")
    page.keyboard.press(" ")
    page.wait_for_function("() => window.term && [...Array(24).keys()].some(y => "
                           "(term.buffer.active.getLine(y) || {translateToString: () => ''}).translateToString().includes('Password'))",
                           timeout=20000)
    assert not [e for e in errors if "Content Security Policy" in e or "CompileError" in e], errors
    page.close()


def test_movement_figure(site, browser):
    """The home page draws how to move; /try/ opens it the first time a
    game starts, and only then."""
    page = browser.new_page()
    page.goto(site + "index.html?lang=es")
    page.wait_for_function("() => document.querySelectorAll('[data-moves] .mv-k.on').length === 16")
    assert "Cómo te mueves" in page.inner_text("[data-moves]")
    page.goto(site + "try/")
    page.wait_for_timeout(1000)
    page.click("#terminal")
    page.keyboard.press(" ")
    page.wait_for_selector("#moves-panel:not([hidden])", timeout=5000)
    page.click("#moves-ok")
    assert page.evaluate("document.getElementById('moves-panel').hidden")
    page.reload()
    page.wait_for_timeout(1000)
    page.click("#terminal")
    page.keyboard.press(" ")
    page.wait_for_timeout(1500)
    assert page.evaluate("document.getElementById('moves-panel').hidden")
    page.close()


def test_schedule_in_visitor_time(site, browser, tmp_path):
    """A schedule worked out from cron shows in the visitor's language and
    local time: 20:00 in Madrid is 14:00 in New York."""
    status = tmp_path / "status.json"
    status.write_text(json.dumps({
        "turn": 4, "season": "Winter of Year 1", "schedule": "Daily at 20:00 (Europe/Madrid)",
        "schedule_auto": True, "repeat": "daily", "tz": "Europe/Madrid",
        "next_turn": 1790877600, "ready": None, "signup": True, "news": [], "nations": []}))
    Site.status_file = status
    try:
        ctx = browser.new_context(timezone_id="America/New_York", locale="es-ES")
        page = ctx.new_page()
        page.goto(site + "index.html?lang=es")
        page.wait_for_function("() => /cada día/.test(document.getElementById('status-schedule').textContent)")
        assert page.inner_text("#status-schedule") == "cada día a las 14:00, en tu hora"
        ctx.close()
    finally:
        Site.status_file = None
