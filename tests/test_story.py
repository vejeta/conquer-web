# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The story (web/story.html): eight scenes, navigation by tap, keys and
Skip, the progress dots, the texts in several languages, no console errors,
reduced motion, and the entry points (the game shows it once).

Needs the Python playwright module and Chromium (CHROMIUM=/path/to/chrome)."""
import io
import json
import wave

import pytest

from conftest import WEB, load
from test_browser import browser, site  # noqa: F401  (the fixtures: the site and Chromium)

pytestmark = pytest.mark.browser


def story(browser, site, lang="en", w=1280, h=800, query="", dur=",".join(["30"] * 8), **ctx):
    context = browser.new_context(viewport={"width": w, "height": h}, **ctx)
    page = context.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "404" not in m.text else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    # a short fixed length for every scene: the narration files are not needed
    page.goto(site + "story.html?lang=%s%s%s" % (lang, "&dur=" + dur if dur else "", query))
    page.wait_for_function("() => window.conquerStory && document.getElementById('begin')")
    return context, page, errors


def current(page):
    return page.evaluate("() => conquerStory.state().n")


def test_the_eight_scenes_and_skip(site, browser):
    context, page, errors = story(browser, site)
    assert page.locator("#begin").is_visible()
    page.click("#begin")
    page.wait_for_function("() => conquerStory.state().n === 1")
    assert page.locator("#dots i").count() == 8
    assert page.locator("#skip").is_visible()
    box = page.locator("#skip").bounding_box()
    assert box["height"] >= 44 and box["x"] + box["width"] > 1200
    # a tap goes on, Space and the right arrow too, the left arrow goes back
    page.mouse.click(600, 300)
    page.wait_for_function("() => conquerStory.state().n === 2")
    page.keyboard.press("ArrowRight")
    page.wait_for_function("() => conquerStory.state().n === 3")
    page.keyboard.press("Space")
    page.wait_for_function("() => conquerStory.state().n === 4")
    page.keyboard.press("ArrowLeft")
    page.wait_for_function("() => conquerStory.state().n === 3")
    assert page.locator("#dots i.on").count() == 1
    assert page.locator("#dots i.done").count() == 2
    page.wait_for_function("() => document.getElementById('cap-text').textContent.startsWith('In that world there are four peoples')")
    for _ in range(5):
        page.keyboard.press("ArrowRight")
    page.wait_for_function("() => conquerStory.state().n === 8")
    page.wait_for_selector("#actions:not([hidden])", timeout=20000)
    assert page.locator("#play").get_attribute("href").startswith("game.html")
    assert errors == []
    context.close()


def test_skip_leaves_and_remembers(site, browser):
    context, page, errors = story(browser, site, query="&next=try/")
    page.click("#begin")
    page.click("#skip")
    page.wait_for_url("**/try/**")
    assert page.evaluate("() => localStorage.getItem('conquer-story-seen')") == "1"
    context.close()


@pytest.mark.parametrize("lang", ["es", "en", "zh"])
def test_texts_in_the_languages(site, browser, lang):
    context, page, errors = story(browser, site, lang=lang)
    texts = load(WEB / "i18n" / ("%s.json" % lang))["story"]
    assert page.locator("#begin").inner_text() == texts["begin"]
    assert page.locator("#skip").inner_text() == texts["skip"]
    page.click("#begin")
    page.wait_for_function("() => conquerStory.state().n === 1")
    page.wait_for_function("() => document.getElementById('cap-text').textContent.length > 0")
    assert page.locator("#cap-text").inner_text() == texts["p1"]
    page.wait_for_function("() => document.getElementById('t-login').textContent === %s" % json.dumps(texts["d1a"]), timeout=15000)
    assert page.evaluate("() => document.documentElement.lang") == lang
    assert errors == []
    context.close()


def test_phone_and_reduced_motion(site, browser):
    context, page, errors = story(browser, site, lang="es", w=390, h=844, reduced_motion="reduce")
    page.click("#begin")
    page.wait_for_function("() => conquerStory.state().n === 1")
    # with reduced motion the dialogue is written at once and nothing animates
    page.wait_for_function("() => document.getElementById('t-login').textContent === 'login: edb'", timeout=15000)
    assert page.evaluate("() => getComputedStyle(document.querySelector('.rain')).animationName") == "none"
    for k in range(2, 9):
        page.keyboard.press("ArrowRight")
        page.wait_for_function("() => conquerStory.state().n === %d" % k)
    assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")
    assert errors == []
    context.close()


def test_the_game_shows_the_story_once(site, browser):
    # automated browsers skip it, unless asked
    context = browser.new_context()
    page = context.new_page()
    page.goto(site + "game.html?story=1")
    page.wait_for_url("**/story.html**")
    assert "next=game.html" in page.url
    context.close()
    context = browser.new_context()
    page = context.new_page()
    page.goto(site + "game.html")
    page.wait_for_selector("#stone")
    assert "story.html" not in page.url
    context.close()


STUB = """() => {
  window.__calls = [];
  var rec = function (k) { return function (v) { window.__calls.push([k, v === undefined ? '' : v, document.documentElement.getAttribute('data-race') || '']); return k === 'music' || k === 'effects' ? true : undefined; }; };
  window.conquerAudio = { screen: rec('screen'), event: rec('event'), setMusic: rec('setMusic'), setEffects: rec('setEffects'),
                          enable: rec('enable'), music: rec('music'), effects: rec('effects'), enabled: rec('enabled') };
}"""


def calls(page, k):
    return page.evaluate("(k) => window.__calls.filter(c => c[0] === k).map(c => c.slice(1))", k)


def test_the_cues_go_to_audio_js(site, browser):
    context, page, errors = story(browser, site, dur=",".join(["2"] * 8))
    page.evaluate(STUB)
    page.click("#begin")
    # no stored choice: the story switches both channels on for the session
    assert calls(page, "setMusic") == [[True, ""]] and calls(page, "setEffects") == [[True, ""]]
    assert page.evaluate("() => localStorage.getItem('conquer-audio')") is None
    seen = []

    def scene(k, want_screens, want_events):
        page.evaluate("(k) => { window.__calls.length = 0; conquerStory.go(k); }", k)
        page.wait_for_function("(k) => conquerStory.state().n === k && window.__calls.filter(c => c[0] === 'screen' || c[0] === 'event').length >= %d" % (len(want_screens) + len(want_events)), arg=k, timeout=15000)
        assert [c[0] for c in calls(page, "screen")] == want_screens
        assert [c[0] for c in calls(page, "event")] == want_events
    scene(1, ["report"], [])
    scene(2, ["app-home"], ["news"])
    scene(3, ["map"] * 4, [])
    # the map bed follows the race of the panel that lights up
    assert [c[1] for c in calls(page, "screen")] == ["human", "elf", "dwarf", "orc"]
    scene(4, ["map"], ["turn"])
    scene(5, ["off"], [])
    scene(6, ["app-home"], ["app-doors-open"])
    scene(7, ["builder"], ["found"])
    scene(8, ["map"], ["turn"])
    assert errors == []
    context.close()


def test_sound_button_is_the_players_choice(site, browser):
    context, page, errors = story(browser, site)
    page.evaluate(STUB)
    page.click("#begin")
    page.evaluate("() => window.__calls.length = 0")
    assert page.locator("#sound").get_attribute("aria-pressed") == "true"
    page.click("#sound")
    assert page.locator("#sound").get_attribute("aria-pressed") == "false"
    assert calls(page, "setMusic")[-1][0] is False and calls(page, "setEffects")[-1][0] is False
    assert calls(page, "screen")[-1][0] == "off"
    assert page.evaluate("() => conquerStory.state().n") == 1
    context.close()


def test_a_stored_choice_is_respected(site, browser):
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    context.add_init_script("localStorage.setItem('conquer-audio', JSON.stringify({music: false, effects: false}))")
    page = context.new_page()
    page.goto(site + "story.html?lang=en&dur=" + ",".join(["30"] * 8))
    page.wait_for_function("() => window.conquerStory && document.getElementById('begin')")
    assert page.locator("#sound").get_attribute("aria-pressed") == "false"
    page.evaluate(STUB)
    page.click("#begin")
    assert calls(page, "setMusic") == [] and calls(page, "setEffects") == []
    context.close()


def test_without_narration_the_text_times_the_panel(site, browser):
    context, page, errors = story(browser, site, dur="")
    page.click("#begin")
    page.wait_for_function("() => conquerStory.state().n === 1 && conquerStory.state().D > 0", timeout=10000)
    texts = load(WEB / "i18n" / "en.json")["story"]
    assert abs(page.evaluate("() => conquerStory.state().D") - max(5, 2.2 + len(texts["p1"]) * 0.062)) < 0.01
    assert errors == []
    context.close()


def test_narration_file_sets_the_length(site, browser):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"\0\0" * 8000 * 3)
    body = buf.getvalue()
    context, page, errors = story(browser, site, dur="")
    page.route("**/story/en/1.mp3", lambda r: r.fulfill(status=200, body=body, content_type="audio/wav"))
    page.click("#begin")
    page.wait_for_function("() => conquerStory.state().n === 1 && conquerStory.state().D > 0", timeout=10000)
    assert abs(page.evaluate("() => conquerStory.state().D") - 3.0) < 0.1
    context.close()


def test_play_goes_to_try_when_asked(site, browser):
    context, page, errors = story(browser, site, query="&to=try")
    assert page.locator("#play").get_attribute("href").startswith("try/")
    context.close()
