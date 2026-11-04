# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""conquer-signup passwd / recovery-init / recovery-renew / reset: the password
change, the recovery code (only its bcrypt hash is kept, in lib/.recovery,
mode 600) and the reset with it. Runs the real script with the real htpasswd
on a throwaway prefix."""
import os
import re
import shutil
import stat
import subprocess

import pytest

from conftest import ROOT

SIGNUP = ROOT / "conquer" / "scripts" / "signup.sh"
CODE = "K7QM-3XPA-9RTD"
CODE2 = "ABCD-EFGH-JKMN"
CODE3 = "PQRS-TUVW-XYZ2"

pytestmark = pytest.mark.skipif(not shutil.which("htpasswd"), reason="htpasswd (apache2-utils) is not installed")


@pytest.fixture
def world(tmp_path):
    prefix = tmp_path / "prefix"
    (prefix / "lib").mkdir(parents=True)
    (prefix / "auth").mkdir()
    env = dict(os.environ, CONQUER_PREFIX=str(prefix), CONQUER_RUN=str(tmp_path / "run"))
    (prefix / "auth" / "htpasswd").write_text("")

    class World:
        lib = prefix / "lib"
        htpasswd = prefix / "auth" / "htpasswd"
        recovery = prefix / "lib" / ".recovery"

        def signup(self, *args, stdin=""):
            return subprocess.run(["bash", str(SIGNUP), *args], input=stdin, env=env,
                                  capture_output=True, text=True, timeout=60)

        def can_sign_in(self, account, password):
            run = subprocess.run(["htpasswd", "-vi", str(self.htpasswd), account], input=password + "\n",
                                 capture_output=True, text=True)
            return run.returncode == 0

        def make(self, account, password="first password", approved=True):
            assert self.signup("request", account, "en", stdin=password + "\n").returncode == 0
            if approved:
                assert self.signup("approve", account).returncode == 0
    return World()


def test_passwd_needs_the_current_password(world):
    world.make("ana")
    bad = world.signup("passwd", "ana", stdin="not it\nsecond password\n")
    assert bad.returncode == 2
    assert world.can_sign_in("ana", "first password") and not world.can_sign_in("ana", "second password")
    ok = world.signup("passwd", "ana", stdin="first password\nsecond password\n")
    assert ok.returncode == 0, ok.stderr
    assert world.can_sign_in("ana", "second password") and not world.can_sign_in("ana", "first password")


def test_passwd_leaves_the_other_accounts_and_the_line_order_alone(world):
    for name in ("ana", "bob", "cy"):
        world.make(name, password="pw-of-" + name)
    before = world.htpasswd.read_text().splitlines()
    assert world.signup("passwd", "bob", stdin="pw-of-bob\nbrand new one\n").returncode == 0
    after = world.htpasswd.read_text().splitlines()
    assert [l.split(":")[0] for l in after] == ["ana", "bob", "cy"]
    assert after[0] == before[0] and after[2] == before[2] and after[1] != before[1]
    assert world.can_sign_in("ana", "pw-of-ana") and world.can_sign_in("cy", "pw-of-cy")
    assert all(l.split(":", 1)[1].startswith("$2") for l in after), "bcrypt hashes"


def test_passwd_refuses_short_passwords_and_unknown_accounts(world):
    world.make("ana")
    assert world.signup("passwd", "ana", stdin="first password\nshort\n").returncode == 1
    assert world.can_sign_in("ana", "first password")
    assert world.signup("passwd", "nobody", stdin="x\nlong enough pw\n").returncode == 3
    assert world.signup("passwd", "-v", stdin="x\nlong enough pw\n").returncode == 3
    assert world.signup("passwd", "ana", stdin="").returncode == 1


def test_recovery_init_stores_only_a_hash_with_mode_600(world):
    world.make("ana")
    out = world.signup("recovery-init", "ana", stdin=CODE + "\n")
    assert out.returncode == 0, out.stderr
    text = world.recovery.read_text()
    assert text.startswith("ana:$2") and CODE not in text and CODE.replace("-", "") not in text
    assert stat.S_IMODE(world.recovery.stat().st_mode) == 0o600
    # Only the first one is made by init; the code stays the same
    again = world.signup("recovery-init", "ana", stdin=CODE2 + "\n")
    assert again.returncode == 2
    assert world.recovery.read_text() == text
    # No stray temporary files
    assert sorted(p.name for p in world.lib.iterdir() if p.name.startswith(".recovery")) == [".recovery"]


def test_recovery_init_waits_for_approval_and_checks_the_code_shape(world):
    world.make("ana", approved=False)
    assert world.signup("recovery-init", "ana", stdin=CODE + "\n").returncode == 3
    assert not world.recovery.exists()
    assert world.signup("approve", "ana").returncode == 0
    for bad in ("", "K7QM3XPA9RTD", "k7qm-3xpa-9rtd", "K7QM-3XPA-9RT0", "K7QM-3XPA-9RTD-X", "$(id)"):
        assert world.signup("recovery-init", "ana", stdin=bad + "\n").returncode == 1, bad
    assert world.signup("recovery-init", "nobody", stdin=CODE + "\n").returncode == 3
    assert world.signup("recovery-init", "ana", stdin=CODE + "\n").returncode == 0


def test_reset_with_the_code_sets_the_password_and_voids_the_code(world):
    world.make("ana")
    world.make("bob", password="bob's password")
    assert world.signup("recovery-init", "ana", stdin=CODE + "\n").returncode == 0
    assert world.signup("recovery-init", "bob", stdin=CODE2 + "\n").returncode == 0
    bob_hash = [l for l in world.recovery.read_text().splitlines() if l.startswith("bob:")][0]
    bad = world.signup("reset", "ana", stdin=CODE2 + "\nbrand new password\n" + CODE3 + "\n")
    assert bad.returncode == 2, "bob's code does not open ana's account"
    assert world.can_sign_in("ana", "first password")
    ok = world.signup("reset", "ana", stdin=CODE + "\nbrand new password\n" + CODE3 + "\n")
    assert ok.returncode == 0, ok.stderr
    assert world.can_sign_in("ana", "brand new password") and not world.can_sign_in("ana", "first password")
    assert world.can_sign_in("bob", "bob's password")
    # The used code is void, the new one works, bob's entry is untouched
    assert world.signup("reset", "ana", stdin=CODE + "\nanother new password\n" + CODE2 + "\n").returncode == 2
    assert bob_hash in world.recovery.read_text().splitlines()
    assert CODE3 not in world.recovery.read_text()
    assert world.signup("reset", "ana", stdin=CODE3 + "\nanother new password\n" + CODE2 + "\n").returncode == 0
    assert world.can_sign_in("ana", "another new password")


def test_reset_gives_no_hint_whether_the_account_exists(world):
    world.make("ana")   # no code yet
    for account in ("ana", "nobody", "-v"):
        out = world.signup("reset", account, stdin=CODE + "\nbrand new password\n" + CODE2 + "\n")
        assert out.returncode == 2, account
    assert world.can_sign_in("ana", "first password")


def test_reset_refuses_a_short_password_without_touching_anything(world):
    world.make("ana")
    world.signup("recovery-init", "ana", stdin=CODE + "\n")
    before = (world.htpasswd.read_text(), world.recovery.read_text())
    assert world.signup("reset", "ana", stdin=CODE + "\nshort\n" + CODE2 + "\n").returncode == 1
    assert (world.htpasswd.read_text(), world.recovery.read_text()) == before


def test_recovery_renew_needs_the_password_and_voids_the_old_code(world):
    world.make("ana")
    world.signup("recovery-init", "ana", stdin=CODE + "\n")
    assert world.signup("recovery-renew", "ana", stdin="wrong\n" + CODE2 + "\n").returncode == 2
    assert world.signup("recovery-renew", "ana", stdin="first password\n" + CODE2 + "\n").returncode == 0
    assert world.signup("reset", "ana", stdin=CODE + "\nbrand new password\n" + CODE3 + "\n").returncode == 2
    assert world.signup("reset", "ana", stdin=CODE2 + "\nbrand new password\n" + CODE3 + "\n").returncode == 0
    assert stat.S_IMODE(world.recovery.stat().st_mode) == 0o600


def test_removing_an_account_forgets_its_code(world):
    world.make("ana")
    world.signup("recovery-init", "ana", stdin=CODE + "\n")
    # An old version left the hash behind when an account was removed by hand;
    # a new account of the same name does not inherit it
    (world.htpasswd).write_text("")
    (world.lib / ".players").write_text("")
    world.make("ana", password="somebody else")
    assert not re.search(r"^ana:", world.recovery.read_text(), re.M)
    assert world.signup("reset", "ana", stdin=CODE + "\nbrand new password\n" + CODE2 + "\n").returncode == 2


def test_manage_players_keeps_the_recovery_file_in_step(world, tmp_path):
    world.make("ana")
    world.make("bob", password="bob's password")
    world.signup("recovery-init", "ana", stdin=CODE + "\n")
    world.signup("recovery-init", "bob", stdin=CODE2 + "\n")
    env = dict(os.environ, HTPASSWD_FILE=str(world.htpasswd), PLAYERS_FILE=str(world.lib / ".players"),
               REQUESTS_FILE=str(world.lib / ".requests"), RECOVERY_FILE=str(world.recovery),
               INVITES_FILE=str(world.lib / ".invites"))

    def manage(*args):
        return subprocess.run(["bash", str(ROOT / "manage-players.sh"), *args], env=env, capture_output=True, text=True, timeout=60)
    assert manage("rename", "ana", "ann").returncode == 0
    assert world.recovery.read_text().startswith("ann:") or "\nann:" in world.recovery.read_text()
    assert world.signup("reset", "ann", stdin=CODE + "\nbrand new password\n" + CODE3 + "\n").returncode == 0
    assert manage("remove", "bob").returncode == 0
    assert "bob:" not in world.recovery.read_text()
