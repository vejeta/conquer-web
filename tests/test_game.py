# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The game's nation builder, played for real, still shows the screens the
coach and the video were made from.

Records tools/tutorial/found-nation.steps.json again, on a copy of the
world (the world itself is not touched), in the game container
conquer-local, or with RECORD_LOCAL=1 in a local /opt/conquer as the user
conquer. record.py stops when a screen is not the expected one; the new
screens must then move the coach step by step as the recorded ones do.
Needs the pyte Python module. Not for a live server: when it is done,
record.py stops every conquer and conqrun running there."""
import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import TUTORIAL, Coach, load, screen_text, steps_file

pytestmark = pytest.mark.game
pytest.importorskip("pyte")
LOCAL = os.environ.get("RECORD_LOCAL") == "1"
WORLD = "/tmp/conquer-test-world"


def game_sh(script):
    if LOCAL:
        cmd = ["su", "conquer", "-s", "/bin/sh", "-c", "PATH=/opt/conquer/bin:$PATH; " + script]
    else:
        cmd = ["docker", "exec", "-u", "conquer", "conquer-local", "sh", "-c", script]
    return subprocess.run(cmd, capture_output=True, text=True)


@pytest.fixture(scope="module")
def world():
    if not LOCAL and not shutil.which("docker"):
        pytest.skip("no docker, and RECORD_LOCAL is not set")
    run = game_sh("set -e; rm -rf %(w)s; cp -a /opt/conquer/lib %(w)s; rm -f %(w)s/lockadd; "
                  "conqowner -d %(w)s -s \"$(id -u)\" > /dev/null" % {"w": WORLD})
    if run.returncode:
        pytest.skip("no game to play: " + run.stderr.strip())
    yield WORLD
    game_sh("rm -rf " + WORLD)


def test_builder_matches_the_recording(world, tmp_path):
    spec = load(TUTORIAL / "found-nation.steps.json")
    spec["cmd"] = "conqrun -a -d " + world
    steps = tmp_path / "steps.json"
    steps.write_text(json.dumps(spec))
    run = subprocess.run([sys.executable, str(TUTORIAL / "record.py"), str(steps),
                          str(tmp_path / "cast"), str(tmp_path / "screens.json")],
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr[-3000:]

    coach = Coach(load(steps_file("builder"))["steps"])
    screens = [(s["id"], screen_text(s["screen"])) for s in load(tmp_path / "screens.json")]
    coach.open_at_screen(screens[0][1])
    for sid, text in screens:
        assert coach.follow(text) == ("points" if sid == "treasury" else sid), "screen %s" % sid
