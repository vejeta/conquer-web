# First-turn tutorial

`web/tutorial.html` and `web/tutorial.es.html` (the page in English and
Spanish), `web/tutorial/first-turn.cast` (the terminal
recording) and `web/tutorial/first-turn.json` (the steps for the in-game
coach) are generated from a real game session.

| File | What it is |
|------|------------|
| `first-turn.steps.json` | The keys pressed at each step, with the text that must be on screen |
| `first-turn.content.json` | The explanation of each step, and the screen text the coach waits for |
| `first-turn.content.es.json` | The same steps in Spanish |
| `tutorial.template.html` | The page; the steps go where `<!--steps-->` is, and each `{{name}}` is a text of `tutorial.strings.json` |
| `tutorial.strings.json` | The rest of the page's text, per language |
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

1. `first-turn.content.fr.json`: a copy of `first-turn.content.json` with
   `title`, `text` and `veteran` translated (keep `id`, `keys`, `detect`).
2. `tutorial.strings.json`: an `"fr"` entry with every text of `"en"`.
3. `build.py`: `"fr": ("first-turn.content.fr.json", "tutorial.fr.html", None)`
   in `LANGUAGES`.
4. `narration.json`: an `"fr"` text (and `title_fr`) in every segment and a
   Kokoro voice under `voices`; the video's captions in `TEXT` in
   `video.py`; then `python3 tools/tutorial/video.py fr`.
5. A link to `tutorial.fr.html` next to the other languages in the crumbs of
   `tutorial.strings.json`.
