# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The game page replays the nation builder recording in Chromium: the
coach follows it and the touch bar switches to the builder's keys.
The touch layer (web/touch.js) is checked on /try/ and on the game page:
the screen classifier, the grid over the terminal, tap to move, the chips,
the options. The sign-up page offers the builder video.

Needs the Python playwright module and Chromium (python3 -m playwright
install chromium, or CHROMIUM=/path/to/chrome)."""
import functools
import http.server
import json
import os
import re
import time
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
    # A builder key on the bar reaches the game
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
        page.evaluate("document.getElementById('site-header').click()")    # sideways, the header folds away: a tap shows it
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
    ({"requests_open": True, "turn": 36, "last_join_turn": 5}, "ask for your seat", "The game is at turn 36: a nation founded now starts late, with extra points"),
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
    "nations": [{"name": "Gondor", "race": "Human", "class": "Warrior", "account": "cy"},
                {"name": "Fung", "race": "Dwarf", "class": "Merchant", "account": None},
                {"name": "Anorian", "race": "Elf", "class": "Mage", "account": None}],
}


def test_admin_page(site, browser):
    """The three tabs show the state; Approve posts to the API and the page
    shows no note about adding the nation by hand, even when the game is past
    the last turn of the early start: approval is the only gate."""
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
    body = page.inner_text("body")
    assert "add-nation.sh" not in body and "assign ana" not in body
    assert page.locator("#notes").count() == 0
    page.close()


def test_admin_assigns_nations(site, browser):
    """Each account has a select with the world's nations (with race), "found a
    new nation" and "administrator"; Assign posts the choice; the nations
    without an account are listed."""
    posts = []
    page = browser.new_page()

    def api(route):
        if route.request.method == "POST":
            posts.append((route.request.url.split("/admin/api/")[1], json.loads(route.request.post_data)))
            return route.fulfill(content_type="application/json", body='{"ok": true, "assigned": "Fung"}')
        route.fulfill(content_type="application/json", body=json.dumps(ADMIN_STATE))
    page.route("**/admin/api/**", api)
    page.goto(site + "admin.html?lang=en")
    page.wait_for_selector("#app:not([hidden])")
    page.click("#tab-players")
    rows = page.locator("#players tr")
    assert rows.count() == 4
    options = rows.nth(0).locator("select option").all_inner_texts()
    assert "Fung (Dwarf)" in options and "Found a new nation" in options and "Administrator" in options
    assert rows.nth(2).locator("select").input_value() == "n:Gondor"
    free = page.inner_text("#free-nations")
    assert "Fung" in free and "Anorian" in free and "Gondor" not in free
    page.locator("#players tr").nth(0).locator("select").select_option("n:Fung")
    page.locator("#players tr").nth(0).locator("button.assign").click()
    page.wait_for_function("() => document.getElementById('info').textContent.includes('opens Fung')")
    page.locator("#players tr").nth(3).locator("select").select_option("+")
    page.locator("#players tr").nth(3).locator("button.assign").click()
    page.locator("#players tr").nth(1).locator("select").select_option("*")
    page.locator("#players tr").nth(1).locator("button.assign").click()
    page.wait_for_function("() => document.getElementById('info').textContent.includes('administrator')")
    assert posts == [("assign", {"account": "ana", "nation": "Fung"}),
                     ("assign", {"account": "di", "found": True}),
                     ("assign", {"account": "root", "admin": True})]
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


# ---------------------------------------------------------------------------
# The touch layer (web/touch.js) over the terminal, on /try/ and game.html

SHOTS = os.environ.get("TOUCH_SHOTS")     # a folder: the screenshot test writes there
FIRST_TURN = dict(recorded_screens("first-turn"))
VIEWPORTS = {"phone": {"width": 390, "height": 844}, "landscape": {"width": 844, "height": 390},
             "desktop": {"width": 1280, "height": 800}}

# What the classifier says of every recorded screen (touch.js: classify)
EXPECTED_FIRST_TURN = {
    "menu": "menu", "password": "prompt_text", "title": "anykey", "map": "map", "mail": "report", "mail2": "report",
    "budget": "report", "armies": "report", "select": "map", "move": "move", "moved": "map", "draft": "prompt_yn",
    "drafted": "map", "diplomacy": "report", "quit": "prompt_yn", "done": "anykey", "newturn": "menu",
}


def touch_page(site, browser, where, viewport="desktop", lang=None, errors=None, touch=None, query="", init=None):
    """/try/ (the terminal is window.term) or game.html (it is in the frame of the
    stand-in for ttyd). Returns (context, page, target), target being where
    `term` lives: the page or the frame."""
    size = VIEWPORTS[viewport]
    touch = viewport != "desktop" if touch is None else touch
    ctx = browser.new_context(viewport=size, has_touch=touch, is_mobile=touch)
    if init:
        ctx.add_init_script(init)
    page = ctx.new_page()
    page.route("**/favicon.ico", lambda r: r.fulfill(status=204))
    if errors is not None:
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
    url = site + ("try/" if where == "try" else "game.html") + ("?lang=" + lang if lang else "")
    if query:
        url += ("&" if lang else "?") + query
    page.goto(url)
    if where == "try":
        page.wait_for_function("() => window.touchLayer && window.term")
        # before the game runs the layer shows the title's one chip: let it read the screen
        page.evaluate("touchLayer.setMode(null)")
        target = page
    else:
        page.wait_for_function("() => { try { return document.getElementById('game').contentWindow.ready } catch (e) { return false } }")
        target = next(f for f in page.frames if "/play" in f.url)
        page.wait_for_function("() => window.touchLayer")
    page.wait_for_timeout(300)
    return ctx, page, target


def show(page, target, text, cursor=None):
    """Write a recorded screen into the terminal and put the cursor: at the end
    of the last line, or at (x, y)."""
    lines = [l.rstrip() for l in text.split("\n")]
    if cursor is None:
        n = len(lines)
        while n and not lines[n - 1]:
            n -= 1
        cursor = (len(lines[n - 1]), n - 1)
    target.evaluate("""([t, c]) => { term.reset(); return new Promise(r => term.write(t, () => {
        term.write('\\x1b[' + (c[1] + 1) + ';' + (c[0] + 1) + 'H', r); })); }""", ["\r\n".join(lines), list(cursor)])


def wait_where(page, where):
    page.wait_for_function("w => touchLayer.where() === w", arg=where, timeout=5000)


def bar(page):
    """The labels of the chips on the bar, and where the badge says we are."""
    return page.evaluate("""() => ({
        where: document.getElementById('touch-where').textContent,
        back: !document.getElementById('touch-back').hidden,
        chips: [...document.querySelectorAll('#touch-chips:not([hidden]) .touch-chip, #builder-keys:not([hidden]) .touch-chip')]
            .map(b => (b.querySelector('.lb') || {}).textContent || b.getAttribute('aria-label')),
    })""")


def test_classifier_knows_every_recorded_screen(site, browser):
    """The screen classifier (touch.js) against the recorded screens of the
    tutorials: what the game shows is told apart by its own text."""
    page = browser.new_page()
    page.goto(site + "try/")
    page.wait_for_function("() => window.conquerTouch")
    screens = recorded_screens("first-turn")
    assert {sid for sid, _ in screens} == set(EXPECTED_FIRST_TURN), "a recorded screen has no expected class"
    for sid, text in screens:
        lines = [l.rstrip() for l in text.split("\n")]
        n = len(lines)
        while n and not lines[n - 1]:
            n -= 1
        cursor = {"x": len(lines[n - 1]), "y": n - 1}
        got = page.evaluate("([l, c]) => conquerTouch.whereAmI(l, c)", [lines, cursor])
        assert got == EXPECTED_FIRST_TURN[sid], sid
    for name in ("found-nation", "found-nation-late"):
        for sid, text in recorded_screens(name):
            assert page.evaluate("l => conquerTouch.whereAmI(l)", text.split("\n")) == "builder", (name, sid)
    page.close()


@pytest.mark.parametrize("text,want", [
    ("Enter the amount:\n\nhow many Infantry do you wish to raise:", "prompt_number"),
    ("Jump to what X location? ", "prompt_number"),
    ("Is the modification complete? (y or n)", "prompt_yn"),
    ("Disband your Infantry army 3?", "prompt_yn"),
    ("  Are your orders for this turn done? [y/N] ", "prompt_yn"),
    ("  ¿Has terminado tus órdenes de este turno? [s/N] ", "prompt_yn"),
    ("  Suas ordens deste turno estão prontas? [s/N] ", "prompt_yn"),
    ("  Hast du deine Befehle für diesen Zug fertig? [j/N] ", "prompt_yn"),
    ("  Czy rozkazy na ten ruch są gotowe? [t/N] ", "prompt_yn"),
    ("Send mail to what nation? ", "prompt_text"),
    ("Pay him off? (y or n)\nHIT ANY KEY", "anykey"),
    ("", "unknown"),
    ("\n".join(["  1) Play", "  2) How to join", "  q) Log out", "", "  Choose an option: "]), "menu"),
])
def test_classifier_prompts(site, browser, text, want):
    page = browser.new_page()
    page.goto(site + "try/")
    page.wait_for_function("() => window.conquerTouch")
    lines = text.split("\n")
    cursor = {"x": len(lines[-1]), "y": len(lines) - 1}
    assert page.evaluate("([l, c]) => conquerTouch.whereAmI(l, c)", [lines, cursor]) == want
    page.close()


def grid_boxes(page):
    """The overlay grid's box and the terminal's text area box, in page pixels."""
    return page.evaluate("""() => {
        const g = document.querySelector('.touch-grid').getBoundingClientRect();
        const frame = document.getElementById('game');
        let s;
        if (frame) {
            const r = frame.contentWindow.term.element.querySelector('.xterm-screen').getBoundingClientRect();
            const f = frame.getBoundingClientRect(), k = f.width / frame.offsetWidth;
            s = { left: f.left + r.left * k, top: f.top + r.top * k, width: r.width * k, height: r.height * k };
        } else {
            s = term.element.querySelector('.xterm-screen').getBoundingClientRect();
        }
        return [[g.left, g.top, g.width, g.height], [s.left, s.top, s.width, s.height]];
    }""")


@pytest.mark.parametrize("where", ["try", "game"])
@pytest.mark.parametrize("viewport", ["desktop", "phone"])
def test_grid_covers_the_text_area(site, browser, where, viewport):
    """The overlay's box is the terminal's text area (within a pixel), before
    and after zooming the stage on a phone."""
    ctx, page, target = touch_page(site, browser, where, viewport)
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.wait_for_timeout(500)
    grid, screen = grid_boxes(page)
    assert grid == pytest.approx(screen, abs=1), (grid, screen)
    if viewport == "phone":
        stage_width = "document.getElementById('touch-stage').getBoundingClientRect().width"
        vp = page.evaluate("document.getElementById('touch-viewport').getBoundingClientRect().width")
        assert vp < 390
        # held upright, the map starts zoomed (about 40 columns across the screen) ...
        assert page.evaluate(stage_width) > 600
        grid, screen = grid_boxes(page)
        assert grid == pytest.approx(screen, abs=1), (grid, screen)
        # ... a double tap brings the whole 80 columns to the phone's width ...
        page.touchscreen.tap(vp / 2, 300)
        page.touchscreen.tap(vp / 2, 300)
        page.wait_for_function("() => document.getElementById('touch-stage').getBoundingClientRect().width < 400", timeout=3000)
        page.wait_for_timeout(500)
        grid, screen = grid_boxes(page)
        assert grid == pytest.approx(screen, abs=1), (grid, screen)
        assert page.evaluate(stage_width) == pytest.approx(vp, abs=1)
        # ... and another one zooms in again
        page.touchscreen.tap(vp / 2, 300)
        page.touchscreen.tap(vp / 2, 300)
        page.wait_for_function("() => document.getElementById('touch-stage').getBoundingClientRect().width > 600", timeout=3000)
        page.wait_for_timeout(500)
        grid, screen = grid_boxes(page)
        assert grid == pytest.approx(screen, abs=1), (grid, screen)
        assert grid[2] > 600
    ctx.close()


def cell_point(page, col, row):
    """The page pixel at the middle of a terminal cell, from the grid's box."""
    return page.evaluate("""([c, r]) => {
        const g = document.querySelector('.touch-grid').getBoundingClientRect();
        const t = window.term || document.getElementById('game').contentWindow.term;
        return [g.left + (c + 0.5) * g.width / t.cols, g.top + (r + 0.5) * g.height / t.rows];
    }""", [col, row])


