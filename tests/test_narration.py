# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The narrated videos: every shot has a screen, every language says the same."""
import pytest

from conftest import TRACKS, TUTORIAL, load, steps_file

NARRATION = TUTORIAL / "narration"
VIDEOS = {"first-turn": sorted(NARRATION.glob("*.json")),
          "found-nation": sorted((NARRATION / "found-nation").glob("*.json"))}
CAPTIONS = {"keys", "look", "intro_title", "intro_sub", "outro_title", "outro_sub", "password", "space"}


CASES = [pytest.param(video, f, id="%s-%s" % (video, f.stem)) for video, files in VIDEOS.items() for f in files]


@pytest.mark.parametrize("video,path", CASES)
def test_segments_show_recorded_screens(video, path):
    screens = {s["id"] for s in load(TUTORIAL / ("%s.screens.json" % video))}
    track = next(t for t, v in TRACKS.items() if v == video)
    steps = {s["id"] for s in load(steps_file(track))["steps"]}
    for seg in load(path)["segments"]:
        if seg["screen"] in ("intro", "outro"):
            continue
        assert seg["screen"] in screens, seg["screen"]
        assert seg.get("step", seg["screen"]) in steps, seg["screen"]
        assert seg["text"].strip()


@pytest.mark.parametrize("video,path", CASES)
def test_languages_match_english(video, path):
    english = load(path.with_name("en.json"))
    narration = load(path)
    assert [s["screen"] for s in narration["segments"]] == [s["screen"] for s in english["segments"]]
    assert [s.get("keys") for s in narration["segments"]] == [s.get("keys") for s in english["segments"]]
    assert CAPTIONS <= set(narration["captions"])


@pytest.mark.parametrize("path", VIDEOS["found-nation"], ids=lambda p: p.stem)
def test_builder_video_has_a_narrator(path):
    """found-nation/<language>.json borrows the voice of <language>.json."""
    assert "voice" in load(NARRATION / path.name)
