# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The narrated videos: every shot has a screen, every language says the same."""
import pytest

from conftest import TRACKS, TUTORIAL, load, steps_file

NARRATION = TUTORIAL / "narration"
VIDEOS = {"first-turn": sorted(NARRATION.glob("*.json")),
          "found-nation": sorted((NARRATION / "found-nation").glob("*.json")),
          "trailer": sorted((NARRATION / "trailer").glob("*.json"))}
# The trailer shows screens of the first turn
SOURCE = {"trailer": "first-turn"}
CAPTIONS = {"keys", "look", "intro_title", "intro_sub", "outro_title", "outro_sub", "password", "space"}


CASES = [pytest.param(video, f, id="%s-%s" % (video, f.stem)) for video, files in VIDEOS.items() for f in files]


@pytest.mark.parametrize("video,path", CASES)
def test_segments_show_recorded_screens(video, path):
    source = SOURCE.get(video, video)
    screens = {s["id"] for s in load(TUTORIAL / ("%s.screens.json" % source))}
    track = next(t for t, v in TRACKS.items() if v == source)
    steps = {s["id"] for s in load(steps_file(track))["steps"]}
    for seg in load(path)["segments"]:
        if seg["screen"] in ("intro", "outro"):
            continue
        assert seg["screen"] in screens, seg["screen"]
        if "caption" in seg:
            assert seg["caption"].strip()
        else:
            assert seg.get("step", seg["screen"]) in steps, seg["screen"]
        assert seg["text"].strip()


@pytest.mark.parametrize("video,path", CASES)
def test_languages_match_english(video, path):
    english = load(path.with_name("en.json"))
    narration = load(path)
    assert [s["screen"] for s in narration["segments"]] == [s["screen"] for s in english["segments"]]
    assert [s.get("keys") for s in narration["segments"]] == [s.get("keys") for s in english["segments"]]
    assert ["caption" in s for s in narration["segments"]] == ["caption" in s for s in english["segments"]]
    assert CAPTIONS <= set(narration["captions"])


@pytest.mark.parametrize("path", VIDEOS["found-nation"] + VIDEOS["trailer"], ids=lambda p: "%s-%s" % (p.parent.name, p.stem))
def test_other_videos_have_a_narrator(path):
    """found-nation/ and trailer/<language>.json borrow the voice of <language>.json."""
    assert "voice" in load(NARRATION / path.name)