def watch_keys(page, target, where):
    """From now on, collect the keys the layer sends (the page's send is
    replaced on /try/; on game.html the stand-in for ttyd records them)."""
    if where == "try":
        page.evaluate("window.keys = []; touchLayer.options.send = s => { keys.push(s) }; 0")
    else:
        target.evaluate("window.sent = ''")


def sent_keys(page, target, where):
    return "".join(page.evaluate("keys")) if where == "try" else target.evaluate("sent")


@pytest.mark.parametrize("where,viewport", [("try", "desktop"), ("game", "desktop"), ("game", "phone")])
def test_tap_the_map_to_move(site, browser, where, viewport):
    """The cursor is at sector (13, 10); a tap on the cell of sector (15, 7)
    sends the diagonals first, then the straights; taps outside the map do
    nothing; a second tap while moving cancels the rest."""
    ctx, page, target = touch_page(site, browser, where, viewport)
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.wait_for_timeout(1200 if viewport == "phone" else 300)    # the phone's view settles on the cursor
    watch_keys(page, target, where)

    def tap(col, row):
        x, y = cell_point(page, col, row)
        if not page.evaluate("([x, y]) => { const v = document.getElementById('touch-viewport').getBoundingClientRect(); return x > v.left && x < v.right && y > v.top && y < v.bottom; }", [x, y]):
            return                               # zoomed in on a phone: that cell is off the screen
        if viewport == "phone":
            page.touchscreen.tap(x, y)
            page.wait_for_timeout(400)           # a phone waits for a possible double tap
        else:
            page.mouse.click(x, y)
        page.wait_for_timeout(500)

    tap(30, 7)
    assert sent_keys(page, target, where) == "uuk"
    # the status line, the right panel: nothing
    watch_keys(page, target, where)
    cols, rows = target.evaluate("[term.cols, term.rows]")
    tap(30, rows - 3)
    tap(cols - 5, 5)
    assert sent_keys(page, target, where) == ""
    # a long way (15 keys), cancelled by a second tap
    if viewport == "desktop":
        watch_keys(page, target, where)
        x, y = cell_point(page, 56, 0)
        page.mouse.click(x, y)
        page.wait_for_timeout(120)
        page.mouse.click(x, y)
        page.wait_for_timeout(800)
        got = sent_keys(page, target, where)
        assert 1 <= len(got) < 15 and set(got) <= {"u", "l"}, got
    ctx.close()


