# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The sign-in page (web/login.html): the Doors of Durin in front of a form
that posts what Apache's mod_auth_form wants. Apache itself is exercised by
the smoke job of the CI; here the server is a stand-in (page.route).

Needs the Python playwright module and Chromium."""
from urllib.parse import parse_qs

import pytest

from test_browser import browser, site  # noqa: F401

pytestmark = pytest.mark.browser

TITLES = {"en": "The Doors of Durin", "es": "Las Puertas de Durin", "zh": "都灵之门"}


@pytest.mark.parametrize("lang", ["es", "en", "zh"])
def test_login_page_renders(site, browser, lang):  # noqa: F811
    page = browser.new_page()
    page.goto(site + "login.html?lang=" + lang)
    page.wait_for_function("t => document.querySelector('h1').innerText === t", arg=TITLES[lang])
    assert page.is_visible("#gate-runes") and page.is_visible(".leaf.l") and page.is_visible(".leaf.r")
    assert page.is_visible("#account") and page.is_visible("#password") and page.is_visible("#remember")
    assert page.get_attribute("#password", "type") == "password"
    assert page.get_attribute("#form", "method") == "post"
    assert page.get_attribute("#account", "name") == "httpd_username"
    assert page.get_attribute("#password", "name") == "httpd_password"
    assert page.get_attribute("#location", "name") == "httpd_location"
    # The keycap is translated, the failure message is hidden at first
    assert page.inner_text("#go").strip() != "Speak friend and enter" or lang == "en"
    assert page.is_hidden("#failed")
    assert "/login/do" in page.get_attribute("#form", "action")
    page.close()


def test_remember_me_picks_the_long_login_and_next_is_kept(site, browser):  # noqa: F811
    page = browser.new_page()
    page.goto(site + "login.html?lang=en&next=/admin/")
    assert page.get_attribute("#form", "action") == "/login/do?next=%2Fadmin%2F"
    page.check("#remember")
    assert page.get_attribute("#form", "action") == "/login/long?next=%2Fadmin%2F"
    assert page.input_value("#location") == "/admin/"
    page.close()


def test_next_cannot_leave_the_site(site, browser):  # noqa: F811
    for bad in ("//evil.example/", "https://evil.example/", "/\\evil.example"):
        page = browser.new_page()
        page.goto(site + "login.html?lang=en&next=" + bad.replace("\\", "%5C"))
        assert page.input_value("#location") == "/game.html", bad
        page.close()


def test_submit_posts_the_form_and_the_doors_open(site, browser):  # noqa: F811
    page = browser.new_page()
    posts = []

    def login(route):
        req = route.request
        posts.append((req.url, req.method, parse_qs(req.post_data or "")))
        route.fulfill(status=302, headers={"location": "/play/"})
    page.route("**/login/**", login)
    page.goto(site + "login.html?lang=en&next=/play/")
    page.fill("#account", "ana")
    page.fill("#password", "pw one")
    page.check("#remember")
    page.click("#go")
    page.wait_for_selector("#gate.open")
    page.wait_for_url("**/play/")
    assert len(posts) == 1
    url, method, body = posts[0]
    assert method == "POST" and url.endswith("/login/long?next=%2Fplay%2F")
    assert body == {"httpd_username": ["ana"], "httpd_password": ["pw one"], "httpd_location": ["/play/"]}
    page.close()


def test_wrong_password_flickers_and_shakes(site, browser):  # noqa: F811
    page = browser.new_page()
    page.route("**/login/do**", lambda r: r.fulfill(status=302, headers={"location": "/login.html?failed=1&next=%2Fplay%2F"}))
    page.goto(site + "login.html?lang=en")
    page.fill("#account", "ana")
    page.fill("#password", "nope")
    page.click("#go")
    page.wait_for_selector("#failed:not([hidden])")
    assert "wrong account or password" in page.inner_text("#failed")
    assert page.evaluate("document.getElementById('gate-runes').classList.contains('flicker')")
    assert page.evaluate("document.getElementById('stage').classList.contains('shake')")
    assert not page.evaluate("document.getElementById('gate').classList.contains('open')")
    assert page.input_value("#password") == ""
    page.close()


def test_redirected_back_with_failed_marker(site, browser):  # noqa: F811
    """Without JavaScript Apache redirects to /login.html?failed=1: the page shows it"""
    page = browser.new_page()
    page.goto(site + "login.html?lang=en&failed=1&next=%2Fadmin%2F")
    assert page.is_visible("#failed")
    assert page.evaluate("document.getElementById('gate-runes').classList.contains('flicker')")
    assert page.input_value("#location") == "/admin/"
    page.close()


def test_signed_out_message(site, browser):  # noqa: F811
    page = browser.new_page()
    page.goto(site + "login.html?lang=es&loggedout=1")
    page.wait_for_function("() => document.getElementById('info').textContent.includes('Has salido')")
    page.close()


def test_pages_have_a_sign_out_link(site, browser):  # noqa: F811
    page = browser.new_page()
    page.route("**/admin/api/**", lambda r: r.fulfill(status=403, content_type="application/json", body='{"ok": false}'))
    for name in ("game.html", "admin.html"):
        page.goto(site + name + "?lang=en")
        assert page.get_attribute("#logout", "href") == "/logout", name
        assert page.inner_text("#logout").strip() == "Sign out", name
    page.close()


def test_admin_goes_to_the_sign_in_page_when_there_is_no_session(site, browser):  # noqa: F811
    page = browser.new_page()
    page.route("**/admin/api/**", lambda r: r.fulfill(status=302, headers={"location": "/login.html?next=%2Fadmin%2Fapi%2Fstate"}))
    page.goto(site + "admin.html?lang=en")
    page.wait_for_url("**/login.html?next=%2Fadmin.html")
    page.close()
