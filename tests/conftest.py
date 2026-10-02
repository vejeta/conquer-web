# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared helpers: the repository layout and a Python model of the coach
(web/coach.js), checked against the recorded game screens."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
TUTORIAL = ROOT / "tools" / "tutorial"
LANGS = sorted(p.stem for p in (WEB / "i18n").glob("*.json"))
# The coach's tracks: steps file (built by build.py), recorded screens
TRACKS = {"first-turn": "first-turn", "builder": "found-nation"}
# Same as BUILDER in web/coach.js and the key bar in web/game.html
BUILDER = re.compile(r"Nation Builder")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def steps_file(track, lang="en"):
    base = TRACKS[track]
    return WEB / "tutorial" / ("%s.json" % base if lang == "en" else "%s.%s.json" % (base, lang))


def screen_text(screen):
    """The 80x24 text of a recorded screen (runs of [text, attributes])."""
    return "\n".join("".join(run[0] for run in line) for line in screen)


def recorded_screens(video):
    return [(s["id"], screen_text(s["screen"])) for s in load(TUTORIAL / ("%s.screens.json" % video))]


class Coach:
    """What web/coach.js does with a track's steps."""

    def __init__(self, steps):
        self.steps = steps
        self.re = [re.compile(s["detect"]) for s in steps]
        self.unique = [sum(o["detect"] == s["detect"] for o in steps) == 1 for s in steps]
        self.index = 0

    def open_at_screen(self, text):
        """loadTrack(name, 'screen'): the last step whose screen shows."""
        self.index = 0
        for i in range(len(self.steps) - 1, -1, -1):
            if self.re[i].search(text):
                self.index = i
                break
        return self.id

    def follow(self, text):
        """The interval: the next step, or an unmistakable one of the next six."""
        for i in range(self.index + 1, min(self.index + 7, len(self.steps))):
            if (i == self.index + 1 or self.unique[i]) and self.re[i].search(text):
                self.index = i
                break
        return self.id

    @property
    def id(self):
        return self.steps[self.index]["id"]


@pytest.fixture
def coach():
    return lambda track, lang="en": Coach(load(steps_file(track, lang))["steps"])