def pointer(page, kind, pid, x, y):
    """A touch pointer event on the grid (Playwright has no multi-touch)."""
    page.evaluate("""([k, id, x, y]) => { document.querySelector('.touch-grid').dispatchEvent(new PointerEvent(k, {
        pointerId: id, pointerType: 'touch', clientX: x, clientY: y, bubbles: true, cancelable: true, isPrimary: id === 1 })); }""",
                  [kind, pid, x, y])


def test_drag_the_edge_to_scroll_the_map(site, browser):
    """A drag on the edge gutter scrolls the map with the shift letters, one
    key per 120 px; a drag inside the map is not a tap and sends nothing."""
    ctx, page, target = touch_page(site, browser, "try", "desktop")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    watch_keys(page, target, "try")
    x, y = cell_point(page, 1, 10)
    pointer(page, "pointerdown", 1, x, y)
    pointer(page, "pointermove", 1, x + 130, y)
    pointer(page, "pointermove", 1, x + 130, y + 250)
    pointer(page, "pointerup", 1, x + 130, y + 250)
    assert sent_keys(page, target, "try") == "HKK"
    watch_keys(page, target, "try")
    x, y = cell_point(page, 20, 8)
    pointer(page, "pointerdown", 1, x, y)
    pointer(page, "pointermove", 1, x + 60, y)
    pointer(page, "pointerup", 1, x + 60, y)
    # two fingers anywhere on the map: the same
    a, b = cell_point(page, 20, 5), cell_point(page, 24, 5)
    pointer(page, "pointerdown", 1, a[0], a[1])
    pointer(page, "pointerdown", 2, b[0], b[1])
    pointer(page, "pointermove", 1, a[0], a[1] + 130)
    pointer(page, "pointermove", 2, b[0], b[1] + 130)
    pointer(page, "pointerup", 1, a[0], a[1] + 130)
    pointer(page, "pointerup", 2, b[0], b[1] + 130)
    page.wait_for_timeout(300)
    assert sent_keys(page, target, "try") == "K"
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_pinch_zooms_and_a_finger_pans(site, browser, where):
    """On a phone: two fingers moving apart zoom the stage (up to 2.5 times
    the fit), one finger pans it, the grid stays over the text."""
    ctx, page, target = touch_page(site, browser, where, "phone")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    watch_keys(page, target, where)

    def stage():
        return page.evaluate("(() => { const r = document.getElementById('touch-stage').getBoundingClientRect(); return [r.left, r.top, r.width]; })()")
    fit = stage()
    vp = page.evaluate("(() => { const r = document.getElementById('touch-viewport').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
    assert fit[2] == pytest.approx(vp[2], abs=1)
    cx, cy = vp[0] + vp[2] / 2, vp[1] + vp[3] / 2
    pointer(page, "pointerdown", 1, cx - 40, cy)
    pointer(page, "pointerdown", 2, cx + 40, cy)
    for step in range(1, 7):
        pointer(page, "pointermove", 1, cx - 40 - step * 20, cy)
        pointer(page, "pointermove", 2, cx + 40 + step * 20, cy)
    pointer(page, "pointerup", 1, cx - 160, cy)
    pointer(page, "pointerup", 2, cx + 160, cy)
    zoomed = stage()
    assert zoomed[2] == pytest.approx(vp[2] * 2.5, abs=2)           # the limit
    grid, screen = grid_boxes(page)
    assert grid == pytest.approx(screen, abs=1)
    # one finger pans: 60 px to the left; not a tap, so no keys
    pointer(page, "pointerdown", 1, cx + 30, cy)
    pointer(page, "pointermove", 1, cx, cy)
    pointer(page, "pointermove", 1, cx - 30, cy)
    pointer(page, "pointerup", 1, cx - 30, cy)
    panned = stage()
    assert panned[0] == pytest.approx(zoomed[0] - 60, abs=2)
    grid, screen = grid_boxes(page)
    assert grid == pytest.approx(screen, abs=1)
    page.wait_for_timeout(500)
    assert sent_keys(page, target, where) == ""
    ctx.close()


def test_the_rotate_hint_shows_once(site, browser):
    ctx, page, target = touch_page(site, browser, "try", "phone")
    assert page.is_visible(".touch-hint")
    assert "sideways" in page.inner_text(".touch-hint")
    page.click(".touch-hint button")
    assert not page.is_visible(".touch-hint")
    page.reload()
    page.wait_for_function("() => window.touchLayer")
    page.wait_for_timeout(500)
    assert not page.is_visible(".touch-hint")
    ctx.close()
    # in landscape there is nothing to say
    ctx, page, target = touch_page(site, browser, "try", "landscape")
    assert not page.is_visible(".touch-hint")
    ctx.close()


def test_every_path_is_diagonals_then_straights(site, browser):
    page = browser.new_page()
    page.goto(site + "try/")
    page.wait_for_function("() => window.conquerTouch")
    got = page.evaluate("[[2, -3], [-4, -1], [0, 5], [-3, 0], [3, 2], [-1, 2], [40, 40], [0, 0]].map(d => conquerTouch.mapPath(d[0], d[1]))")
    assert got == ["uuk", "yhhh", "jjjjj", "hhh", "nnl", "bj", "n" * 40, ""]
    page.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_chips_follow_the_screen(site, browser, where):
    """The chips and the badge change with what the game shows: a budget
    report offers its keys and Back; a (y/n) question Yes and No; a prompt
    for text, Type; for a number, the keypad; the map, its commands."""
    ctx, page, target = touch_page(site, browser, where, "desktop")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    state = bar(page)
    assert state["where"] == "Map" and not state["back"]
    assert state["chips"][:4] == ["Move", "Armies", "Budget", "Construct"] and "Quit" in state["chips"]
    show(page, target, FIRST_TURN["budget"])
    wait_where(page, "report")
    state = bar(page)
    assert state["where"] == "Map › Budget" and state["back"]
    assert state["chips"] == ["Production", "Change", "Home"]
    show(page, target, FIRST_TURN["quit"])
    wait_where(page, "prompt_yn")
    assert bar(page)["chips"] == ["Yes", "No"]
    show(page, target, FIRST_TURN["password"])
    wait_where(page, "prompt_text")
    assert bar(page)["chips"] == ["Type", "Enter", "Delete", "Esc"]
    show(page, target, "\n\n\nhow many Infantry do you wish to raise:")
    wait_where(page, "prompt_number")
    assert bar(page)["chips"][:10] == [str(n % 10) for n in range(1, 11)]
    show(page, target, FIRST_TURN["menu"])
    wait_where(page, "menu")
    chips = bar(page)["chips"]
    assert chips[0] == "Play" and chips[-1] == "Log out"
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_chips_send_their_keys(site, browser, where):
    ctx, page, target = touch_page(site, browser, where, "desktop")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    watch_keys(page, target, where)
    page.locator("#touch-chips .touch-chip", has_text="Budget").click()
    assert sent_keys(page, target, where) == "B"
    # Back from a report is the key that ends it
    show(page, target, FIRST_TURN["armies"])
    wait_where(page, "report")
    watch_keys(page, target, where)
    page.click("#touch-back")
    assert sent_keys(page, target, where) == " "
    # and More lists every command of the game, each one a key
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.locator("#touch-chips .touch-chip", has_text="More").click()
    page.wait_for_selector(".touch-sheet:not([hidden])")
    cmds = page.evaluate("[...document.querySelectorAll('.touch-cmd kbd')].map(k => k.textContent)")
    for key in "abBcCdDfFgGHIJKLmMNpPqrRsStTvwWxXYZ?":
        assert key in cmds, key
    watch_keys(page, target, where)
    page.locator(".touch-cmd", has_text="Go to your capital").click()
    assert sent_keys(page, target, where) == "X"
    assert page.evaluate("document.querySelector('.touch-sheet').hidden")
    ctx.close()


def test_the_dpad_moves_and_scrolls(site, browser):
    """Tap: one step (y u b n h j k l); hold: a page of the map (capitals);
    the middle one picks the next unit (p)."""
    ctx, page, target = touch_page(site, browser, "try", "phone")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.evaluate("window.keys = []; touchLayer.options.send = s => { keys.push(s) }; 0")
    page.wait_for_selector(".touch-dpad:not([hidden])")
    page.click(".touch-pb[data-key='u']")
    page.click(".touch-pb[data-key='p']")
    page.locator(".touch-pb[data-key='h']").dispatch_event("pointerdown", {"pointerType": "touch"})
    page.wait_for_timeout(700)
    page.locator(".touch-pb[data-key='h']").dispatch_event("pointerup", {"pointerType": "touch"})
    assert page.evaluate("keys") == ["u", "p", "H"]
    # the Move chip hides it
    page.locator("#touch-chips .touch-chip", has_text="Move").click()
    assert page.evaluate("document.querySelector('.touch-dpad').hidden")
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_options_persist(site, browser, where):
    """Scanlines, the plain frame, the race and the key hints are kept in localStorage
    (conquer-touch) across a reload."""
    ctx, page, target = touch_page(site, browser, where, "desktop")
    page.click("#touch-gear")
    assert page.evaluate("document.getElementById('touch-gear').getAttribute('aria-expanded')") == "true"
    page.check("#touch-opt-scan")
    page.check("#touch-opt-plain")
    page.select_option("#touch-opt-race", "dwarf")
    page.uncheck("#touch-opt-hints")
    assert page.evaluate("document.querySelector('.touch-viewport').classList.contains('touch-scan')")
    stored = json.loads(page.evaluate("localStorage.getItem('conquer-touch')"))
    assert stored["scan"] is True and stored["plain"] is True and stored["hints"] is False
    assert page.get_attribute("html", "data-race") == "dwarf"
    page.reload()
    page.wait_for_function("() => window.touchLayer")
    page.wait_for_timeout(400)
    assert page.evaluate("document.querySelector('.touch-viewport').classList.contains('touch-scan')")
    assert page.get_attribute("html", "data-race") == "dwarf"        # the race survives the reload
    assert page.evaluate("document.getElementById('stone').classList.contains('plain')")
    assert page.evaluate("document.getElementById('touch-ui').classList.contains('touch-nohints')")
    page.click("#touch-gear")
    assert page.is_checked("#touch-opt-scan") and not page.is_checked("#touch-opt-hints")
    # Escape closes the panel
    page.keyboard.press("Escape")
    assert page.evaluate("document.getElementById('touch-panel').hidden")
    ctx.close()


def test_the_keys_button_folds_the_bar(site, browser):
    ctx, page, target = touch_page(site, browser, "game", "desktop")
    assert page.is_visible("#touch-ui")
    page.click("#toggle")
    assert not page.is_visible("#touch-ui")
    assert page.get_attribute("#toggle", "aria-expanded") == "false"
    page.click("#toggle")
    assert page.is_visible("#touch-ui")
    ctx.close()


@pytest.mark.parametrize("lang,army,budget,where", [
    ("es", "Ejércitos", "Presupuesto", "Mapa › Presupuesto"),
    ("zh", "军队", "预算", "地图 › 预算"),
])
@pytest.mark.parametrize("page_name", ["try", "game"])
def test_touch_texts_are_translated(site, browser, page_name, lang, army, budget, where):
    ctx, page, target = touch_page(site, browser, page_name, "desktop", lang=lang)
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.wait_for_function("a => document.getElementById('touch-chips').textContent.includes(a)", arg=army, timeout=5000)
    assert budget in bar(page)["chips"]
    show(page, target, FIRST_TURN["budget"])
    wait_where(page, "report")
    page.wait_for_function("w => document.getElementById('touch-where').textContent === w", arg=where, timeout=5000)
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
@pytest.mark.parametrize("viewport", ["phone", "desktop"])
def test_touch_layer_has_no_console_errors(site, browser, where, viewport):
    errors = []
    ctx, page, target = touch_page(site, browser, where, viewport, errors=errors)
    for name in ("map", "budget", "quit", "password"):
        show(page, target, FIRST_TURN[name], (26, 10) if name == "map" else None)
        page.wait_for_timeout(400)
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.locator("#touch-chips .touch-chip", has_text="More").click()
    page.keyboard.press("Escape")
    page.click("#touch-gear")
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": VIEWPORTS["landscape"]["width"], "height": VIEWPORTS["landscape"]["height"]})
    page.wait_for_timeout(800)
    assert errors == []
    ctx.close()


@pytest.mark.skipif(not SHOTS, reason="TOUCH_SHOTS=<folder> writes the screenshots")
@pytest.mark.parametrize("where", ["try", "game"])
@pytest.mark.parametrize("viewport", ["phone", "landscape", "desktop"])
def test_screenshots(site, browser, where, viewport):
    ctx, page, target = touch_page(site, browser, where, viewport)
    shots = {"map": (FIRST_TURN["map"], (26, 10)), "report": (FIRST_TURN["budget"], None),
             "prompt": (FIRST_TURN["quit"], None)}
    os.makedirs(SHOTS, exist_ok=True)
    for name, (text, cursor) in shots.items():
        show(page, target, text, cursor)
        page.wait_for_timeout(700)
        page.screenshot(path=os.path.join(SHOTS, "%s-%s-%s.png" % (where, viewport, name)))
    show(page, target, FIRST_TURN["map"], (26, 10))
    page.wait_for_timeout(500)
    page.click("#touch-gear")
    page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(SHOTS, "%s-%s-options.png" % (where, viewport)))
    page.evaluate("conquerAudio.enable(true)")
    page.evaluate("document.getElementById('touch-opt-music').checked = true")
    page.screenshot(path=os.path.join(SHOTS, "integrated-%s-%s-options-sound.png" % (where, viewport)))
    page.keyboard.press("Escape")
    page.locator("#touch-chips .touch-chip", has_text="More").click()
    page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(SHOTS, "%s-%s-more.png" % (where, viewport)))
    ctx.close()

