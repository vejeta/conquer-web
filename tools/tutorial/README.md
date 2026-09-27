# First-turn tutorial

`web/tutorial.html` and `web/tutorial.es.html` (the page in English and
Spanish), `web/tutorial/first-turn.cast` (the terminal
recording) and `web/tutorial/first-turn.json` (the steps for the in-game
coach) are generated from a real game session.

| File | What it is |
|------|------------|
| `first-turn.steps.json` | The keys pressed at each step, with the text that must be on screen |
| `first-turn.content.json` | The explanation of each step, and the screen text the coach waits for |
| `tutorial.template.html` | The page; the steps go where `<!--steps-->` is, and each `{{name}}` is a text of the page |
| `i18n/<language>.json` | The page's texts in each language and, but in English, the steps' title, text and veteran note by step id |
| `record.py` | Plays the steps in the running game container and records the session |
| `build.py` | Writes the page and the coach steps |
| `video.py` | Renders the narrated videos (MP4 + captions) |

To record again, on a world at turn 1 with a new nation `tidewater`
(password `tide123`) linked to the account `maren`, and the game container
running as `conquer-local`:

```bash
python3 tools/tutorial/record.py tools/tutorial/first-turn.steps.json \
    web/tutorial/first-turn.cast tools/tutorial/first-turn.screens.json
python3 tools/tutorial/build.py
```

`record.py` needs the `pyte` Python module and stops with an error when a
screen is not the expected one (for example, when a random start places
the capital with water to the south: pick another direction in the steps).

## Narrated videos

`video.py` turns the recording into `web/tutorial/first-turn.en.mp4` and
`first-turn.es.mp4`, with captions (`.vtt`). The narration is in
`narration.json`, one segment per step plus an opening and a closing; each
shot holds the step's screen for as long as the narrator speaks. The voices
(`bm_george` in English, `em_alex` in Spanish) come from Kokoro, an
Apache-2.0 neural text-to-speech model that runs offline; `narration.json`
also sets their speed.

```bash
python3 -m pip install kokoro-onnx soundfile   # once; the model (~350 MB)
                                               # downloads on first use
python3 tools/tutorial/video.py en es          # needs ffmpeg and node + playwright
```

To use a human voice instead, record one audio file per segment with the
same text and replace the synthesis in `render()`.

## Another language

Each page shows the video of its own language (`<html lang>`). To add one,
say French (`fr`):

1. `i18n/fr.json`: a copy of `i18n/es.json` with every text in French
   (`language` is the language's own name, "Français"). A text or step left
   out is shown in English. `build.py` then writes `web/tutorial.fr.html`
   and `web/tutorial/first-turn.fr.json`, and links every tutorial page to
   the others.
2. The rest of the site: see `web/i18n/README.md` (the language list in
   `web/site.js`, where `pages` gets `tutorial`).
3. The narrated video: an `"fr"` text (and `title_fr`) in every segment of
   `narration.json` and a voice under `voices`, the video's captions in
   `TEXT` in `video.py`, then `python3 tools/tutorial/video.py fr`.
