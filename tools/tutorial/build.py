#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the first-turn tutorial from a recorded game session.

Inputs (tools/tutorial/):
  first-turn.content.json   the text of every step (title, keys, explanation,
                            and the screen text that shows the step is reached)
  first-turn.content.es.json  the same steps in Spanish
  tutorial.strings.json     the rest of the page's text, per language
  first-turn.screens.json   the 80x24 screen after every step, written by
                            record.py together with web/tutorial/first-turn.cast
  tutorial.template.html    the page, with <!--steps--> where the steps go and
                            {{name}} for each text of tutorial.strings.json

Outputs:
  web/tutorial.html               the tutorial page (English)
  web/tutorial.es.html            the tutorial page (Spanish)
  web/tutorial/first-turn.json    the steps for the in-game coach (game.html)
  web/tutorial/first-turn.es.json the same in Spanish

Re-record after game changes with record.py (see README.md), then run this.
"""
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "..", "web")

# Language: steps, and the page and coach steps written from them
LANGUAGES = {
    "en": ("first-turn.content.json", "tutorial.html", "first-turn.json"),
    "es": ("first-turn.content.es.json", "tutorial.es.html", "first-turn.es.json"),
}


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


def build(lang, template, screens, strings):
    content_file, page_file, coach_file = LANGUAGES[lang]
    content = json.load(open(os.path.join(HERE, content_file)))
    ui = strings[lang]

    items = []
    for n, step in enumerate(content["steps"], 1):
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
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: ui[m.group(1)], page)
    with open(os.path.join(WEB, page_file), "w") as f:
        f.write(page)
    print("wrote web/%s (%d steps)" % (page_file, len(items)))

    if coach_file:
        coach = {"title": content["title"], "steps": [
            {k: s[k] for k in ("id", "title", "keys", "text", "detect")} for s in content["steps"]]}
        os.makedirs(os.path.join(WEB, "tutorial"), exist_ok=True)
        with open(os.path.join(WEB, "tutorial", coach_file), "w") as f:
            json.dump(coach, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("wrote web/tutorial/%s" % coach_file)


def main():
    screens = {s["id"]: s["screen"] for s in json.load(open(os.path.join(HERE, "first-turn.screens.json")))}
    template = open(os.path.join(HERE, "tutorial.template.html")).read()
    strings = json.load(open(os.path.join(HERE, "tutorial.strings.json")))
    for lang in LANGUAGES:
        build(lang, template, screens, strings)


if __name__ == "__main__":
    main()