def audio_page(site, browser, init=None):
    page = browser.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "404" not in m.text else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    if init:
        page.add_init_script(init)
    page.goto(site + "audio-test.html")
    return page, errors


def test_nation_password_prompt_says_how_long_it_may_be(site, browser):
    errors = []
    ctx, page, target = touch_page(site, browser, "try", "phone", errors=errors)
    show(page, target, "< Building Country iberia >\n\nEnter National Password: ")
    page.wait_for_function("() => !document.getElementById('touch-fieldhint').hidden", timeout=5000)
    assert page.inner_text("#touch-fieldhint") == "2–7 characters"
    show(page, target, "< Building Country iberia >\n\nEnter a Name for your Country: ")
    page.wait_for_function("() => document.getElementById('touch-fieldhint').hidden", timeout=5000)
    assert errors == []
    ctx.close()


def test_nation_password_hint_shows_with_the_builders_status_line(site, browser):
    """In the real builder the bottom line always says "Nation Builder": the hint
    must still show at the password prompt (found by the end-to-end rehearsal)."""
    ctx, page, target = touch_page(site, browser, "try", "desktop")
    screen = "< Building Country iberia >\n\nEnter National Password: " + "\n" * 20 + " Conquer 4.12: Nation Builder       Country #8"
    show(page, target, screen, (26, 2))
    wait_where(page, "builder")
    page.wait_for_function("() => !document.getElementById('touch-fieldhint').hidden", timeout=5000)
    assert page.inner_text("#touch-fieldhint") == "2–7 characters"
    ctx.close()


