# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The game's nation builder, played for real, still shows the screens the
coach and the video were made from.

Records tools/tutorial/found-nation.steps.json again, on a copy of the
default world at turn 1 (the game's world is not touched), in the game container
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
def game():
    if not LOCAL:
        up = shutil.which("docker") and subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "conquer-local"], capture_output=True, text=True).stdout
        if (up or "").strip() != "true":
            pytest.skip("the game container conquer-local is not running, and RECORD_LOCAL is not set")
    yield
    game_sh("rm -rf " + WORLD)


def copy_world(turns):
    """The default world as installed, at turn 1, then `turns` turn updates
    later (the builder gives points for starting late after turn 1)."""
    run = game_sh("set -e; src=/opt/conquer/default-world; [ -d $src ] || src=/opt/conquer/lib; "
                  "rm -rf %(w)s; cp -a $src %(w)s; rm -f %(w)s/lockadd; "
                  "for h in /opt/conquer/share/help[0-5]; do [ -f $h ] && cp $h %(w)s/; done; "
                  "conqowner -d %(w)s -s \"$(id -u)\" > /dev/null; "
                  "i=0; while [ $i -lt %(t)d ]; do conqrun -x -d %(w)s > /dev/null; i=$((i + 1)); done"
                  % {"w": WORLD, "t": turns})
    assert run.returncode == 0, "cannot prepare the world: " + run.stderr
    return WORLD


@pytest.mark.parametrize("recording,turns", [("found-nation", 0), ("found-nation-late", 1)])
def test_builder_matches_the_recording(game, tmp_path, recording, turns):
    world = copy_world(turns)
    spec = load(TUTORIAL / ("%s.steps.json" % recording))
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
