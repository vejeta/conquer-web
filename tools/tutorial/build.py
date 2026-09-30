#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the first-turn tutorial from a recorded game session.

Inputs (tools/tutorial/):
  first-turn.content.json   the steps, in English: title, keys, explanation,
                            and the screen text that shows the step is reached
                            (detect), or for screens of the player menu the
                            menu text to wait for, in the page's language
                            (detect_menu, a key of conquer/i18n)
  first-turn.screens.json   the 80x24 screen after every step, written by
                            record.py together with web/tutorial/first-turn.cast
  tutorial.template.html    the page, with <!--steps--> where the steps go and
                            {{name}} for each text of the page
  i18n/<language>.json      one file per language: the page's texts ("page")
                            and, but in English, the steps' title, text and
                            veteran note by step id ("steps"); what a language
                            does not have is shown in English

Outputs, for English and every language in i18n/:
  web/tutorial.html, web/tutorial.<language>.html      the tutorial page
  web/tutorial/first-turn.json, first-turn.<language>.json
                                the steps for the in-game coach

Re-record after game changes with record.py (see README.md), then run this.
"""
import glob
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "..", "web")


def suffix(lang):
    return "" if lang == "en" else "." + lang


def key_html(key, ui):
    if key == "password":
        return "<kbd class=\"wide\">%s</kbd>" % html.escape(ui["key_password"])
    if key == "Space":
        key = ui["key_space"]
    return "<kbd>%s</kbd>" % html.escape(key)


def screen_html(lines, ui):
    """80x24 screen as a <pre>: reverse video and bold kept as spans."""
    rows = []
    for runs in lines:
        parts = []
        for text, attr in runs:
            t = html.escape(text)
            cls = []
            if attr & 1:
                cls.append("rev")
            if attr & 2:
                cls.append("b")
            parts.append('<span class="%s">%s</span>' % (" ".join(cls), t) if cls else t)
        rows.append("".join(parts).rstrip())
    return '<pre class="screen" role="img" aria-label="%s">%s</pre>' % (html.escape(ui["screen_label"]), "\n".join(rows))


def menu_texts(lang):
    """The player menu's texts in a language (conquer/i18n), English under."""
    texts = {}
    for code in ("en", lang):
        path = os.path.join(HERE, "..", "..", "conquer", "i18n", code + ".sh")
        if os.path.exists(path):
            texts.update(re.findall(r'^MSG\[(\w+)\]="((?:[^"\\]|\\.)*)"', open(path).read(), re.M | re.S))
    return texts


def menu_detect(text):
    """Regular expression for the first line of a menu text as the terminal
    shows it: styles removed, %s standing for anything."""
    line = next(l for l in re.sub(r"\$\{\w+\}", "", text).split("\n") if l.strip()).strip()
    return ".*".join(re.escape(part) for part in line.split("%s"))


def load_languages():
    """{code: catalog}, English first; every language falls back to English."""
    langs = {"en": json.load(open(os.path.join(HERE, "i18n", "en.json")))}
    for path in sorted(glob.glob(os.path.join(HERE, "i18n", "*.json"))):
        code = os.path.basename(path)[:-5]
        if code != "en":
            langs[code] = json.load(open(path))
    return langs


def build(lang, langs, template, screens, english):
    cat = langs[lang]
    ui = dict(langs["en"]["page"], **cat.get("page", {}))
    ui["lang"] = lang
    # Links to the tutorial in the other languages, each in its own name
    ui["lang_links"] = " · ".join(
        '<a href="tutorial%s.html" hreflang="%s" lang="%s">%s</a>' % (suffix(code), code, code, html.escape(c["language"]))
        for code, c in langs.items() if code != lang)
    translated = cat.get("steps", {})
    menu = menu_texts(lang)
    steps = []
    for step in english["steps"]:
        s = dict(step)
        s.update(translated.get(step["id"], {}))
        # Steps in the player menu wait for the menu's text in this language
        if "detect_menu" in s:
            s["detect"] = menu_detect(menu[s.pop("detect_menu")])
        steps.append(s)

    items = []
    for n, step in enumerate(steps, 1):
        keys = "".join(key_html(k, ui) for k in step["keys"]) or "<span class=\"nokey\">%s</span>" % ui["just_look"]
        veteran = ('<p class="veteran"><strong>%s</strong> %s</p>' % (ui["veterans"], step["veteran"])) if step.get("veteran") else ""
        items.append(
            '<li class="step" id="step-%(id)s">\n'
            '  <div class="step-text">\n'
            '    <h3><span class="num">%(n)02d</span> %(title)s</h3>\n'
            '    <p class="keys">%(keys)s</p>\n'
            '    %(text)s\n    %(veteran)s\n'
            '  </div>\n'
            '  <div class="step-screen">%(screen)s</div>\n'
            '</li>' % {"id": step["id"], "n": n, "title": html.escape(step["title"]), "keys": keys,
                       "text": step["text"], "veteran": veteran, "screen": screen_html(screens[step["id"]], ui)})
    page = template.replace("<!--steps-->", "\n".join(items))
    # The movement figure (web/moves.js) in the language of the page
    page = page.replace('<div data-moves="compact"></div>', '<div data-moves="compact" data-moves-lang="%s"></div>' % lang)
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: ui[m.group(1)], page)
    page_file = "tutorial%s.html" % suffix(lang)
    with open(os.path.join(WEB, page_file), "w") as f:
        f.write(page)

    coach_file = "first-turn%s.json" % suffix(lang)
    coach = {"title": cat.get("title", english["title"]), "steps": [
        {k: s[k] for k in ("id", "title", "keys", "text", "detect")} for s in steps]}
    os.makedirs(os.path.join(WEB, "tutorial"), exist_ok=True)
    with open(os.path.join(WEB, "tutorial", coach_file), "w") as f:
        json.dump(coach, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote web/%s and web/tutorial/%s (%d steps)" % (page_file, coach_file, len(items)))


def build_found(lang, langs):
    """The coach of the game's nation builder (found-nation.content.json):
    web/tutorial/found-nation[.language].json, the steps' title and text in
    the language ("found_steps" in i18n/), English where it has none."""
    found = json.load(open(os.path.join(HERE, "found-nation.content.json")))
    cat = langs[lang]
    translated = cat.get("found_steps", {})
    steps = []
    for step in found["steps"]:
        s = dict(step)
        s.update(translated.get(step["id"], {}))
        steps.append({k: s[k] for k in ("id", "title", "keys", "text", "detect")})
    name = "found-nation%s.json" % suffix(lang)
    with open(os.path.join(WEB, "tutorial", name), "w") as f:
        json.dump({"title": cat.get("found_title", found["title"]), "steps": steps}, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote web/tutorial/%s (%d steps)" % (name, len(steps)))


def main():
    english = json.load(open(os.path.join(HERE, "first-turn.content.json")))
    screens = {s["id"]: s["screen"] for s in json.load(open(os.path.join(HERE, "first-turn.screens.json")))}
    template = open(os.path.join(HERE, "tutorial.template.html")).read()
    langs = load_languages()
    for lang in langs:
        build(lang, langs, template, screens, english)
        build_found(lang, langs)


if __name__ == "__main__":
    main()