def test_nation_password_hint_does_not_resize_the_screen(site, browser):
    """The hint used to take a row of its own, so the screen was refitted (a resize
    for the game) while the player typed the password: the second entry then did
    not match. It floats now: the screen keeps its size (found by the end-to-end
    rehearsal)."""
    for viewport in ("desktop", "phone"):
        ctx, page, target = touch_page(site, browser, "game", viewport)
        name = "< Building Country iberia >\n\nEnter a Name for your Country: "
        show(page, target, name)
        page.wait_for_function("() => document.getElementById('touch-fieldhint').hidden", timeout=5000)
        page.wait_for_timeout(600)
        measure = "() => { const r = document.querySelector('.stone').getBoundingClientRect(); return [Math.round(r.height), Math.round(r.width)]; }"
        rows = lambda: target.evaluate("[term.cols, term.rows]")
        before, size = page.evaluate(measure), rows()
        show(page, target, "< Building Country iberia >\n\nEnter National Password: ")
        page.wait_for_function("() => !document.getElementById('touch-fieldhint').hidden", timeout=5000)
        page.wait_for_timeout(600)
        assert page.evaluate(measure) == before, viewport
        assert rows() == size, viewport
        ctx.close()


def test_map_is_redrawn_when_the_terminal_changes_size(site, browser):
    """The game takes the new size but redraws only what it draws next, so the
    sector panel showed twice on a wide screen (the end-to-end rehearsal read
    the old one): on the map the layer sends ^L after a resize, and only there."""
    ctx, page, target = touch_page(site, browser, "game", "desktop")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.wait_for_timeout(600)
    watch_keys(page, target, "game")
    page.set_viewport_size({"width": 1100, "height": 640})
    end = time.time() + 10
    while "\x0c" not in sent_keys(page, target, "game") and time.time() < end:
        page.wait_for_timeout(200)
    assert "\x0c" in sent_keys(page, target, "game")
    # not at a prompt: a ^L there would be typed into the answer
    show(page, target, "< Building Country iberia >\n\nEnter a Name for your Country: ")
    page.wait_for_timeout(600)
    watch_keys(page, target, "game")
    page.set_viewport_size({"width": 1280, "height": 800})
    page.wait_for_timeout(1500)
    assert "\x0c" not in sent_keys(page, target, "game")
    ctx.close()


