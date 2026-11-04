# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""update-vps.sh patches the virtual host of an existing server: the sign-in
log, the log of wrong recovery codes, the limits on request bodies and the
account API. Runs that part of the script (between its two markers) on a
sample virtual host, with stand-ins for apache2ctl and systemctl."""
import os
import re
import subprocess

import pytest

from conftest import ROOT

SCRIPT = (ROOT / "update-vps.sh").read_text()
START = "# Abuse limits in the virtual host"
END = "# fail2ban with the jail for wrong passwords"

# A virtual host as deploy-to-vps.sh wrote it before the account pages
OLD_VHOST = """<VirtualHost *:443>
    ServerName example.test
    ProxyPass /admin/api/ http://127.0.0.1:7682/admin/api/
    ProxyPass /play/ http://127.0.0.1:7681/play/
    ErrorLog ${APACHE_LOG_DIR}/conquer_ssl_error.log
    CustomLog ${APACHE_LOG_DIR}/conquer_ssl_access.log combined
    <Location "/admin/">
        AuthType form
        AuthUserFile "/etc/apache2/conquer-web.htpasswd"
        SessionCryptoPassphraseFile "/etc/apache2/conquer-web.session"
    </Location>
    <Location "/play/">
        AuthType form
        AuthName "Conquer"
        AuthFormProvider file
        AuthUserFile "/etc/apache2/conquer-web.htpasswd"
        Session On
        SessionCryptoPassphraseFile "/etc/apache2/conquer-web.session"
        Require valid-user
    </Location>
</VirtualHost>
"""
# ... and after the previous update (sign-in log and body limits, no account API)
MID_VHOST = OLD_VHOST.replace(
    "    <Location \"/admin/\">",
    """    LogFormat "%h %l - %t \\"%r\\" %>s \\"%{Location}o\\"" conquer_login
    SetEnvIf Request_URI "^/login/(do|long)$" conquer_login_post
    CustomLog ${APACHE_LOG_DIR}/conquer_login.log conquer_login env=conquer_login_post
    <Location "/join/api/">
        LimitRequestBody 65536
    </Location>
    <Location "/admin/api/">
        LimitRequestBody 65536
    </Location>
    <Location "/admin/">""")


def patch(tmp_path, vhost, configtest_ok=True):
    sites = tmp_path / "sites-available"
    sites.mkdir(exist_ok=True)
    conf = sites / "example.test.conf"
    conf.write_text(vhost)
    block = SCRIPT[SCRIPT.index(START):SCRIPT.index(END)].replace("/etc/apache2/sites-available", str(sites))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    ctl = bin_dir / "apache2ctl"
    ctl.write_text("#!/bin/sh\nexit %d\n" % (0 if configtest_ok else 1))
    ctl.chmod(0o755)
    (bin_dir / "systemctl").write_text("#!/bin/sh\necho \"$@\" >> %s\n" % (tmp_path / "systemctl.log"))
    (bin_dir / "systemctl").chmod(0o755)
    env = dict(os.environ, PATH="%s:%s" % (bin_dir, os.environ["PATH"]))
    run = subprocess.run(["bash", "-c", 'DOMAIN=example.test\n' + block], env=env, capture_output=True, text=True, timeout=30)
    return run, conf


@pytest.mark.parametrize("start", [OLD_VHOST, MID_VHOST], ids=["before-sign-in-log", "before-account-pages"])
def test_the_virtual_host_gets_everything_it_lacks(tmp_path, start):
    run, conf = patch(tmp_path, start)
    assert run.returncode == 0, run.stderr + run.stdout
    text = conf.read_text()
    # both logs
    assert text.count("conquer_login.log conquer_login env=conquer_login_post") == 1
    assert text.count('CustomLog ${APACHE_LOG_DIR}/conquer_recover.log conquer_login env=conquer_recover_post') == 1
    assert 'SetEnvIf Request_URI "^/(join/api/recover|account/api/(password|recovery))$" conquer_recover_post' in text
    # the account API: proxied, behind the sign-in, with the site's own file names
    assert "ProxyPass /account/api/ http://127.0.0.1:7682/account/api/" in text
    block = re.search(r'<Location "/account/api/">\s*AuthType form.*?</Location>', text, re.S).group(0)
    assert 'AuthUserFile "/etc/apache2/conquer-web.htpasswd"' in block
    assert 'SessionCryptoPassphraseFile "/etc/apache2/conquer-web.session"' in block
    assert "Require valid-user" in block and 'RequestHeader set X-WEBAUTH-USER "%{REMOTE_USER}s"' in block
    for api in ("/join/api/", "/admin/api/", "/account/api/"):
        assert re.search(r'<Location "%s">\s*LimitRequestBody 65536\s*</Location>' % re.escape(api), text), api
    # the game's own Location is still the last one
    assert text.rindex("<Location") == text.rindex('<Location "/play/">')
    assert "reload apache2" in (tmp_path / "systemctl.log").read_text()
    assert not list(conf.parent.glob("*.before-abuse")) and not list(conf.parent.glob("*.new"))


def test_patching_twice_changes_nothing(tmp_path):
    run, conf = patch(tmp_path, OLD_VHOST)
    assert run.returncode == 0
    once = conf.read_text()
    run, conf = patch(tmp_path, once)
    assert run.returncode == 0
    assert conf.read_text() == once
    assert "already in the virtual host" in run.stdout


def test_a_change_apache_refuses_is_undone(tmp_path):
    run, conf = patch(tmp_path, MID_VHOST, configtest_ok=False)
    assert conf.read_text() == MID_VHOST
    assert "Apache refused" in run.stdout


def test_restarts_itself_after_a_pull_that_changed_it():
    """bash keeps running the copy it opened: after git pull changed the script,
    the steps after the pull must come from the new version, with the same
    arguments, and the backup is not made twice."""
    pull = SCRIPT.index("g pull --ff-only")
    restart = SCRIPT.index('CONQUER_UPDATE_RESTARTED=1 exec "$SCRIPT_DIR/update-vps.sh" "${ARGS[@]}"')
    assert pull < restart < SCRIPT.index("# 3. The game container")
    assert 'g diff --quiet "$before" "$after" -- update-vps.sh' in SCRIPT
    assert SCRIPT.index('ARGS=("$@")') < SCRIPT.index("while [ $# -gt 0 ]")
    backup = SCRIPT.index("# 1. A copy of what must never be lost")
    assert SCRIPT.index('if [ -z "${CONQUER_UPDATE_RESTARTED:-}" ]; then', backup) < SCRIPT.index("BACKUP=")
