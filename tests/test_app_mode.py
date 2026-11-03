# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pages inside the Android app (html.in-app): no site chrome, a compact
bar, the practice game in one tap, a game that fits phones, sound on by
default, and the bridge (window.cefriumQuery) used when there is one.

Needs a browser: pytest -m browser (CHROMIUM=/path/to/chrome)."""
import json

import pytest

from conftest import ROOT
from test_browser import FIRST_TURN, VIEWPORTS, browser, show, site, touch_page, wait_where  # noqa: F401

pytestmark = pytest.mark.browser

# What the app's bridge looks like to a page: calls collect in window.calls
SPY = """window.calls = [];
window.cefriumQuery = function (o) { window.calls.push(JSON.parse(o.request)); if (o.onSuccess) o.onSuccess('{"ok":true}'); };"""


def calls(page):
    return page.evaluate("window.calls")


def has_class(page, name="in-app"):
    return page.evaluate("document.documentElement.classList.contains(%s)" % json.dumps(name))


@pytest.mark.parametrize("how", ["query", "ua", "bridge"])
def test_the_app_is_recognised(site, browser, how):
    kwargs = {"query": "app=1"} if how == "query" else {"init": SPY} if how == "bridge" else {}
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True,
                              user_agent="Mozilla/5.0 (Linux; Android 14) Cefrium/1.0" if how == "ua" else None)
    if "init" in kwargs:
        ctx.add_init_script(kwargs["init"])
    page = ctx.new_page()
    page.goto(site + "game.html" + ("?app=1" if how == "query" else ""))
    assert has_class(page)
    # the site's header is gone, the app's bar (44 px at most) is there
    assert not page.is_visible("#site-header")
    assert page.is_visible("#app-bar")
    assert page.evaluate("document.getElementById('app-bar').getBoundingClientRect().height") <= 44
    for name in ("app-home", "app-coach", "app-keyboard", "app-menu"):
        assert page.is_visible("#" + name), name
    ctx.close()


def test_app_mode_is_remembered_while_navigating(site, browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto(site + "index.html?app=1")
    assert has_class(page)
    assert not page.is_visible(".site-header") and not page.is_visible(".site-footer")
    page.goto(site + "hall.html")
    assert has_class(page)
    ctx.close()
    # the web is untouched
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto(site + "index.html")
    assert not has_class(page)
    assert page.is_visible(".site-header") and page.is_visible(".site-footer")
    page.goto(site + "game.html")
    assert page.is_visible("#site-header") and not page.is_visible("#app-bar")
    ctx.close()


def test_the_app_bar_menu_and_home(site, browser):
    ctx, page, target = touch_page(site, browser, "game", "phone", query="app=1")
    page.click("#app-coach")
    assert page.is_visible("#coach")
    page.click("#app-coach")
    assert not page.is_visible("#coach")
    page.click("#app-menu")
    assert page.is_visible("#app-menu-list")
    assert page.locator("#app-menu-list .app-item").count() >= 2
    ctx.close()


def test_the_app_bar_folds_away_sideways(site, browser):
    ctx, page, target = touch_page(site, browser, "game", "landscape", query="app=1")
    assert not page.is_visible("#app-bar") or page.evaluate("document.getElementById('app-bar').getBoundingClientRect().bottom") <= 0
    assert page.is_visible("#app-handle")
    page.click("#app-handle")
    page.wait_for_timeout(400)
    assert page.evaluate("document.getElementById('app-bar').getBoundingClientRect().top") >= 0
    ctx.close()


def test_the_menu_gets_the_app_argument(site, browser):
    ctx, page, target = touch_page(site, browser, "game", "phone", query="app=1")
    assert "arg=app%3D1" in target.url and "arg=en" in target.url
    ctx.close()
    ctx, page, target = touch_page(site, browser, "game", "phone")
    assert "app" not in target.url.split("?", 1)[1]
    ctx.close()


def test_the_practice_game_starts_by_itself(site, browser):
    errors = []
    ctx, page, target = touch_page(site, browser, "try", "phone", query="app=1&autostart=1", errors=errors)
    # no "How to move", no coach, no password to type: the map
    page.wait_for_function("() => touchLayer.where() === 'map'", timeout=90000)
    assert not page.is_visible("#moves-panel")
    assert not page.is_visible("#coach")
    assert "Password" not in page.evaluate("[...Array(24).keys()].map(y => term.buffer.active.getLine(y).translateToString(true)).join('\\n')")
    assert [e for e in errors if "Content Security Policy" in e or "CompileError" in e] == []
    ctx.close()


def test_the_web_does_not_start_by_itself(site, browser):
    ctx, page, target = touch_page(site, browser, "try", "desktop")
    page.wait_for_timeout(1500)
    assert page.evaluate("touchLayer.where()") != "map"
    assert "Space" in page.evaluate("[...Array(24).keys()].map(y => term.buffer.active.getLine(y).translateToString(true)).join('\\n')")
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
@pytest.mark.parametrize("query", ["", "app=1"])
def test_landscape_shows_every_row(site, browser, where, query):
    """Sideways, the 24 rows of the screen are all inside the box (nothing clipped)."""
    ctx, page, target = touch_page(site, browser, where, "landscape", query=query)
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.wait_for_timeout(900)
    r = page.evaluate("""() => {
        const t = window.term || document.getElementById('game').contentWindow.term;
        const s = t.element.querySelector('.xterm-screen').getBoundingClientRect();
        const f = document.getElementById('game');
        const k = f ? f.getBoundingClientRect().width / f.offsetWidth : 1;
        const o = f ? f.getBoundingClientRect() : { left: 0, top: 0 };
        const box = document.querySelector('.terminal').getBoundingClientRect();
        return { cols: t.cols, rows: t.rows, font: t.options.fontSize, top: o.top + s.top * k, bottom: o.top + s.bottom * k,
                 boxTop: box.top, boxBottom: box.bottom, h: innerHeight };
    }""")
    assert r["cols"] >= 80 and r["rows"] >= 24, r
    assert r["top"] >= r["boxTop"] - 1 and r["bottom"] <= r["boxBottom"] + 1 and r["bottom"] <= r["h"], r
    assert r["font"] >= 9, r        # readable: the frame no longer eats the height
    # the grid still covers the text
    grid = page.evaluate("(() => { const g = document.querySelector('.touch-grid').getBoundingClientRect(); return [g.top, g.bottom]; })()")
    assert grid[1] <= r["h"] + 1
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_portrait_starts_zoomed_on_the_cursor(site, browser, where):
    ctx, page, target = touch_page(site, browser, where, "phone")
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.wait_for_timeout(900)
    r = page.evaluate("""() => {
        const v = document.getElementById('touch-viewport').getBoundingClientRect();
        const g = document.querySelector('.touch-grid').getBoundingClientRect();
        const t = window.term || document.getElementById('game').contentWindow.term;
        const b = t.buffer.active;
        const cx = g.left + (b.cursorX + 0.5) * g.width / t.cols, cy = g.top + (b.cursorY + 0.5) * g.height / t.rows;
        return { vw: v.width, vl: v.left, vt: v.top, vh: v.height, gw: g.width, cx, cy };
    }""")
    # about 40 of the 80 columns fill the width
    assert r["gw"] / r["vw"] == pytest.approx(2, abs=0.35), r
    # and the cursor is in view, near the middle
    assert r["vl"] + r["vw"] * 0.2 < r["cx"] < r["vl"] + r["vw"] * 0.8, r
    assert r["vt"] < r["cy"] < r["vt"] + r["vh"], r
    # a report shows the whole screen
    show(page, target, FIRST_TURN["budget"])
    wait_where(page, "report")
    page.wait_for_function("() => document.getElementById('touch-stage').getBoundingClientRect().width < 400", timeout=4000)
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_sound_is_on_in_the_app_and_off_on_the_web(site, browser, where):
    ctx, page, target = touch_page(site, browser, where, "phone", query="app=1")
    assert page.evaluate("conquerAudio.enabled()") is True
    # a speaker in the ledge mutes it, and the choice is kept
    assert page.is_visible("#touch-sound")
    page.click("#touch-sound")
    assert page.evaluate("conquerAudio.enabled()") is False
    page.reload()
    page.wait_for_function("() => window.touchLayer")
    assert page.evaluate("conquerAudio.enabled()") is False
    ctx.close()
    ctx, page, target = touch_page(site, browser, where, "phone")
    assert page.evaluate("conquerAudio.enabled()") is False
    assert not page.is_visible("#touch-sound")
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_the_bridge_is_used_when_there_is_one(site, browser, where):
    ctx, page, target = touch_page(site, browser, where, "phone", init=SPY)
    assert {"type": "keepAwake", "on": True} in calls(page)
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.evaluate("window.calls.length = 0")
    # the compass buzzes through the app, not through navigator.vibrate
    page.evaluate("window.vibrations = 0; navigator.vibrate = () => { if (new Error().stack.includes('touch.js')) window.vibrations++; return true; }")
    page.evaluate("touchLayer.options.send = () => {}")
    page.locator(".touch-pb[data-key='k']").dispatch_event("pointerup", {"pointerType": "touch"})
    assert {"type": "haptic", "ms": 8} in calls(page)
    assert page.evaluate("window.vibrations") == 0
    # the race of the nation goes to the app's colours
    page.evaluate("conquerRace.choose('elf')")
    assert {"type": "race", "race": "elf"} in calls(page)
    ctx.close()


def test_without_the_bridge_nothing_breaks(site, browser):
    errors = []
    ctx, page, target = touch_page(site, browser, "game", "phone", errors=errors)
    show(page, target, FIRST_TURN["map"], (26, 10))
    wait_where(page, "map")
    page.evaluate("touchLayer.options.send = () => {}")
    page.locator(".touch-pb[data-key='k']").dispatch_event("pointerup", {"pointerType": "touch"})
    page.evaluate("conquerRace.choose('orc')")
    assert errors == []
    ctx.close()


@pytest.mark.parametrize("where", ["try", "game"])
def test_the_keyboard_opens_for_text_with_a_hint_once(site, browser, where):
    ctx, page, target = touch_page(site, browser, where, "phone", query="app=1")
    show(page, target, FIRST_TURN["password"])
    wait_where(page, "prompt_text")
    assert page.is_visible(".touch-kbhint")
    assert "keyboard" in page.inner_text(".touch-kbhint").lower()
    ctx.close()


def test_app_mode_has_no_console_errors(site, browser):
    errors = []
    for where in ("try", "game"):
        for viewport in ("phone", "landscape"):
            ctx, page, target = touch_page(site, browser, where, viewport, query="app=1", errors=errors, init=SPY)
            show(page, target, FIRST_TURN["map"], (26, 10))
            wait_where(page, "map")
            page.wait_for_timeout(500)
            if viewport == "landscape":
                page.click("#app-handle")
                page.wait_for_timeout(400)
            page.click("#app-menu")
            ctx.close()
    assert errors == []