def test_audio_plays_after_a_click(site, browser):
    page, errors = audio_page(site, browser)
    assert page.evaluate("conquerAudio.enabled()") is False
    page.click("#b")
    page.evaluate("conquerAudio.enable(true)")
    page.wait_for_function("() => conquerAudio._state() === 'running'")
    assert page.evaluate("conquerAudio.enabled()") is True
    # the effects are files: all of them load
    page.wait_for_function("() => conquerAudio._loaded().length === 13", timeout=15000)
    assert page.evaluate("conquerAudio._failed()") == []
    before = page.evaluate("conquerAudio._nodes()")
    page.evaluate("conquerAudio.event('turn'); conquerAudio.event('ui'); conquerAudio.event('bogus')")
    assert page.evaluate("conquerAudio._nodes()") == before + 2
    # screen() picks the bed; the map's follows the race
    page.evaluate("conquerAudio.screen('map')")
    assert page.evaluate("conquerAudio._bed()") == "map-human"
    page.evaluate("document.documentElement.setAttribute('data-race', 'dwarf'); conquerAudio.screen('map')")
    assert page.evaluate("conquerAudio._bed()") == "map-dwarf"
    for s, bed in (("builder", "builder"), ("report_x", "report"), ("combat", "combat"), ("menu", "combat"), ("off", "")):
        page.evaluate("s => conquerAudio.screen(s)", s)
        assert page.evaluate("conquerAudio._bed()") == bed
    page.evaluate("conquerAudio.screen('app-home')")
    assert page.evaluate("conquerAudio._bed()") == "app-home"
    assert page.evaluate("conquerAudio._failed()") == []
    assert page.evaluate("conquerAudio._demo()") == ["app-doors-open"]
    page.evaluate("conquerAudio.enable(false)")
    assert page.evaluate("conquerAudio.enabled()") is False
    assert page.evaluate("conquerAudio._bed()") == ""
    assert errors == []
    page.close()


