# First-turn tutorial

`web/tutorial.html` (the page), `web/tutorial/first-turn.cast` (the terminal
recording) and `web/tutorial/first-turn.json` (the steps for the in-game
coach) are generated from a real game session.

| File | What it is |
|------|------------|
| `first-turn.steps.json` | The keys pressed at each step, with the text that must be on screen |
| `first-turn.content.json` | The explanation of each step, and the screen text the coach waits for |
| `tutorial.template.html` | The page; the steps go where `<!--steps-->` is |
| `record.py` | Plays the steps in the running game container and records the session |
| `build.py` | Writes the page and the coach steps |
| `video.sh` | Renders the narrated videos (MP4 + captions) |

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
