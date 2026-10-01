# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The in-game coach follows the recorded game screens step by step."""
import re

import pytest

from conftest import BUILDER, LANGS, TRACKS, WEB, load, recorded_screens, steps_file

# A recorded screen that is not a coach step of its own: the step it shows
SAME_STEP = {("found-nation", "treasury"): "points"}


# The recordings of each track: the builder is also recorded on a world past
# turn 1, where it gives points for starting late (found-nation-late)
RECORDINGS = {"first-turn": ["first-turn"], "builder": ["found-nation", "found-nation-late"]}
CASES = [(track, video) for track, videos in RECORDINGS.items() for video in videos]


def expected(video, screen_id):
    return SAME_STEP.get((video.replace("-late", ""), screen_id), screen_id)


@pytest.mark.parametrize("track", TRACKS)
@pytest.mark.parametrize("lang", LANGS)
def test_every_language_has_the_same_steps(track, lang):
    english = load(steps_file(track))["steps"]
    steps = load(steps_file(track, lang))["steps"]
    assert [s["id"] for s in steps] == [s["id"] for s in english]
    if track == "builder":
        # The builder speaks English: the screens it waits for do not change
        # (the first turn starts in the menu, which speaks the player's language)
        assert [s["detect"] for s in steps] == [s["detect"] for s in english]
    for s in steps:
        assert s["title"].strip() and s["text"].strip(), s["id"]


@pytest.mark.parametrize("track", TRACKS)
def test_every_step_has_a_recorded_screen(track):
    screens = {expected(video, sid) for video in RECORDINGS[track] for sid, _ in recorded_screens(video)}
    assert [s["id"] for s in load(steps_file(track))["steps"] if s["id"] not in screens] == []


@pytest.mark.parametrize("track,video", CASES)
def test_coach_follows_the_recording(coach, track, video):
    """Played in order, each screen moves the coach to its own step."""
    c = coach(track)
    screens = recorded_screens(video)
    # The first turn opens at its first step; the builder where the player is
    if track == "builder":
        c.open_at_screen(screens[0][1])
    for sid, text in screens:
        assert c.follow(text) == expected(video, sid), "screen %s" % sid


@pytest.mark.parametrize("video", RECORDINGS["builder"])
def test_builder_coach_opens_on_any_screen(coach, video):
    """The builder track opens where the player already is (a coach opened
    in the middle of the builder, or a page reloaded)."""
    for sid, text in recorded_screens(video):
        assert coach("builder").open_at_screen(text) == expected(video, sid), "screen %s" % sid


@pytest.mark.parametrize("track,video", CASES)
def test_builder_is_recognised_only_in_the_builder(track, video):
    for sid, text in recorded_screens(video):
        assert bool(BUILDER.search(text)) == (track == "builder"), "screen %s" % sid


def test_coach_and_page_use_the_same_builder_pattern():
    assert "BUILDER = /Nation Builder/" in (WEB / "coach.js").read_text()
    assert "/Nation Builder/.test(text)" in (WEB / "game.html").read_text()


def test_model_matches_coach_js():
    """conftest.Coach copies these rules of web/coach.js: change both."""
    js = (WEB / "coach.js").read_text()
    assert "for (var i = steps.length - 1; i >= 0; i--) if (steps[i].re.test(text))" in js
    assert "for (var i = stepIndex + 1; i < Math.min(stepIndex + 7, steps.length); i++)" in js
    assert "(i === stepIndex + 1 || steps[i].unique) && steps[i].re.test(text)" in js


def test_builder_keys_are_on_the_key_bar():
    """While the builder is open the phone key bar has its keys (letters of
    one choice, like the races, are buttons in the coach itself)."""
    html = (WEB / "game.html").read_text()
    bar = re.search(r'<div class="group builder" id="builder-keys" hidden>(.*?)</div>', html, re.S)
    assert bar, "builder key group missing from game.html"
    keys = {k.encode().decode("unicode_escape") for k in re.findall(r'data-key="([^"]*)"', bar.group(1))}
    assert set("jkhl?yn") | {" ", "\r", "\x1b", "\x7f"} <= keys


def test_coach_knows_the_named_keys():
    """A key button types its label (a letter, a number like 50), so a named
    key must be mapped by coach.js (KEY_INPUT) or shown as text ("password")."""
    js = (WEB / "coach.js").read_text()
    mapped = set(re.findall(r"(\w+):", re.search(r"KEY_INPUT = \{([^}]*)\}", js).group(1))) | {"password"}
    for track in TRACKS:
        for lang in LANGS:
            for step in load(steps_file(track, lang))["steps"]:
                for k in step["keys"]:
                    assert not (k.isalpha() and len(k) > 1) or k in mapped, "%s %s step %s: key %r" % (track, lang, step["id"], k)
