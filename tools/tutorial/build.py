#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the first-turn tutorial from a recorded game session.

Inputs (tools/tutorial/):
  first-turn.content.json   the text of every step (title, keys, explanation,
                            and the screen text that shows the step is reached)
  first-turn.screens.json   the 80x24 screen after every step, written by
                            record.py together with web/tutorial/first-turn.cast
  tutorial.template.html    the page, with <!--steps--> where the steps go

Outputs:
  web/tutorial.html               the tutorial page
  web/tutorial/first-turn.json    the steps for the in-game coach (game.html)

Re-record after game changes with record.py (see README.md), then run this.
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "..", "web")

KEY_NAMES = {"Space", "Enter", "Esc", "password"}


def key_html(key):
    if key == "password":
        return "<kbd class=\"wide\">your password</kbd>"
    return "<kbd>%s</kbd>" % html.escape(key)


def screen_html(lines):
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
    return '<pre class="screen" role="img" aria-label="Game screen">%s</pre>' % "\n".join(rows)


def main():
    content = json.load(open(os.path.join(HERE, "first-turn.content.json")))
    screens = {s["id"]: s["screen"] for s in json.load(open(os.path.join(HERE, "first-turn.screens.json")))}
    template = open(os.path.join(HERE, "tutorial.template.html")).read()

    items = []
    for n, step in enumerate(content["steps"], 1):
        keys = "".join(key_html(k) for k in step["keys"]) or "<span class=\"nokey\">just look</span>"
        veteran = ('<p class="veteran"><strong>Veterans:</strong> %s</p>' % step["veteran"]) if step.get("veteran") else ""
        items.append(
            '<li class="step" id="step-%(id)s">\n'
            '  <div class="step-text">\n'
            '    <h3><span class="num">%(n)02d</span> %(title)s</h3>\n'
            '    <p class="keys">%(keys)s</p>\n'
            '    %(text)s\n    %(veteran)s\n'
            '  </div>\n'
            '  <div class="step-screen">%(screen)s</div>\n'
            '</li>' % {"id": step["id"], "n": n, "title": html.escape(step["title"]), "keys": keys,
                       "text": step["text"], "veteran": veteran, "screen": screen_html(screens[step["id"]])})
    page = template.replace("<!--steps-->", "\n".join(items))
    with open(os.path.join(WEB, "tutorial.html"), "w") as f:
        f.write(page)

    coach = {"title": content["title"], "steps": [
        {k: s[k] for k in ("id", "title", "keys", "text", "detect")} for s in content["steps"]]}
    os.makedirs(os.path.join(WEB, "tutorial"), exist_ok=True)
    with open(os.path.join(WEB, "tutorial", "first-turn.json"), "w") as f:
        json.dump(coach, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote web/tutorial.html and web/tutorial/first-turn.json (%d steps)" % len(items))


if __name__ == "__main__":
    main()
