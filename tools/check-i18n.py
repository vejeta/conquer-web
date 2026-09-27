#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the translations of the site, the tutorial and the player menu.

Errors (exit status 1): a text used by a page or script that English does
not have, a text in a language that English does not have, a text whose
placeholders ({name} in the web, %s in the menu) differ from English, a
language of web/site.js without its catalog. Texts a language does not
have yet are listed as missing: they are shown in English.

usage: tools/check-i18n.py
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
errors = []


def rel(path):
    return os.path.relpath(path, ROOT)


def flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, prefix + k + "."))
        else:
            out[prefix + k] = v
    return out


def compare(name, en, other, placeholders):
    """en and other: {key: text}. Returns the missing keys."""
    for k in sorted(set(other) - set(en)):
        errors.append("%s: unknown text %s" % (name, k))
    for k in sorted(set(other) & set(en)):
        if isinstance(en[k], str) and placeholders(en[k]) != placeholders(other[k]):
            errors.append("%s: %s has %s, English has %s" % (name, k, placeholders(other[k]), placeholders(en[k])))
    return sorted(set(en) - set(other))


def web():
    d = os.path.join(ROOT, "web", "i18n")
    en = flat(json.load(open(os.path.join(d, "en.json"))))

    def braces(s):
        return sorted(re.findall(r"\{(\w+)\}", s))
    missing = {}
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        code = os.path.basename(path)[:-5]
        if code != "en":
            missing[code] = compare(rel(path), en, flat(json.load(open(path))), braces)
    # Languages offered by site.js
    site = open(os.path.join(ROOT, "web", "site.js")).read()
    for code in re.findall(r"\{ code: '([\w-]+)'", site):
        if not os.path.exists(os.path.join(d, code + ".json")):
            errors.append("web/site.js: language %s has no web/i18n/%s.json" % (code, code))
    # Keys used by the pages and scripts
    used = set()
    for path in glob.glob(os.path.join(ROOT, "web", "*.html")) + glob.glob(os.path.join(ROOT, "web", "try", "*.html")):
        s = open(path).read()
        used |= {(rel(path), k) for k in re.findall(r'data-i18n(?:-title)?="([\w.]+)"', s)}
        for ns in re.findall(r"conquerI18n\.t\('(\w+)\.' \+ key", s):
            used |= {(rel(path), ns + "." + k) for k in re.findall(r"\b(?:m|T)\('(\w+)'", s)}
    coach = open(os.path.join(ROOT, "web", "coach.js")).read()
    used |= {("web/coach.js", "coach." + k) for k in re.findall(r"\bT\('(\w+)'", coach)}
    for where, k in sorted(used):
        if k not in en:
            errors.append("%s: text %s is not in web/i18n/en.json" % (where, k))
    return missing


def menu():
    d = os.path.join(ROOT, "conquer", "i18n")

    def load(path):
        return dict(re.findall(r'^MSG\[(\w+)\]="((?:[^"\\]|\\.)*)"', open(path).read(), re.M | re.S))
    en = load(os.path.join(d, "en.sh"))

    def formats(s):
        return sorted(re.findall(r"%[^%]", s.replace("%%", "")))
    missing = {}
    for path in sorted(glob.glob(os.path.join(d, "*.sh"))):
        code = os.path.basename(path)[:-3]
        if code != "en":
            other = load(path)
            # a date format is not a printf format
            blank = {k: "" for k in ("menu_date_format",) if k in other}
            missing[code] = compare(rel(path), dict(en, menu_date_format=""), dict(other, **blank), formats)
    for name in ("menu.sh", "join.sh"):
        s = open(os.path.join(ROOT, "conquer", "scripts", name)).read()
        for k in re.findall(r"\b(?:t|tr_raw) (\w+)", s):
            if k not in en:
                errors.append("conquer/scripts/%s: text %s is not in conquer/i18n/en.sh" % (name, k))
    return missing


def tutorial():
    d = os.path.join(ROOT, "tools", "tutorial", "i18n")
    steps = {s["id"]: s for s in json.load(open(os.path.join(ROOT, "tools", "tutorial", "first-turn.content.json")))["steps"]}
    en = json.load(open(os.path.join(d, "en.json")))
    english = dict(("page." + k, v) for k, v in en["page"].items())
    english.update(("steps.%s.%s" % (i, k), s[k]) for i, s in steps.items() for k in ("title", "text", "veteran") if k in s)
    missing = {}
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        code = os.path.basename(path)[:-5]
        if code != "en":
            other = json.load(open(path))
            texts = dict(("page." + k, v) for k, v in other.get("page", {}).items())
            texts.update(("steps.%s.%s" % (i, k), v) for i, s in other.get("steps", {}).items() for k, v in s.items())
            missing[code] = compare(rel(path), english, texts, lambda s: sorted(re.findall(r"\{\{(\w+)\}\}", s)))
    return missing


def main():
    report = {"web": web(), "menu": menu(), "tutorial": tutorial()}
    for part, langs in report.items():
        for code, keys in langs.items():
            if keys:
                print("%s %s: %d texts shown in English: %s" % (part, code, len(keys), ", ".join(keys[:8]) + (" ..." if len(keys) > 8 else "")))
            else:
                print("%s %s: complete" % (part, code))
    for e in errors:
        print("ERROR " + e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
