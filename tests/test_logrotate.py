# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""setup-logrotate.sh keeps the site's Apache logs 7 days: it writes
/etc/logrotate.d/conquer-web, is idempotent, and keeps Debian's own apache2
rule from naming the same files (logrotate refuses duplicates)."""
import os
import shutil
import subprocess

import pytest

from conftest import ROOT

SETUP = ROOT / "setup-logrotate.sh"
LOGS = "/var/log/apache2"
STOCK = """/var/log/apache2/*.log {
\tdaily
\tmissingok
\trotate 14
\tcompress
\tdelaycompress
\tnotifempty
\tcreate 640 root adm
\tsharedscripts
\tpostrotate
\t\tif pgrep -f ^/usr/sbin/apache2 > /dev/null; then
\t\t\tinvoke-rc.d apache2 reload 2>&1 | logger -t apache2.logrotate
\t\tfi
\tendscript
}
"""


def run_setup(tmp_path):
    env = dict(os.environ, LOGROTATE_DIR=str(tmp_path / "logrotate.d"), LOG_DIR=LOGS, SKIP_SERVICE="1")
    (tmp_path / "logrotate.d").mkdir(exist_ok=True)
    return subprocess.run(["bash", str(SETUP)], env=env, capture_output=True, text=True, timeout=30)


def test_the_rule_keeps_seven_days_and_reloads_apache(tmp_path):
    out = run_setup(tmp_path)
    assert out.returncode == 0, out.stderr + out.stdout
    rule = (tmp_path / "logrotate.d" / "conquer-web").read_text()
    assert rule.count("%s/conquer_*.log {" % LOGS) == 1
    words = [l.strip() for l in rule.splitlines()]
    for want in ("daily", "rotate 7", "compress", "delaycompress", "missingok", "notifempty", "create 640 root adm", "sharedscripts", "postrotate", "endscript"):
        assert want in words, want
    # the reload Debian's apache2 rule does
    assert "invoke-rc.d apache2 reload" in rule and "pgrep -f ^/usr/sbin/apache2" in rule


def test_it_is_idempotent(tmp_path):
    (tmp_path / "logrotate.d").mkdir()
    (tmp_path / "logrotate.d" / "apache2").write_text(STOCK)
    assert "(changed)" in run_setup(tmp_path).stdout
    files = {p.name: (p.read_text(), p.stat().st_mtime_ns) for p in (tmp_path / "logrotate.d").iterdir()}
    again = run_setup(tmp_path)
    assert again.returncode == 0 and "(changed)" not in again.stdout
    assert files == {p.name: (p.read_text(), p.stat().st_mtime_ns) for p in (tmp_path / "logrotate.d").iterdir()}
    assert sorted(files) == ["apache2", "conquer-web"], "no stray files in the logrotate directory"


@pytest.mark.skipif(not shutil.which("logrotate"), reason="logrotate is not installed")
def test_logrotate_accepts_both_rules_and_names_each_log_once(tmp_path):
    (tmp_path / "logrotate.d").mkdir()
    (tmp_path / "logrotate.d" / "apache2").write_text(STOCK.replace(LOGS, str(tmp_path / "log")))
    logs = tmp_path / "log"
    logs.mkdir()
    for name in ("conquer_ssl_access.log", "conquer_ssl_error.log", "conquer_login.log", "conquer_recover.log",
                 "conquer_access.log", "access.log", "error.log", "other_vhost_access.log"):
        (logs / name).write_text("x\n")
    env = dict(os.environ, LOGROTATE_DIR=str(tmp_path / "logrotate.d"), LOG_DIR=str(logs), SKIP_SERVICE="1")
    assert subprocess.run(["bash", str(SETUP)], env=env, capture_output=True, text=True, timeout=30).returncode == 0
    main = tmp_path / "main.conf"
    main.write_text("include %s\n" % (tmp_path / "logrotate.d"))
    out = subprocess.run(["logrotate", "-d", "-s", str(tmp_path / "state"), str(main)], capture_output=True, text=True, timeout=30)
    text = out.stdout + out.stderr
    assert "duplicate" not in text and "error:" not in text, text
    # each conquer log is handled once, with 7 rotations; the others keep Debian's 14
    sections = text.split("rotating pattern:")
    seven = [s for s in sections if "(7 rotations)" in s]
    fourteen = [s for s in sections if "(14 rotations)" in s]
    assert len(seven) == 1 and len(fourteen) == 1, text
    for name in ("conquer_ssl_access.log", "conquer_ssl_error.log", "conquer_login.log", "conquer_recover.log", "conquer_access.log"):
        assert "considering log %s" % (logs / name) in seven[0]
        assert "considering log %s" % (logs / name) not in fourteen[0]
    for name in ("access.log", "error.log", "other_vhost_access.log"):
        assert "considering log %s" % (logs / name) in fourteen[0], name


def test_deploy_and_update_run_the_setup():
    assert "setup-logrotate.sh" in (ROOT / "update-vps.sh").read_text()
    assert "setup-logrotate.sh" in (ROOT / "deploy-to-vps.sh").read_text()
