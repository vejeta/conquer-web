# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The privacy notice (web/privacy.html, web/privacy.es.html): both exist and
link to each other, load nothing from other sites, every page with a footer
links to it, and the placeholders the owner must fill are still there once
each (so none is forgotten silently).

When the owner has filled them in, set PLACEHOLDERS_FILLED = True: the test
then demands that none is left."""
import re

import pytest

from conftest import WEB

PLACEHOLDERS_FILLED = True
PLACEHOLDERS = ["CONTACT_EMAIL", "POSTAL_ADDRESS", "HOSTING_PROVIDER", "HOSTING_COUNTRY", "MAIL_PROVIDER"]
PAGES = {"en": WEB / "privacy.html", "es": WEB / "privacy.es.html"}


def text(path):
    return path.read_text(encoding="utf-8")


def test_both_pages_exist():
    for path in PAGES.values():
        assert path.is_file(), path


def test_pages_link_to_each_other():
    assert 'href="privacy.es.html"' in text(PAGES["en"])
    assert 'href="privacy.html"' in text(PAGES["es"])
    assert '<html lang="en">' in text(PAGES["en"])
    assert '<html lang="es">' in text(PAGES["es"])


@pytest.mark.parametrize("lang", PAGES)
def test_no_external_resources(lang):
    html = re.sub(r"<!--.*?-->", "", text(PAGES[lang]), flags=re.S)
    # Resources the browser loads by itself: scripts, styles, images, media,
    # frames, fonts and CSS url(). Plain <a href> links may go out.
    loaded = re.findall(r'<(?:script|img|iframe|video|audio|source|embed|object)\b[^>]*?\b(?:src|data)="([^"]*)"', html)
    loaded += re.findall(r'<link\b[^>]*?\bhref="([^"]*)"', html)
    loaded += re.findall(r"url\(\s*['\"]?([^)'\"]*)", html)
    loaded += re.findall(r"@import\s+['\"]?([^'\";]*)", html)
    external = [u for u in loaded if re.match(r"(?:[a-z][a-z0-9+.-]*:)?//|[a-z][a-z0-9+.-]*:", u, re.I)]
    assert external == []
    assert 'http-equiv="Content-Security-Policy"' not in html or "default-src 'self'" in html


@pytest.mark.parametrize("lang", PAGES)
def test_placeholders(lang):
    html = text(PAGES[lang])
    for name in PLACEHOLDERS:
        token = "{{%s}}" % name
        want = 0 if PLACEHOLDERS_FILLED else 1
        assert html.count(token) == want, "%s in %s: expected %d, found %d" % (token, PAGES[lang].name, want, html.count(token))
    # no other token of the same kind
    found = set(re.findall(r"\{\{(\w+)\}\}", html))
    assert found <= (set() if PLACEHOLDERS_FILLED else set(PLACEHOLDERS))


def test_contains_the_required_parts():
    en, es = text(PAGES["en"]), text(PAGES["es"])
    for html in (en, es):
        assert "Juan Manuel Méndez Rey" in html
        assert "https://www.aepd.es" in html
        assert "2026-11-04" in html
        assert "POST_NOTIFICATIONS" in html
    assert "not legal advice" in en.lower() and "no es asesoramiento" in es.lower()


def pages_with_footer():
    return sorted(p for p in WEB.glob("*.html") if "<footer" in text(p))


def test_every_footer_links_to_privacy():
    pages = pages_with_footer()
    assert len(pages) >= 10
    missing = []
    for p in pages:
        footer = re.search(r"<footer.*?</footer>", text(p), re.S).group(0)
        if not re.search(r'href="/?privacy(?:\.es)?\.html"', footer):
            missing.append(p.name)
    assert missing == []


def test_language_pages_are_declared():
    site = (WEB / "site.js").read_text(encoding="utf-8")
    assert re.search(r"code: 'en'.*'privacy'", site) and re.search(r"code: 'es'.*'privacy'", site)