def test_audio_music_and_effects_are_separate_and_persist(site, browser):
    page, errors = audio_page(site, browser)
    page.click("#b")
    page.evaluate("""() => { const a = conquerAudio; a.setMusic(true); a.setEffects(false);
        a.musicVolume(0.3); a.effectsVolume(0.7); a.setVolume(0.2); }""")
    assert page.evaluate("[conquerAudio.music(), conquerAudio.effects(), conquerAudio.enabled()]") == [True, False, True]
    page.wait_for_function("() => conquerAudio._state() === 'running'")
    page.wait_for_function("() => conquerAudio._loaded().length === 13", timeout=15000)
    before = page.evaluate("conquerAudio._nodes()")
    page.evaluate("conquerAudio.event('turn')")           # effects are off: silent
    assert page.evaluate("conquerAudio._nodes()") == before
    page.reload()
    assert page.evaluate("[conquerAudio.music(), conquerAudio.effects()]") == [True, False]
    assert page.evaluate("[conquerAudio.volume(), conquerAudio.musicVolume(), conquerAudio.effectsVolume()]") == [0.2, 0.3, 0.7]
    # enabled before, but nothing starts until the first click
    assert page.evaluate("conquerAudio._state()") == "none"
    page.click("#b")
    page.wait_for_function("() => conquerAudio._state() === 'running'")
    page.evaluate("conquerAudio.setMusic(false)")
    assert page.evaluate("conquerAudio.enabled()") is False
    assert errors == []
    page.close()


def test_audio_falls_back_to_the_synth_when_a_file_is_missing(site, browser):
    page, errors = audio_page(site, browser, "localStorage.setItem('conquer-audio', JSON.stringify({music: true, effects: true}))")
    page.route("**/sound/*.ogg", lambda r: r.fulfill(status=404, body=""))
    page.click("#b")
    page.wait_for_function("() => conquerAudio._state() === 'running'")
    page.evaluate("conquerAudio.screen('builder')")
    page.wait_for_function("() => conquerAudio._failed().length > 0", timeout=15000)
    page.evaluate("conquerAudio.event('turn')")
    page.wait_for_timeout(300)
    assert page.evaluate("conquerAudio._nodes()") > 0
    page.close()


def test_audio_without_web_audio_is_silent(site, browser):
    page, errors = audio_page(site, browser, "delete window.AudioContext; delete window.webkitAudioContext;")
    page.click("#b")
    page.evaluate("""() => { const a = conquerAudio; a.enable(true); a.event('turn'); a.screen('map');
        a.setVolume(0.3); a.setMusic(true); a.setEffects(true); a._demo(); a.enable(false); }""")
    assert page.evaluate("conquerAudio.enabled()") is False
    page.wait_for_timeout(200)
    assert errors == []
    page.close()


