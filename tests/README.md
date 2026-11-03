# Tests

Markers: `browser` (Chromium) and `game` (the game container running); the rest runs anywhere.

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
| `test_compose.py` | The compose files keep numeric settings literal (docker-compose 1.29 passes `${VARIABLES}` to Docker as strings) |
| `test_offsite.py` | `offsite-backup.sh` keeps the newest copies by name and prunes a directory target (no network; the SSH and rsync targets use the same selection) |
| `test_game.py` | The game's nation builder, played again in the game container (or `RECORD_LOCAL=1`) at turn 1 and one turn later, shows the screens the coach and the video were made from |
| `test_browser.py` | `game.html` replays the nation builder recording (`fake/play.html` stands in for ttyd): the coach and the touch bar follow it, resizing never cuts the game screen, arrow keys move; the touch layer (`web/touch.js`) on `try/` and `game.html`: the screen classifier against the recorded screens, the grid over the terminal before and after zoom, tap to move, edge and two-finger scroll, pinch and pan, the chips following the screen, options kept across a reload, texts in Spanish and Chinese, no console errors (`TOUCH_SHOTS=<folder>` also writes screenshots at three sizes); `try/` runs the game under the VPS's security policy; `signup.html` offers the builder video and shows the pending or approved panel from the stubbed `/join/api/request`; the home page call to action follows `status.json`; `admin.html` renders the stubbed `/admin/api/state` and posts Approve, Reject and invite requests |

The recordings they use come from `tools/tutorial/record.py` (see
`tools/tutorial/README.md`): record again when the game's screens change.
CI runs the fast tests in the lint job, the game test in the smoke job and
the browser tests in their own job.
