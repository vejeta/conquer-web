# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""conquer-signup expire: requests nobody decided in N days go away with
their accounts (the gate runs it once a day). Runs the real script on a
throwaway prefix, with a stand-in for htpasswd."""
import os
import stat
import subprocess
import time

import pytest

from conftest import ROOT

SIGNUP = ROOT / "conquer" / "scripts" / "signup.sh"
DAY = 86400


@pytest.fixture
def world(tmp_path):
    prefix = tmp_path / "prefix"
    (prefix / "lib").mkdir(parents=True)
    (prefix / "auth").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "htpasswd"
    fake.write_text('#!/bin/sh\ncat > /dev/null\necho "$4:fake-hash"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, CONQUER_PREFIX=str(prefix), CONQUER_RUN=str(tmp_path / "run"),
               PATH="%s:%s" % (bin_dir, os.environ["PATH"]))
    (prefix / "auth" / "htpasswd").write_text("")

    class World:
        lib = prefix / "lib"
        htpasswd = prefix / "auth" / "htpasswd"

        def signup(self, *args, password="long enough\n"):
            return subprocess.run(["bash", str(SIGNUP), *args], input=password, env=env,
                                  capture_output=True, text=True, timeout=30)

        def age(self, account, days):
            """Make the request of account days days old."""
            lines = []
            for line in (self.lib / ".requests").read_text().splitlines():
                f = line.split("\t")
                if f[0] == account:
                    f[1] = str(int(time.time()) - int(days * DAY))
                lines.append("\t".join(f))
            (self.lib / ".requests").write_text("\n".join(lines) + "\n")

        def read(self, name):
            path = self.lib / name if name != "htpasswd" else self.htpasswd
            return path.read_text() if path.exists() else ""
    return World()


def test_expire_removes_old_pending_accounts_only(world):
    for name in ("old", "recent", "approved"):
        assert world.signup("request", name, "%s@example.org" % name, "hi", "en").returncode == 0
    assert world.signup("approve", "approved").returncode == 0
    world.age("old", 31)
    world.age("recent", 29)
    out = world.signup("expire", "30", password="")
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["old"]
    assert "old:" not in world.read("htpasswd") and "old" not in world.read(".players").split()
    assert not any(l.startswith("old\t") for l in world.read(".requests").splitlines())
    # The others are untouched
    assert "recent:fake-hash" in world.read("htpasswd")
    assert "recent:?" in world.read(".players")
    assert "recent\t" in world.read(".requests")
    assert "approved:+" in world.read(".players") and "approved:fake-hash" in world.read("htpasswd")


def test_expire_never_touches_an_approved_account_with_a_stale_line(world):
    assert world.signup("request", "kept", "", "", "en").returncode == 0
    world.age("kept", 90)
    # Approved by hand, leaving the request line behind
    players = world.read(".players").replace("kept:?", "kept:+")
    (world.lib / ".players").write_text(players)
    out = world.signup("expire", "30", password="")
    assert out.returncode == 0 and out.stdout.strip() == ""
    assert "kept:+" in world.read(".players") and "kept:fake-hash" in world.read("htpasswd")
    assert world.read(".requests").strip() == ""


def test_expire_without_requests_or_with_bad_days(world):
    assert world.signup("expire", "30", password="").returncode == 0
    assert world.signup("expire", "x", password="").returncode == 1
    assert world.signup("expire", "0", password="").returncode == 1
    assert world.signup("expire", "-3", password="").returncode == 1
