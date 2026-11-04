# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The terminal menu's limits (conquer/scripts/menu.sh): an account that is
not approved gets no terminal, a second terminal of one account is turned
away, and a menu nobody types at closes itself. Runs the real menu on a
throwaway prefix, with the game replaced by nothing (the menu never starts
it here)."""
import os
import subprocess
import time

import pytest

from conftest import ROOT

MENU = ROOT / "conquer" / "scripts" / "menu.sh"


@pytest.fixture
def prefix(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "run").mkdir()
    (tmp_path / "lib" / ".players").write_text("pending:?\nplayer:Rome\nboss:*\n")
    # The helpers the banner calls: none of them is needed here
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("conquer-ready", "conquer-status", "conquer-next-turn"):
        (bin_dir / name).write_text("#!/bin/sh\nexit 1\n")
        (bin_dir / name).chmod(0o755)
    return tmp_path


def start(prefix, account, lang="en", idle="900"):
    env = dict(os.environ,
               CONQUER_PREFIX=str(prefix), CONQUER_RUN=str(prefix / "run"),
               CONQUER_I18N_LIB=str(ROOT / "conquer" / "scripts" / "i18n.sh"),
               CONQUER_I18N_DIR=str(ROOT / "conquer" / "i18n"),
               TTYD_USER=account, MENU_IDLE_TIMEOUT=idle, TERM="dumb",
               PATH="%s:%s" % (prefix / "bin", os.environ["PATH"]))
    return subprocess.Popen(["bash", str(MENU), lang], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=env)


def finish(proc, timeout=15):
    out, err = proc.communicate(timeout=timeout)
    return proc.returncode, out + err


def test_pending_account_gets_no_terminal(prefix):
    code, out = finish(start(prefix, "pending"))
    assert code == 0
    assert "pending" in out and "Choose an option" not in out


def test_pending_message_is_localized(prefix):
    code, out = finish(start(prefix, "pending", lang="es"))
    assert code == 0 and "pendiente" in out


def test_second_terminal_of_one_account_is_turned_away(prefix):
    first = start(prefix, "player")
    try:
        deadline = time.time() + 10
        while not list((prefix / "run").glob("session-*.lock")) and time.time() < deadline:
            time.sleep(0.05)
        time.sleep(0.5)  # the first menu is at its prompt
        code, out = finish(start(prefix, "player"))
        assert code == 0
        assert "already open" in out and "Choose an option" not in out
        # Another account is not affected
        other = start(prefix, "boss")
        time.sleep(1)
        assert other.poll() is None
        finish(other)
    finally:
        assert finish(first)[0] == 0
    # The place is free again once the first menu has gone
    again = start(prefix, "player")
    time.sleep(1)
    assert again.poll() is None
    finish(again)


def test_second_terminal_message_is_localized(prefix):
    first = start(prefix, "player")
    try:
        time.sleep(1.5)
        code, out = finish(start(prefix, "player", lang="de"))
        assert code == 0 and "schon in einem anderen Fenster" in out
    finally:
        finish(first)


def test_idle_menu_closes_itself(prefix):
    proc = start(prefix, "player", idle="1")
    started = time.time()
    code = proc.wait(timeout=10)  # stdin stays open: only the timer can end it
    out = proc.stdout.read()
    proc.stdin.close()
    assert code == 0
    assert time.time() - started < 10
    assert "without a key" in out
