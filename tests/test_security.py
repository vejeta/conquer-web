# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Security rules that must keep holding (see SECURITY.md): the account name
rule is the same everywhere, the terminal menu has no way out to a shell, the
proxy configs keep the identity header and the WebSocket origin check, and
the containers keep their hardening. They read the scripts and configs; the
end-to-end checks are in .github/workflows/ci.yml."""
import re
import subprocess

import pytest

from conftest import ROOT

SCRIPTS = ROOT / "conquer" / "scripts"
PROXY_CONFIGS = ["apache/local.conf", "vps/virtualhost.conf.template"]
COMPOSE = ["docker-compose.vps.yml", "docker-compose.local.yml"]

GOOD_NAMES = ["a", "kestrel", "Ana_2", "a.b-c", "9lives", "x" * 32]
BAD_NAMES = ["", ".", "..", ".x", "-v", "-", "_x", "a b", "a:b", "a/b", "a;b", "$(id)", "x" * 33, "a\nb", "ana\n"]


def bash(script, *args):
    return subprocess.run(["bash", "-c", script, "bash", *args], capture_output=True, text=True, timeout=30)


def function(path, name):
    """The text of a shell function, from its name to the closing brace."""
    m = re.search(r"^%s\(\) \{\n.*?^\}\n" % re.escape(name), path.read_text(), re.S | re.M)
    assert m, "%s not found in %s" % (name, path)
    return m.group(0)


@pytest.mark.parametrize("path, name", [(SCRIPTS / "signup.sh", "valid_account"), (ROOT / "manage-players.sh", "valid_name")])
def test_shell_account_rule(path, name):
    check = function(path, name) + '\n%s "$1"' % name
    for good in GOOD_NAMES:
        assert bash(check, good).returncode == 0, "%r should be accepted by %s" % (good, name)
    for bad in BAD_NAMES:
        assert bash(check, bad).returncode != 0, "%r should be refused by %s" % (bad, name)


def test_gate_account_rule_is_the_same():
    source = (ROOT / "conquer" / "gate" / "main.go").read_text()
    m = re.search(r"accountRe\s*=\s*regexp\.MustCompile\(`([^`]+)`\)", source)
    assert m
    # Go's $ matches only at the end of the text; Python's also before a final newline
    pattern = re.compile(m.group(1).replace("$", r"\Z"))
    for good in GOOD_NAMES:
        assert pattern.search(good), good
    for bad in BAD_NAMES:
        assert not pattern.search(bad), bad
    # The same expression as the shell tools
    for path in (SCRIPTS / "signup.sh", ROOT / "manage-players.sh"):
        assert m.group(1) in path.read_text(), "%s uses another account rule" % path.name


def test_practice_world_cannot_be_dot_or_dotdot():
    """new_practice_world runs rm -rf on this directory."""
    script = function(SCRIPTS / "menu.sh", "practice_dir") + '\nPRACTICE_ROOT=/practice PLAYER="$1"; practice_dir'
    for player, expected in [("kestrel", "/practice/kestrel"), ("..", "/practice/_.."), (".", "/practice/_."),
                             ("-rf", "/practice/_-rf"), ("a/b", "/practice/a_b"), ("", "/practice/guest")]:
        out = bash(script, player).stdout.strip()
        assert out == expected, "%r -> %r" % (player, out)
        assert not out.endswith(("/..", "/.", "/practice/")), out


def test_every_pager_is_secure():
    """less runs shell commands (!), an editor (v) and reads files (:e) unless LESSSECURE=1."""
    for path in SCRIPTS.glob("*.sh"):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#", 1)[0]
            if re.search(r"\b(less|more|man|vi|vim|nano|emacs)\b", code) and not code.strip().startswith(("echo", "say")):
                assert "LESSSECURE=1" in code, "%s:%d runs a pager without LESSSECURE=1" % (path.name, n)


def test_menu_never_hands_out_a_shell():
    for name in ("menu.sh", "join.sh"):
        text = (SCRIPTS / name).read_text()
        assert not re.search(r"^\s*(exec\s+)?(ba|da|z|k)?sh\b(?!\s*#)", text, re.M), "%s starts a shell" % name
        assert not re.search(r"\beval\b", text), "%s uses eval" % name
    # The game's nation builder gets a clean environment
    assert "env -i" in (SCRIPTS / "join.sh").read_text()


def test_join_links_only_safe_nation_names():
    """A nation named "*:x" would read as an administrator in .players."""
    text = (SCRIPTS / "join.sh").read_text()
    assert '[[ "$nation" =~ ^[A-Za-z0-9_.-]{1,9}$ ]]' in text


@pytest.mark.parametrize("name", PROXY_CONFIGS)
def test_proxy_config_identity_and_origin(name):
    text = (ROOT / name).read_text()
    # A client-supplied identity is dropped before anything else
    assert re.search(r"^\s*RequestHeader unset X-WEBAUTH-USER early", text, re.M)
    # Only the game's own page may open a WebSocket to the terminal
    assert re.search(r'RewriteCond "%\{HTTP:Origin\}\|https://%\{HTTP_HOST\}" "!\^\(\.\+\)\\\|\\1\$" \[NC\]', text)
    assert re.search(r"RewriteRule \^/play/ - \[F,L\]", text)
    # ... and that rule comes before the one that proxies the socket
    assert text.index("RewriteRule ^/play/ - [F,L]") < text.index("ws://")
    # Both the terminal and the administrator page check the account
    for location in ("/play/", "/admin/"):
        block = re.search(r'^\s*<Location "%s">(.*?)</Location>' % location, text, re.S | re.M)
        assert block, location
        assert "Require valid-user" in block.group(1)
        assert 'RequestHeader set X-WEBAUTH-USER "%{REMOTE_USER}s"' in block.group(1)


@pytest.mark.parametrize("name", PROXY_CONFIGS)
def test_sign_in_is_a_page_and_a_session_cookie(name):
    """/play/ and /admin/ sign in through web/login.html: a form (mod_auth_form)
    and a session cookie that is encrypted, httponly, secure and same-site."""
    text = (ROOT / name).read_text()
    assert "AuthType Basic" not in text
    for location in ("/play/", "/admin/", "/login/do", "/login/long", "/logout"):
        block = re.search(r'^\s*<Location "%s">(.*?)</Location>' % location, text, re.S | re.M)
        assert block, location
        body = block.group(1)
        assert "Session On" in body, location
        assert "SessionCookieName conquer_session path=/;httponly;secure;samesite=lax" in body, location
        assert re.search(r'SessionCryptoPassphraseFile "[^"]+"', body), location
    for location in ("/play/", "/admin/"):
        body = re.search(r'^\s*<Location "%s">(.*?)</Location>' % location, text, re.S | re.M).group(1)
        assert "AuthType form" in body and "AuthFormProvider file" in body
        assert "AuthFormLoginRequiredLocation" in body and "/login.html" in body
        assert "SessionCookieRemove On" in body     # the game never sees the cookie
    assert "SetHandler form-login-handler" in text and "SetHandler form-logout-handler" in text
    # Remember me: the same form, a cookie of 30 days
    assert re.search(r'^\s*<Location "/login/long">.*?SessionMaxAge 2592000.*?</Location>', text, re.S | re.M)
    assert re.search(r'^\s*<Location "/login/do">.*?SessionMaxAge 0.*?</Location>', text, re.S | re.M)


def test_local_apache_has_the_sign_in_modules():
    text = (ROOT / "apache" / "Dockerfile").read_text()
    for module in ("auth_form", "session", "session_cookie", "session_crypto", "request"):
        assert module in text
    assert "session.key" in text


def test_vps_config_headers():
    text = (ROOT / "vps" / "virtualhost.conf.template").read_text()
    assert "Strict-Transport-Security" in text
    csp = re.search(r'Content-Security-Policy "([^"]+)"', text).group(1)
    for directive in ("default-src 'self'", "frame-ancestors 'self'", "object-src 'none'", "base-uri 'self'"):
        assert directive in csp
    assert "http://127.0.0.1:7682/admin/api/" in text and "http://127.0.0.1:7681/play/" in text


@pytest.mark.parametrize("name", COMPOSE)
def test_game_container_is_hardened(name):
    text = (ROOT / name).read_text()
    assert re.search(r"cap_drop:\s*\n\s*- ALL", text)
    assert "no-new-privileges:true" in text
    assert re.search(r"^\s*pids_limit: \d+", text, re.M) and re.search(r"^\s*mem_limit: \w+", text, re.M)
    # Published ports only on the loopback: the proxy is the only way in
    for port in re.findall(r"^\s*-\s*\"?([^\s\"]*:\d+:\d+)\"?", text, re.M):
        if port.count(":") == 2:
            assert port.startswith("127.0.0.1:"), "%s publishes %s beyond localhost" % (name, port)


def test_local_compose_does_not_publish_the_game_ports():
    text = (ROOT / "docker-compose.local.yml").read_text()
    game = text.split("  apache:")[0]
    assert not re.search(r"^\s*ports:", game, re.M), "ttyd and the gate must only be reachable through Apache"


def test_backups_are_private():
    text = (SCRIPTS / "turn.sh").read_text()
    assert "umask 077" in text and "chmod 700" in text


def test_no_tracing_or_secrets_in_ci():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert not re.search(r"set -[a-z]*x|bash -x|ACTIONS_STEP_DEBUG", text)
    assert "secrets." not in text
