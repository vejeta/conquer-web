# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Android app step of update-vps.sh (between its APK-STEP markers), run
alone against a fake GitHub API served from a local http.server."""
import hashlib
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from conftest import ROOT

SCRIPT = (ROOT / "update-vps.sh").read_text()
BLOCK = SCRIPT[SCRIPT.index("# APK-STEP-BEGIN"):SCRIPT.index("# APK-STEP-END")]
TOKEN = "ghp_faketoken1234567890"


class Fake:
    def __init__(self):
        self.tag = "v1.0.0"
        self.apk = b"apk bytes v1.0.0"
        self.sha = None            # None: the right checksum
        self.seen = []             # (path, headers) of each request

    def sha_text(self):
        return self.sha or "%s  conquer.apk\n" % hashlib.sha256(self.apk).hexdigest()


@pytest.fixture
def api():
    fake = Fake()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            fake.seen.append((self.path, dict(self.headers)))
            base = "http://127.0.0.1:%d" % self.server.server_port
            if self.path == "/repos/x/y/releases/latest":
                body = json.dumps({"tag_name": fake.tag, "assets": [
                    {"name": "conquer.apk", "url": base + "/assets/1"},
                    {"name": "conquer.apk.sha256", "url": base + "/assets/2"}]}).encode()
            elif self.path in ("/assets/1", "/assets/2"):
                if "octet-stream" not in self.headers.get("Accept", ""):
                    self.send_response(415)
                    self.end_headers()
                    return
                body = fake.apk if self.path == "/assets/1" else fake.sha_text().encode()
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    fake.url = "http://127.0.0.1:%d" % srv.server_port
    yield fake
    srv.shutdown()


def run(tmp_path, api, env_file="APK_REPO=x/y\nAPK_URL=/downloads/conquer.apk\n", token=None, mode=0o600):
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "production.env").write_text(env_file)
    web = tmp_path / "www"
    web.mkdir(exist_ok=True)
    tokfile = tmp_path / "github-token"
    if token:
        tokfile.write_text(token + "\n")
        tokfile.chmod(mode)
    env = dict(os.environ, WEB_ROOT=str(web), GITHUB_API=api.url,
               CONQUER_GITHUB_TOKEN_FILE=str(tokfile), TMPDIR=str(tmp_path))
    r = subprocess.run(["bash", "-c", "set -e\n" + BLOCK + "\necho finished"], cwd=tmp_path, env=env,
                       capture_output=True, text=True, timeout=60)
    return r, web / "downloads"


def test_installs_the_release_and_offers_it(tmp_path, api):
    r, dl = run(tmp_path, api)
    assert r.returncode == 0 and "finished" in r.stdout, r.stderr + r.stdout
    assert (dl / "conquer.apk").read_bytes() == api.apk
    assert (dl / "version.txt").read_text().strip() == "v1.0.0"
    assert (dl / "conquer.apk.sha256").read_text() == api.sha_text()
    assert "✅ Android app v1.0.0 installed" in r.stdout
    assert (tmp_path / "www" / "site-config.js").read_text() == "window.CONQUER_SITE = { apk: '/downloads/conquer.apk' };\n"
    assert not list(dl.glob(".*.new"))
    # no token file: anonymous
    assert all("Authorization" not in h for _, h in api.seen)


def test_skips_when_the_version_is_installed(tmp_path, api):
    run(tmp_path, api)
    n = len(api.seen)
    api.apk = b"changed on the server but same tag"
    r, dl = run(tmp_path, api)
    assert "already installed" in r.stdout
    assert len(api.seen) == n + 1          # only the release lookup
    assert (dl / "conquer.apk").read_bytes() == b"apk bytes v1.0.0"


def test_a_newer_release_replaces_it(tmp_path, api):
    run(tmp_path, api)
    api.tag, api.apk = "v1.1.0", b"newer"
    r, dl = run(tmp_path, api)
    assert (dl / "conquer.apk").read_bytes() == b"newer"
    assert (dl / "version.txt").read_text().strip() == "v1.1.0"


def test_a_bad_checksum_keeps_the_old_files(tmp_path, api):
    run(tmp_path, api)
    api.tag, api.apk, api.sha = "v1.1.0", b"tampered", "0" * 64 + "  conquer.apk\n"
    r, dl = run(tmp_path, api)
    assert r.returncode == 0 and "finished" in r.stdout
    assert "⚠️" in r.stdout and "checksum" in r.stdout
    assert (dl / "conquer.apk").read_bytes() == b"apk bytes v1.0.0"
    assert (dl / "version.txt").read_text().strip() == "v1.0.0"


def test_a_failing_server_only_warns(tmp_path, api):
    api.url = api.url.replace("127.0.0.1:", "127.0.0.1:1")      # nothing listens there
    r, dl = run(tmp_path, api)
    assert r.returncode == 0 and "finished" in r.stdout
    assert "⚠️" in r.stdout and not (dl / "conquer.apk").exists()
    # and the section stays hidden: the file is not there
    assert not (tmp_path / "www" / "site-config.js").exists()


def test_a_token_file_with_the_wrong_mode_is_refused(tmp_path, api):
    r, dl = run(tmp_path, api, token=TOKEN, mode=0o644)
    assert r.returncode == 0 and "mode 644" in r.stdout
    assert api.seen == [] and not (dl / "conquer.apk").exists()
    assert TOKEN not in r.stdout + r.stderr


def test_the_token_is_sent_but_never_on_the_command_line(tmp_path, api):
    r, dl = run(tmp_path, api, token=TOKEN)
    assert (dl / "conquer.apk").exists()
    assert api.seen and all(h.get("Authorization") == "Bearer " + TOKEN for _, h in api.seen)
    assert TOKEN not in r.stdout + r.stderr
    # curl gets a header file (-H @file), not the header
    assert '-H "@$hdr"' in BLOCK and "Bearer $token" in BLOCK
    assert not any(("curl" in line and "$token" in line) for line in BLOCK.splitlines())


def test_nothing_happens_without_apk_settings(tmp_path, api):
    r, dl = run(tmp_path, api, env_file="APK_REPO=\nAPK_URL=\n")
    assert r.returncode == 0 and api.seen == [] and not dl.exists()
    assert not (tmp_path / "www" / "site-config.js").exists()


def test_an_odd_repository_name_is_refused(tmp_path, api):
    r, dl = run(tmp_path, api, env_file="APK_REPO=x/y;touch pwned\nAPK_URL=\n")
    assert "owner/repository" in r.stdout and api.seen == []
    assert not (tmp_path / "pwned").exists()


def test_the_downloads_survive_the_page_sync_and_apache_types_apk():
    assert "--exclude /downloads/" in SCRIPT
    tpl = (ROOT / "vps" / "virtualhost.conf.template").read_text()
    assert "AddType application/vnd.android.package-archive .apk" in tpl


def test_the_generic_repository_names_no_app_repository():
    """conquer-web is public and generic: the private app repository is a
    deployment setting (APK_REPO), never named in a tracked file."""
    out = subprocess.run(["git", "grep", "-n", "-I", "-i", "conquer-cefrium", "--", ".", ":(exclude)tests/test_apk_download.py"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.stdout == "", out.stdout
