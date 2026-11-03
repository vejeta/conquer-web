# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""offsite-backup.sh: which copies the target keeps, and a copy sent to a
directory (no network; the rsync and SSH targets use the same selection)."""
import os
import shutil
import subprocess

import pytest

from conftest import ROOT

SCRIPT = str(ROOT / "offsite-backup.sh")
NAMES = [f"conquer-h-2026010{d}-040000.tar.gz" for d in range(1, 6)]


def run(*args, stdin="", env=None):
    full = dict(os.environ, OFFSITE_TEST="1", **(env or {}))
    return subprocess.run([SCRIPT, *args], input=stdin, capture_output=True, text=True, env=full)


def test_select_old_keeps_the_newest_by_name():
    names = NAMES + ["conquer-h-20260101-040000.tar.gz.enc", "notes.txt", ".", "conquer-x*.tar.gz", "conquer-h-1.tar.gz.old"]
    out = run("--select-old", "3", stdin="\n".join(names) + "\n").stdout.split()
    assert out == ["conquer-h-20260102-040000.tar.gz", "conquer-h-20260101-040000.tar.gz.enc", "conquer-h-20260101-040000.tar.gz"]
    assert run("--select-old", "9", stdin="\n".join(NAMES)).stdout == ""


def test_select_old_only_in_test_mode():
    full = {k: v for k, v in os.environ.items() if k != "OFFSITE_TEST"}
    done = subprocess.run([SCRIPT, "--select-old", "3"], input="", capture_output=True, text=True, env=full)
    assert done.returncode != 0


@pytest.mark.skipif(not shutil.which("openssl"), reason="needs openssl")
def test_copy_to_a_directory_prunes_old_copies(tmp_path):
    lib = tmp_path / "data" / "lib"
    lib.mkdir(parents=True)
    (lib / "nations").write_text("god\n")
    target = tmp_path / "target"
    target.mkdir()
    for n in NAMES:
        (target / n).write_text("old")
    (target / "keep.txt").write_text("not ours")
    (tmp_path / "backup.env").write_text(f"BACKUP_TARGET={target}\nBACKUP_KEEP=3\n")
    done = run(env={
        "OFFSITE_CONFIG": str(tmp_path / "backup.env"), "OFFSITE_SETTINGS": str(tmp_path / "none"),
        "OFFSITE_DATA_DIR": str(tmp_path / "data"), "OFFSITE_LOCAL_DIR": str(tmp_path / "local"),
        "CONTAINER": "no-such-container", "HTPASSWD_FILE": str(tmp_path / "none"),
    })
    assert done.returncode == 0, done.stdout + done.stderr
    left = sorted(p.name for p in target.iterdir())
    assert "keep.txt" in left and len(left) == 4
    assert NAMES[-1] in left and NAMES[-2] in left and NAMES[0] not in left
    assert len(list((tmp_path / "local").iterdir())) == 1


@pytest.mark.skipif(not shutil.which("openssl"), reason="needs openssl")
def test_decrypt_a_relative_path_from_where_it_is_typed(tmp_path):
    pw = tmp_path / "pw"
    pw.write_text("secret\n")
    cfg = tmp_path / "backup.env"
    cfg.write_text(f'BACKUP_PASSWORD_FILE="{pw}"\n')
    (tmp_path / "copy.tar.gz").write_bytes(b"payload")
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", f"file:{pw}",
                    "-in", "copy.tar.gz", "-out", "copy.tar.gz.enc"], cwd=tmp_path, check=True)
    (tmp_path / "copy.tar.gz").unlink()
    full = dict(os.environ, OFFSITE_TEST="1", OFFSITE_CONFIG=str(cfg))
    done = subprocess.run([SCRIPT, "--decrypt", "copy.tar.gz.enc"], cwd=tmp_path, capture_output=True, text=True, env=full)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (tmp_path / "copy.tar.gz").read_bytes() == b"payload"
    missing = subprocess.run([SCRIPT, "--decrypt", "nope.enc"], cwd=tmp_path, capture_output=True, text=True, env=full)
    assert missing.returncode != 0 and "No such file" in missing.stdout
