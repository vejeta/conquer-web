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


def status_fixture(tmp_path, **fields):
    status = tmp_path / "status.json"
    status.write_text(json.dumps(dict({"turn": 3, "season": "Spring of Year 1", "news": [], "nations": []}, **fields)))
    return status


@pytest.mark.parametrize("fields,want,note", [
    ({"requests_open": True, "turn": 3, "last_join_turn": 5}, "ask for your seat", "invite code you are in at once"),
    ({"requests_open": True, "turn": 36, "last_join_turn": 5}, "ask for your seat", "The game is at turn 36"),
    ({"requests_open": False, "turn": 3, "last_join_turn": 5}, None, None),
    ({"signup": True, "turn": 3}, "ask for your seat", "invite code you are in at once"),
])
def test_home_asks_for_a_seat(site, browser, tmp_path, fields, want, note):
    """The home page offers one call to action, from status.json: the same
    for everyone, another line for latecomers, hidden when requests are closed."""
    Site.status_file = status_fixture(tmp_path, **fields)
    try:
        page = browser.new_page()
        page.goto(site + "index.html?lang=en")
        page.wait_for_function("() => document.getElementById('status-turn').textContent !== ''")
        hidden = page.evaluate("document.getElementById('join').hidden")
        if want is None:
            assert hidden
        else:
            assert not hidden
            assert want in page.inner_text("#join a")
            assert note in page.inner_text("#join-note")
            assert page.get_attribute("#join a", "href") == "signup.html"
        page.close()
    finally:
        Site.status_file = None


def fill_signup(page, **extra):
    page.fill("#account", "ana")
    page.fill("#password", "correct horse")
    page.fill("#password2", "correct horse")
    for field, value in extra.items():
        page.fill("#" + field, value)


@pytest.mark.parametrize("status", ["pending", "approved"])
def test_signup_done_panel(site, browser, status):
    """The reply's status picks the panel: a pending seat offers the practice
    world while waiting, an approved one (invite code) the first key."""
    seen = []

    def api(route):
        seen.append(json.loads(route.request.post_data))
        route.fulfill(content_type="application/json", body=json.dumps({"ok": True, "account": "ana", "status": status}))
    page = browser.new_page()
    page.route("**/join/api/request", api)
    page.goto(site + "signup.html?lang=en")
    fill_signup(page, email="ana@example.org", message="I found you on Usenet")
    if status == "approved":
        page.click("#invite summary")
        page.fill("#code", "k7qm-3xpa")
    page.click("#submit")
    if status == "pending":
        page.wait_for_selector("#done-pending:not([hidden])")
        assert page.evaluate("document.getElementById('done').hidden")
        assert page.get_attribute("#done-pending a[href='try/']", "href") == "try/"
        assert "ana@example.org" in page.inner_text("#pending-mail")
        assert "Your seat is pending" in page.inner_text("#done-pending")
        assert seen == [{"account": "ana", "password": "correct horse", "email": "ana@example.org",
                         "message": "I found you on Usenet", "lang": "en"}]
    else:
        page.wait_for_selector("#done:not([hidden])")
        assert page.evaluate("document.getElementById('done-pending').hidden")
        assert page.inner_text("#done-account") == "ana"
        assert seen[0]["code"] == "k7qm-3xpa"
    page.close()


def test_signup_without_email_or_code(site, browser):
    """Email and code are optional; a bad email is refused before asking."""
    seen = []

    def api(route):
        seen.append(json.loads(route.request.post_data))
        route.fulfill(content_type="application/json", body='{"ok": true, "account": "ana", "status": "pending"}')
    page = browser.new_page()
    page.route("**/join/api/request", api)
    page.goto(site + "signup.html?lang=en")
    fill_signup(page, email="not-an-address")
    page.click("#submit")
    assert "email address" in page.inner_text("#error") and not seen
    page.fill("#email", "")
    page.click("#submit")
    page.wait_for_selector("#done-pending:not([hidden])")
    assert seen == [{"account": "ana", "password": "correct horse", "lang": "en"}]
    assert "no email" in page.inner_text("#pending-mail")
    page.close()


@pytest.mark.parametrize("lang", ["es", "zh"])
def test_signup_sends_the_page_language(site, browser, lang):
    """The request says which language the page is shown in, for the mails."""
    seen = []

    def api(route):
        seen.append(json.loads(route.request.post_data))
        route.fulfill(content_type="application/json", body='{"ok": true, "account": "ana", "status": "pending"}')
    page = browser.new_page()
    page.route("**/join/api/request", api)
    page.goto(site + "signup.html?lang=" + lang)
    fill_signup(page)
    page.click("#submit")
    page.wait_for_selector("#done-pending:not([hidden])")
    assert seen[0]["lang"] == lang == page.evaluate("conquerI18n.lang()")
    page.close()


