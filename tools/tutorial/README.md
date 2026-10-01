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
| `narration/<language>.json` | What the narrator says over each shot, the words on the frames, and the voice |
| `narration/voices/<language>.wav` | The designed narrator of a language (see *Voices*) |
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

### The nation builder

The coach also follows the game's own nation builder (`conqrun -a`), which
a new player meets the first time they play. Its steps are
`found-nation.content.json` (and `found_title`, `found_steps` in
`i18n/<language>.json`); `build.py` writes `web/tutorial/found-nation[.language].json`.
`found-nation.steps.json` records the builder founding `iberia` on a world
at turn 1 (the builder never asks for an account):

```bash
python3 tools/tutorial/record.py tools/tutorial/found-nation.steps.json \
    web/tutorial/found-nation.cast tools/tutorial/found-nation.screens.json
```

`RECORD_LOCAL=1` records from a game installed in `/opt/conquer` on this
machine, as the user `conquer`, instead of the container.

## Narrated videos

`video.py` turns the recording into one video per language,
`web/tutorial/first-turn.<language>.mp4`, with captions (`.vtt`). The
tutorial page of each language plays its own video; a language without one
shows the terminal recording instead.

### What a video is made of

- **The shots:** one per narration segment (an opening, one per step, a
  closing). Each shows the recorded 80x24 game screen of that step
  (`first-turn.screens.json`) with the step's number, title and keys,
  rendered as a 1280x720 frame by Chromium (`frames.js`), and is held for as
  long as the narrator speaks.
- **The narration:** `narration/<language>.json`:
  - `segments`: the spoken `text` of each shot (numbers and keys written the
    way they are said, e.g. "capital R") and, for the steps, the `title`
    shown on screen (if missing, the tutorial's own title);
  - `captions`: the words on the frames ("Keys", the opening and closing
    titles...);
  - `voice`: the text-to-speech engine and voice (below).
- **The captions (`.vtt`):** the spoken text, timed to the audio.

### Voices

Every engine runs offline and has a license that allows publishing the audio
(see `docs/languages.md` for the comparison):

| `engine` | Model | Voice settings |
|----------|-------|----------------|
| `qwen-custom` | Qwen3-TTS 1.7B CustomVoice (Apache-2.0) | `speaker` (Ryan, Aiden, Uncle_Fu, Vivian, Serena, Dylan, Eric, Ono_Anna, Sohee), `language`, optional `instruct` (the tone) |
| `qwen-clone` | Qwen3-TTS 1.7B Base (Apache-2.0) | `language`, `design` (a description of the narrator) and `reference` (a sentence in the language) |
| `voxcpm` | VoxCPM2 (Apache-2.0), for languages Qwen3-TTS lacks (Polish, Turkish, Arabic, Hindi...) | `design` and `reference`, as for `qwen-clone` |
| `kokoro` | Kokoro-82M (Apache-2.0) | `voice`, `lang`, `speed` |

Qwen3-TTS speaks Chinese, English, French, German, Italian, Japanese,
Korean, Portuguese, Russian and Spanish; other languages use `voxcpm`.

A `qwen-clone` or `voxcpm` voice is designed once: the first render asks Qwen3-TTS
VoiceDesign to read `reference` with a voice matching `design`, and saves
it as `narration/voices/<language>.wav`. Every segment is then spoken in
that voice, and later renders reuse the file, so the narrator stays the
same. To choose another narrator, change `design` and delete the `.wav`.

Today: English uses `qwen-custom` Ryan, Chinese `qwen-custom` Uncle_Fu,
Spanish, German, Portuguese (Brazil) and Russian `qwen-clone` narrators
designed as native speakers, and Polish a `voxcpm` narrator designed the
same way.

### Generating the videos

Needs Python 3.10 or later, `ffmpeg`, and node with `playwright` (Chromium)
for the frames. In a virtual environment:

```bash
python3 -m venv ~/.venv/conquer-tts
~/.venv/conquer-tts/bin/pip install qwen-tts soundfile   # Qwen3-TTS voices
~/.venv/conquer-tts/bin/pip install kokoro-onnx          # only for kokoro voices
python3 -m venv ~/.venv/conquer-voxcpm                   # voxcpm voices, apart:
~/.venv/conquer-voxcpm/bin/pip install voxcpm soundfile  # other dependencies
npm install -g playwright                                # if node lacks it

~/.venv/conquer-tts/bin/python tools/tutorial/video.py            # every language
~/.venv/conquer-tts/bin/python tools/tutorial/video.py es de      # some of them
~/.venv/conquer-voxcpm/bin/python tools/tutorial/video.py pl      # voxcpm ones
```

- The Qwen3-TTS models (about 4.5 GB each: CustomVoice, Base and, to design
  a voice, VoiceDesign; VoxCPM2 about 5 GB) download from Hugging Face on first use, to
  `~/.cache/huggingface`. The machine needs to reach `huggingface.co` and
  `*.hf.co`. Kokoro's files come from GitHub, to `~/.cache/conquer-tts`.
- On a GPU a video takes a minute or two. On a 4-core CPU with 16 GB of RAM
  it takes about 15 minutes (the speech is generated about 6 times slower
  than it plays).
- Disk: the three Qwen3-TTS models take about 13 GB, VoxCPM2 about 5 GB,
  and each virtual environment (with PyTorch) about 6 GB. With little room,
  render the Qwen3-TTS languages, delete `~/.cache/huggingface`, then
  render the `voxcpm` ones.
- Every sentence spoken is kept in `~/.cache/conquer-tts/speech` (by voice and
  text): a render cut short goes on where it stopped, and changing one sentence
  speaks only that one again. Delete the folder to speak everything again.
- `FFMPEG=/path/to/ffmpeg` picks the ffmpeg binary.
- Qwen3-TTS samples its speech: two renders of the same text differ
  slightly. Listen to each video before publishing it, and render a
  language again if a sentence sounds wrong.

### The nation builder video

`video.py --video found-nation` renders `web/tutorial/found-nation.<language>.mp4`
(and `.vtt`) from `found-nation.screens.json`, with the words of
`narration/found-nation/<language>.json` spoken by the same narrator as the
first-turn video (the `voice` of `narration/<language>.json`). A segment may
name the coach `step` whose number and title it shows (when its screen is
not a step of its own) and the `keys` shown on the frame. The sign-up page
offers the video in its language, or in English.

```bash
~/.venv/conquer-tts/bin/python tools/tutorial/video.py --video found-nation en es
~/.venv/conquer-voxcpm/bin/python tools/tutorial/video.py --video found-nation pl
```

To use a human voice instead, record one audio file per segment with the
same text and replace `tts.speak()` in `render()` with reading those files.

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
3. The narrated video: `narration/fr.json`, a copy of `narration/es.json`
   with the spoken texts, titles and captions in French and a `voice` for
   the language (for `qwen-clone`, a `design` describing a native narrator
   and a `reference` sentence in French). Then
   `python3 tools/tutorial/video.py fr` (see *Generating the videos*), and
   commit the video, its captions and the designed voice.
