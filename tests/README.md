# Tests

```bash
python3 -m pip install pytest                 # and playwright, for the browser tests
python3 -m pytest -m "not browser and not game"   # fast: no browser, no game
python3 -m pytest -m game                     # the game container conquer-local running, and pyte
python3 -m pytest -m browser                  # Chromium: python3 -m playwright install chromium,
                                              # or CHROMIUM=/path/to/chrome
```

| File | What it checks |
|------|----------------|
| `test_coach.py` | The coach (`web/coach.js`) follows the recorded game screens step by step, in every language; the builder track and key bar; `conftest.Coach` is a Python copy of the coach's rules |
| `test_narration.py` | Every shot of the narrated videos shows a recorded screen; the languages match English |
| `test_i18n.py` | `tools/check-i18n.py` passes |
| `test_game.py` | The game's nation builder, played again in the game container (or `RECORD_LOCAL=1`), shows the screens the coach and the video were made from |
| `test_browser.py` | `game.html` replays the nation builder recording (`fake/play.html` stands in for ttyd): the coach and key bar follow it, resizing never cuts the game screen; `signup.html` offers the builder video |

The recordings they use come from `tools/tutorial/record.py` (see
`tools/tutorial/README.md`): record again when the game's screens change.
CI runs the fast tests in the lint job, the game test in the smoke job and
the browser tests in their own job.
