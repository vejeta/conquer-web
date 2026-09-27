# Languages of the website

Every text of the site's pages is in one file per language: `en.json`
(English, the reference), `es.json` (Spanish)... `site.js` loads English
and the visitor's language on top of it, so a text a language does not have
is shown in English.

The visitor's language is, in this order: `?lang=` in the address, the
choice made in the language menu of the home page, the browser's languages,
English.

## What is where

| Texts | Where |
|-------|-------|
| Home page, game page, try page, coach, hall of fame | `i18n/<language>.json`, one section per page (`index`, `game`, `try`, `coach`, `hall`) |
| First-turn tutorial and coach steps | `tools/tutorial/i18n/<language>.json`, built into `tutorial.<language>.html` and `tutorial/first-turn.<language>.json` |
| Player's guide | a page per language: `guide.<language>.html` |
| Terminal menu and join wizard | `conquer/i18n/<language>.sh` |
| Narrated video | `tools/tutorial/narration.json` (see `tools/tutorial/README.md`) |

In the pages, `data-i18n="index.tagline"` takes its content from the
catalog, `data-i18n-title` its tooltip, `data-i18n-page="guide"` links to
that page in the visitor's language, and `data-lang-links="guide"` lists the
page in the other languages. Scripts use `conquerI18n.t('index.m_ready',
{ done: 3, total: 5 })`; `{name}` is filled in by the page. Texts are
static markup of this site: they may hold `<strong>`, `<kbd>`, `<a>`.

## Adding a language

Say French (`fr`):

1. `web/i18n/fr.json`: a copy of `en.json` with the texts in French.
   `_language` is the language's own name ("Français"). Keep the keys,
   the `{placeholders}` and the markup.
2. `web/site.js`: add `{ code: 'fr', name: 'Français', pages: [] }` to
   `LANGUAGES` (and `dir: 'rtl'` for Arabic, Farsi, Hebrew...).
3. When the tutorial is translated (`tools/tutorial/i18n/fr.json`, then
   `python3 tools/tutorial/build.py`), add `'tutorial'` to `pages`; when
   `guide.fr.html` exists, add `'guide'`.
4. The terminal menu: `conquer/i18n/fr.sh` (see its README).
5. `python3 tools/check-i18n.py` lists missing and unknown texts in every
   language.

Game screens stay as the original English ones.