def test_touch_layer_and_sound_work_together(site, browser):
    errors = []
    ctx, page, target = touch_page(site, browser, "try", "desktop", errors=errors)
    page.evaluate("""() => { window.__aud = []; const a = window.conquerAudio;
        const s = a.screen, e = a.event;
        a.screen = n => { window.__aud.push(['screen', n]); return s.call(a, n); };
        a.event = n => { window.__aud.push(['event', n]); return e.call(a, n); }; }""")
    page.click("#touch-gear")
    page.click("#touch-opt-music")
    assert page.evaluate("conquerAudio.music()") is True
    assert page.evaluate("conquerAudio.effects()") is False
    page.click("#touch-opt-effects")
    assert page.evaluate("conquerAudio.effects()") is True
    for i in ("touch-opt-music-volume", "touch-opt-effects-volume"):
        assert page.is_visible("#" + i)
    page.fill("#touch-opt-music-volume", "30")
    assert page.evaluate("conquerAudio.musicVolume()") == 0.3
    assert page.is_visible("#touch-opt-preview")
    page.keyboard.press("Escape")
    show(page, target, FIRST_TURN["budget"])
    wait_where(page, "report")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    log = page.evaluate("window.__aud")
    screens = [n for k, n in log if k == "screen"]
    assert screens.index("report") < screens.index("map", screens.index("report"))
    page.evaluate("window.__aud.length = 0")
    page.locator("#touch-chips .touch-chip").first.click()
    assert ["event", "ui"] in page.evaluate("window.__aud")
    assert errors == []
    ctx.close()


# ---------------------------------------------------------------------------
# The design system on every page (web/theme.css) and the game screen's artefacts

PAGES = ["index.html", "signup.html", "hall.html", "guide.html", "guide.es.html", "tutorial.html", "tutorial.de.html",
         "design.html", "game.html", "try/index.html", "admin.html"]
HEX = re.compile(r"(?<![&\w])#[0-9a-fA-F]{3,8}\b|rgba?\(")


@pytest.mark.parametrize("name", PAGES)
def test_every_page_uses_the_theme_and_has_no_colours_of_its_own(site, browser, name):
    """theme.css is loaded, the page has a site header and no colour literal
    in its own markup or styles (theme.css and the xterm themes made from its
    tokens are the only places colours live), and the console stays quiet."""
    src = (WEB / name).read_text(encoding="utf-8")
    assert re.search(r'<link rel="stylesheet" href="(\.\./|/)?theme\.css">', src), name
    assert 'class="site-header' in src, name
    assert not HEX.search(re.sub(r"<!--.*?-->", "", src, flags=re.S)), name
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and "404" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/admin/api/state", lambda r: r.fulfill(json={"ok": True, "requests": [], "players": [], "invites": []}))
    page.goto(site + name)
    page.wait_for_timeout(500)
    assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--phos').trim()") == "#8fe3a0"
    assert page.evaluate("!!document.querySelector('.site-header .nav')") or name in ("design.html",)
    assert not errors, errors
    ctx.close()


def test_long_reading_pages_are_parchment_with_a_dark_header(site, browser):
    for name in ["guide.html", "guide.es.html", "tutorial.html", "tutorial.de.html"]:
        page = browser.new_page()
        page.goto(site + name)
        assert page.get_attribute(".reading", "data-theme") == "parchment", name
        assert page.get_attribute("html", "data-theme") is None, name
        header_bg = page.evaluate("getComputedStyle(document.querySelector('.site-header')).backgroundColor")
        reading_bg = page.evaluate("getComputedStyle(document.querySelector('.reading')).backgroundColor")
        assert header_bg != reading_bg, name
        page.close()


def test_race_choice_sets_and_keeps_the_phosphor(site, browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(site + "hall.html")
    assert page.get_attribute("html", "data-race") is None
    page.evaluate("conquerRace.choose('elf')")
    assert page.get_attribute("html", "data-race") == "elf"
    page.reload()
    assert page.get_attribute("html", "data-race") == "elf"
    assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--phos').trim()") != "#8fe3a0"
    # what the game shows is used only while nothing was chosen
    page.evaluate("conquerRace.seen('orc')")
    assert page.get_attribute("html", "data-race") == "elf"
    page.evaluate("conquerRace.choose('auto')")
    assert page.get_attribute("html", "data-race") == "orc"
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_game_screen_reads_the_race_and_turns_to_parchment(site, browser, where):
    """The nation's race on screen sets the colours; reports and the builder
    are read on parchment (the stone and the terminal's own theme together)."""
    ctx, page, target = touch_page(site, browser, where, "desktop")
    assert page.evaluate("document.getElementById('stone').classList.contains('parchment')") is False
    dark = target.evaluate("term.options.theme.background")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    assert page.evaluate("document.getElementById('stone').classList.contains('parchment')") is False
    show(page, target, FIRST_TURN["budget"])
    wait_where(page, "report")
    page.wait_for_function("() => document.getElementById('stone').classList.contains('parchment')")
    paper = target.evaluate("term.options.theme.background")
    assert paper != dark
    show(page, target, FIRST_TURN["map"], (26, 10))
    page.wait_for_function("() => !document.getElementById('stone').classList.contains('parchment')")
    assert target.evaluate("term.options.theme.background") == dark
    # the nation builder says the race: Dwarf
    show(page, target, "Nation Builder\n\nNational Race: Dwarf\n")
    wait_where(page, "builder")
    page.wait_for_function("() => document.documentElement.getAttribute('data-race') === 'dwarf'")
    ctx.close()
