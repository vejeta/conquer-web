# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Failed sign-ins and fail2ban: the filter matches the log line Apache writes
for a wrong password (and nothing else), the jail has the agreed numbers, the
setup script is idempotent and keeps the administrator's address out of bans,
and the old request-counting jail is gone."""
import configparser
import os
import re
import shutil
import subprocess

import pytest

from conftest import ROOT

FILTER = ROOT / "vps" / "fail2ban" / "conquer-login.conf"
JAIL = ROOT / "vps" / "fail2ban" / "conquer-login.jail"
SETUP = ROOT / "setup-fail2ban.sh"
IP = r"(?P<host>\d{1,3}(?:\.\d{1,3}){3}|[0-9a-fA-F:]+)"


def failregex():
    cfg = configparser.ConfigParser(interpolation=None, strict=False)
    cfg.read(FILTER, encoding="utf-8")
    lines = [l.strip() for l in cfg["Definition"]["failregex"].splitlines() if l.strip()]
    return [re.compile(l.replace("<HOST>", IP)) for l in lines]


def hit(line):
    """The address fail2ban would count, or None."""
    for rx in failregex():
        m = rx.search(line)
        if m:
            return m.group("host")
    return None


def login_line(ip="203.0.113.9", request="POST /login/do HTTP/1.1", status=302, location="/login.html?failed=1&"):
    return '%s - - [04/Nov/2026:10:00:00 +0000] "%s" %s "%s"' % (ip, request, status, location)


GOOD = [
    # What Apache writes (checked against a real Apache 2.4 with mod_auth_form)
    login_line(),
    login_line(request="POST /login/do?next=%2Fplay%2F HTTP/1.1", location="/login.html?failed=1&next=%2Fplay%2F"),
    login_line(request="POST /login/long HTTP/1.1", location="/login.html?failed=1&"),
    login_line(request="POST /login/long?next=%2Fadmin%2F HTTP/1.1", location="https://conquer.example/login.html?failed=1&next=%2Fadmin%2F"),
    login_line(ip="2001:db8::7"),
]
BAD = [
    # A good sign-in goes on to the game
    login_line(location="/play/"),
    login_line(request="POST /login/long HTTP/1.1", location="/admin/"),
    # No redirect, or not a sign-in post
    login_line(status=200, location="-"),
    login_line(status=403, location="-"),
    login_line(request="GET /login/do HTTP/1.1"),
    login_line(request="POST /login/other HTTP/1.1"),
    login_line(request="POST /logout HTTP/1.1", location="/login.html?failed=1&"),
    login_line(request="POST /play/ HTTP/1.1", location="/login.html?failed=1&"),
    # The page itself, and the sign-in page with failed=1 elsewhere in the log
    login_line(request="GET /login.html?failed=1 HTTP/1.1", status=200, location="-"),
    # The failure text must be in the Location, not smuggled in the request
    login_line(location="-", request='POST /login/do?x=login.html?failed=1 HTTP/1.1'),
    "",
    "garbage",
]


@pytest.mark.parametrize("line", GOOD)
def test_filter_matches_a_failed_sign_in(line):
    assert hit(line) == line.split(" ")[0]


@pytest.mark.parametrize("line", BAD)
def test_filter_ignores_everything_else(line):
    assert hit(line) is None


def test_the_address_is_the_first_field_so_text_in_the_log_cannot_name_another():
    line = login_line(ip="203.0.113.9", request='POST /login/do?ip=198.51.100.1 HTTP/1.1')
    assert hit(line) == "203.0.113.9"


def test_filter_agrees_with_fail2ban_when_it_is_installed(tmp_path):
    tool = shutil.which("fail2ban-regex")
    if not tool:
        pytest.skip("fail2ban-regex is not installed")
    log = tmp_path / "sample.log"
    log.write_text("\n".join(GOOD[:4] + BAD[:6]) + "\n")
    out = subprocess.run([tool, str(log), str(FILTER)], capture_output=True, text=True, timeout=60).stdout
    assert re.search(r"Failregex: 4 total", out), out


def jail():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(JAIL, encoding="utf-8")
    return cfg["conquer-login"]


def test_jail_numbers():
    j = jail()
    assert j["filter"] == "conquer-login"
    assert j["maxretry"] == "8" and j["findtime"] == "10m" and j["bantime"] == "1h"
    assert j["logpath"] == "/var/log/apache2/conquer_login.log"


def run_setup(tmp_path, **env):
    full = dict(os.environ, F2B_DIR=str(tmp_path / "f2b"), LOG_DIR=str(tmp_path / "log"),
                SKIP_APT="1", SKIP_SERVICE="1")
    full.pop("ADMIN_IP", None)
    full.update(env)
    (tmp_path / "log").mkdir(exist_ok=True)
    return subprocess.run(["bash", str(SETUP)], env=full, capture_output=True, text=True, timeout=30)


def test_setup_installs_the_jail_and_is_idempotent(tmp_path):
    first = run_setup(tmp_path)
    assert first.returncode == 0, first.stderr + first.stdout
    assert "(changed)" in first.stdout
    f2b = tmp_path / "f2b"
    assert (f2b / "filter.d" / "conquer-login.conf").read_text() == FILTER.read_text()
    text = (f2b / "jail.d" / "conquer-login.local").read_text()
    assert "ignoreip = 127.0.0.1/8 ::1\n" in text and "IGNORE_IPS" not in text
    assert (tmp_path / "log" / "conquer_login.log").exists()
    stamp = [(p, p.stat().st_mtime_ns) for p in f2b.rglob("*") if p.is_file()]
    second = run_setup(tmp_path)
    assert second.returncode == 0 and "(changed)" not in second.stdout
    assert stamp == [(p, p.stat().st_mtime_ns) for p in f2b.rglob("*") if p.is_file()]


def test_admin_ip_is_never_banned(tmp_path):
    assert run_setup(tmp_path, ADMIN_IP="203.0.113.7").returncode == 0
    text = (tmp_path / "f2b" / "jail.d" / "conquer-login.local").read_text()
    assert "ignoreip = 127.0.0.1/8 ::1 203.0.113.7\n" in text
    # Changing it rewrites the jail
    assert run_setup(tmp_path, ADMIN_IP="198.51.100.0/24").returncode == 0
    assert "198.51.100.0/24" in (tmp_path / "f2b" / "jail.d" / "conquer-login.local").read_text()


@pytest.mark.parametrize("bad", ["not an ip", "1.2.3.4; bantime = 0", "$(id)", "1.2.3.4\nmaxretry=1"])
def test_admin_ip_cannot_inject_configuration(tmp_path, bad):
    out = run_setup(tmp_path, ADMIN_IP=bad)
    assert out.returncode != 0
    assert not (tmp_path / "f2b" / "jail.d" / "conquer-login.local").exists()


def test_old_dos_jail_is_removed(tmp_path):
    jd = tmp_path / "f2b" / "jail.d"
    fd = tmp_path / "f2b" / "filter.d"
    jd.mkdir(parents=True)
    fd.mkdir(parents=True)
    (fd / "apache-dos-conquer.conf").write_text("[Definition]\nfailregex = x\n")
    (jd / "conquer-web.conf").write_text(
        "[apache-auth-conquer]\nenabled = true\nmaxretry = 3\n\n"
        "[apache-dos-conquer]\nenabled = true\nmaxretry = 200\n\n"
        "[ttyd-auth]\nenabled = true\n")
    assert run_setup(tmp_path).returncode == 0
    kept = (jd / "conquer-web.conf").read_text()
    assert "apache-dos-conquer" not in kept and "maxretry = 200" not in kept
    assert "[apache-auth-conquer]" in kept and "[ttyd-auth]" in kept
    assert not (fd / "apache-dos-conquer.conf").exists()


def test_no_script_installs_the_dos_jail_any_more():
    for name in ("setup-security.sh", "setup-security-basic.sh", "deploy-to-vps.sh", "update-vps.sh"):
        text = (ROOT / name).read_text()
        assert "[apache-dos-conquer]" not in text, name
        assert "filter.d/apache-dos-conquer" not in text.replace("rm -f", ""), name


def test_deploy_and_update_run_the_fail2ban_setup():
    assert "setup-fail2ban.sh" in (ROOT / "deploy-to-vps.sh").read_text()
    assert "setup-fail2ban.sh" in (ROOT / "update-vps.sh").read_text()


LOG_FORMAT = 'LogFormat "%h %l - %t \\"%r\\" %>s \\"%{Location}o\\"" conquer_login'


@pytest.mark.parametrize("conf", ["vps/virtualhost.conf.template", "apache/local.conf", "update-vps.sh"])
def test_apache_logs_failed_sign_ins(conf):
    text = (ROOT / conf).read_text()
    assert LOG_FORMAT in text
    assert 'SetEnvIf Request_URI "^/login/(do|long)$" conquer_login_post' in text
    assert re.search(r"CustomLog \S*conquer_login\.log|CustomLog \S*/login\.log", text)
    assert "env=conquer_login_post" in text


@pytest.mark.parametrize("conf", ["vps/virtualhost.conf.template", "apache/local.conf", "update-vps.sh"])
def test_api_bodies_are_limited_to_64k(conf):
    text = (ROOT / conf).read_text()
    for api in ("/join/api/", "/admin/api/"):
        assert re.search(r'<Location "%s">\s*LimitRequestBody 65536\s*</Location>' % re.escape(api), text), (conf, api)


def test_filter_on_the_log_of_a_running_apache():
    """CI signs in wrongly and rightly against the local stack and hands the
    login log over in CONQUER_LOGIN_LOG: the wrong ones count, the right ones do not."""
    path = os.environ.get("CONQUER_LOGIN_LOG")
    if not path:
        pytest.skip("CONQUER_LOGIN_LOG is not set")
    lines = [l for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]
    failed = [l for l in lines if "failed=1" in l]
    ok = [l for l in lines if "failed=1" not in l]
    assert failed and ok, lines
    assert all(hit(l) for l in failed), failed
    assert not any(hit(l) for l in ok), ok