def test_signup_invite_link_opens_the_code(site, browser):
    page = browser.new_page()
    page.goto(site + "signup.html?lang=es&code=K7QM-3XPA")
    page.wait_for_function("() => document.title === 'Pide tu plaza'")
    assert page.evaluate("document.getElementById('invite').open")
    assert page.input_value("#code") == "K7QM-3XPA"
    page.close()


ADMIN_STATE = {
    "ok": True, "turn": 36, "last_join_turn": 5,
    "requests": [{"account": "ana", "since": 1, "email": "ana@example.org", "message": "Hello <b>there</b>"},
                 {"account": "bob", "since": 2, "email": "", "message": ""}],
    "players": [{"account": "ana", "state": "?", "nation": None}, {"account": "root", "state": "*", "nation": None},
                {"account": "cy", "state": "nation", "nation": "Gondor"}, {"account": "di", "state": "+", "nation": None}],
    "invites": ["K7QM-3XPA", "AAAA-BBBB"],
}


def test_admin_page(site, browser):
    """The three tabs show the state; Approve posts to the API and the page
    tells how to add the nation when the game is past the last joining turn."""
    posts = []
    state = json.loads(json.dumps(ADMIN_STATE))

    def api(route):
        req = route.request
        if req.method == "POST":
            posts.append((req.url.split("/admin/api/")[1], json.loads(req.post_data)))
            if req.url.endswith("/approve"):
                state["requests"] = state["requests"][1:]
                return route.fulfill(content_type="application/json", body='{"ok": true, "account": "ana", "emailed": true}')
            if req.url.endswith("/invite"):
                state["invites"].append("NEW1-CODE")
                return route.fulfill(content_type="application/json", body='{"ok": true, "codes": ["NEW1-CODE"]}')
        route.fulfill(content_type="application/json", body=json.dumps(state))
    page = browser.new_page()
    page.route("**/admin/api/**", api)
    page.goto(site + "admin.html?lang=en")
    page.wait_for_selector("#app:not([hidden])")
    rows = page.locator("#requests li")
    assert rows.count() == 2
    assert "ana@example.org" in rows.nth(0).inner_text()
    assert "Hello <b>there</b>" in rows.nth(0).inner_text()      # shown as text
    assert "no email" in rows.nth(1).inner_text()
    page.click("#tab-players")
    text = page.inner_text("#players")
    for want in ("plays: Gondor", "administrator", "approved, not founded yet", "requested"):
        assert want in text
    page.click("#tab-invites")
    assert page.locator("#invites li").count() == 2
    page.fill("#count", "3")
    page.click("#make")
    page.wait_for_function("() => document.querySelectorAll('#invites li').length === 3")
    assert ("invite", {"count": 3}) in posts
    page.click("#tab-requests")
    page.locator("#requests li").nth(0).locator("button.approve").click()
    page.wait_for_function("() => document.querySelectorAll('#requests li').length === 1")
    assert ("approve", {"account": "ana"}) in posts
    assert "approved" in page.inner_text("#info")
    note = page.inner_text("#notes")
    assert "turn 36" in note and "add-nation.sh" in note and "assign ana NATION" in note
    page.close()


def test_admin_reject_asks_first(site, browser):
    posts = []
    page = browser.new_page()

    def api(route):
        if route.request.method == "POST":
            posts.append(route.request.post_data)
            return route.fulfill(content_type="application/json", body='{"ok": true}')
        route.fulfill(content_type="application/json", body=json.dumps(ADMIN_STATE))
    page.route("**/admin/api/**", api)
    page.goto(site + "admin.html?lang=es")
    page.wait_for_selector("#app:not([hidden])")
    answers = iter([False, True])
    page.on("dialog", lambda d: d.accept() if next(answers) else d.dismiss())
    page.locator("#requests li").nth(0).locator("button.reject").click()
    page.wait_for_timeout(300)
    assert posts == []
    page.locator("#requests li").nth(0).locator("button.reject").click()
    page.wait_for_function("() => document.getElementById('info').textContent.includes('rechazado')")
    assert [json.loads(p) for p in posts] == [{"account": "ana"}]
    page.close()


@pytest.mark.parametrize("status", [401, 403])
def test_admin_needs_an_administrator(site, browser, status):
    page = browser.new_page()
    page.route("**/admin/api/**", lambda r: r.fulfill(status=status, content_type="application/json",
                                                      body='{"ok": false, "error": "forbidden"}'))
    page.goto(site + "admin.html?lang=en")
    page.wait_for_selector("#signin:not([hidden])")
    assert "administrator account" in page.inner_text("#signin")
    assert page.evaluate("document.getElementById('app').hidden")
    page.close()
