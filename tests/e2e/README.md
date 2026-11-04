# End-to-end rehearsal

An automated rehearsal of the whole player journey, with several players at
once, on the Docker stack that CI's `smoke` job builds and runs: real Apache,
the form login, the gate (`conquer-gate`), ttyd and the game.

**Staging is the default.** It is the local stack plus a mail catcher
(Mailpit), on a throwaway world and a throwaway administrator, and nothing
leaves the machine. **Production mode is optional** and only for the day you
want the real server in the picture (see the end).

| File | What it is |
|------|------------|
| `../../docker-compose.e2e.yml` | Override of `docker-compose.local.yml`: Mailpit (SMTP 1025, web and API on 127.0.0.1:8025), the gate's `SMTP_*`, `NOTIFY_EMAIL` and `SITE_URL` pointed at it, 60 simultaneous sessions, no early turn update |
| `up.sh`, `down.sh` | Bring the staging stack up (with a random administrator password, in `.run.env`, never committed) and take it down |
| `test_journey.py` | The journey, N players in parallel (Playwright, pytest) |
| `soak.py` | Game bots (pexpect, no browser), 10 nations for N turns, season end, backup and restore |
| `load.py` | K concurrent game sessions through ttyd behind Apache; prints memory and CPU |
| `prod-rehearsal.sh` | The journey on the live server, with a backup first and a restore at the end |
| `e2e_support.py` | Shared helpers: the administrator's session, the mail catcher's API, the game container, a driver for the terminal in the browser |

## Run it on your machine

```bash
python3 -m pip install -r tests/e2e/requirements.txt
python3 -m playwright install --with-deps chromium

tests/e2e/up.sh --wipe-data        # builds and starts the stack; deletes ./data of THIS checkout
set -a; . tests/e2e/.run.env; set +a

python3 -m pytest tests/e2e/test_journey.py      # the journey; E2E_PLAYERS=6 by default
python3 tests/e2e/soak.py --turns 8              # bots; 25 turns by default
python3 tests/e2e/load.py --sessions 10          # 30 sessions for 120 s by default

tests/e2e/down.sh --wipe-data
```

`up.sh` refuses to start on a world that is already in `./data`: pass
`--wipe-data` only when that world is throwaway. Without `E2E_BASE_URL` and
the administrator's password (from `.run.env`) the tests skip, so a plain
`pytest` never needs the stack.

The stack relaxes only what six players from one address would trip:
`SIGNUP_DAILY_LIMIT=1000` and `NOTIFY_DIGEST_SECONDS=0` in
`docker-compose.e2e.yml`. The sign-up form's minimum fill time (3 s) and the
honeypot stay on: the journey waits 3.3 s with the form filled before it
presses the button, as a person would.

## What the journey checks

Each player runs in its own thread and browser context, with a mix of Pixel 7,
iPhone 13 and desktop (1280x800) profiles and Spanish, English and German
pages. Per player:

1. ask for a seat on `signup.html`; the administrator approves through
   `/admin/api/approve`; the mail catcher holds the administrator's notice
   (the player gives no email and is not mailed: after the approval the
   player opens the site and signs in)
2. the Doors form (`login.html` to `/login/do`): a wrong password first for one
   player; the cookie is `HttpOnly` and `Secure`
3. the sound: music and effects on, every sound file loads
4. found a nation in the game's builder: distinct races (Human, Elf, Dwarf, Orc)
   and classes, the nation password of 2 to 7 characters (the touch layer's
   hint is checked, too short and too long are refused by the game), through the
   touch layer's chips (even players) or by keyboard (odd players); the
   screen is read through the xterm buffer; the world and `.players` are
   checked for the new nation
5. on the map: tap to move, the d-pad, arrow keys and letters, reports on
   parchment (budget, armies), a message to another player's nation; the
   orders question at the end (with Yes and No chips in every language)
6. a turn update is forced (`conquer-turn --now`, as the smoke job does); every
   player signs in again: the turn moved, the treasury changed, the newspaper
   tells the previous season, the other nation's message arrived
7. one more player asks for a seat after turn 5 (the builder's `-A`, "points
   added for starting late")
8. sign out: the cookie is gone and `/play/` redirects to the login page

No console error and no failed request (other than the favicon) is allowed on
the game page. When a step fails, a Playwright trace (`npx playwright
show-trace`), a video and a screenshot of that player are kept in
`test-results/e2e/<account>/`.

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `E2E_BASE_URL` | from `.run.env` | The site the browsers open |
| `E2E_ADMIN_USER`, `E2E_ADMIN_PASSWORD` | from `.run.env` | An administrator of that site |
| `E2E_MAILPIT_URL` | `http://127.0.0.1:8025` | The mail catcher; empty: no mail checks |
| `E2E_CONTAINER` | `conquer-local` | The game container |
| `E2E_PLAYERS` | 6 | Players in the journey (one more joins late) |
| `E2E_SOAK_TURNS`, `E2E_SOAK_NATIONS` | 25, 10 | The soak |
| `E2E_LOAD_SESSIONS`, `E2E_LOAD_SECONDS` | 30, 120 | The load |

## Soak and load

`soak.py` founds ten nations with `conqrun` on a pseudo terminal, then for each
turn every bot signs in to `conquer -n NATION` (all at once), makes two to
four random moves (move an army, draft, build, a report, walking), quits, and
`conquer-turn --now` runs the real update. After each update: the turn
advanced, no core file, the world files are not empty, `conquer-status
--nations` and `status.json` are valid, the container log has no crash. At the
end: `season-end.sh` (the season is listed in the hall of fame), then
`backup-world.sh`, one more turn, `restore-world.sh`: the turn and the nation
list are the ones of the backup. Needs `sudo` for the files in `data/`.

`load.py` makes one administrator account per session (removed at the end),
signs each in with the form, opens the practice world from the menu through
`wss://.../play/ws`, and types keys for the given time. It prints the time to
reach the map, traffic, and the average and peak CPU, memory and processes of
the game and Apache containers (`docker stats`). It fails only when more than
5 % of the sessions had an error or a timeout.

## CI

The `e2e` job of `.github/workflows/ci.yml` runs staging, the journey, the soak
(8 turns) and the load (10 sessions, 60 s) on every pull request and on manual
runs; a nightly run does the full soak (25 turns) and the load with 30
sessions for 2 minutes. The results folder is uploaded when the job fails.

## Production mode (optional)

Only if you want the rehearsal on the live server. **Staging above is the
normal way and needs none of this.** Run it on the server, when nobody is
playing:

```bash
python3 -m venv .e2e-venv && . .e2e-venv/bin/activate
pip install -r tests/e2e/requirements.txt && playwright install --with-deps chromium
sudo -v
tests/e2e/prod-rehearsal.sh --yes-i-have-a-backup --base-url https://your-domain \
    [--players 4]
```

The script refuses to run without `--yes-i-have-a-backup` and while anyone is
in the game. It makes a world backup itself (`backup-world.sh`) and records the
existing accounts (names only). It creates a throwaway administrator
(`e2e-admin-xxxxxx`) and runs the journey with test accounts called
`e2e-<random>`. At the end, always (also when the journey fails or you press
Ctrl-C), it stops the game, restores that backup with `restore-world.sh`,
deletes every `e2e-*` account (web accounts, `.players` marks, `.requests`),
starts the game again, and prints what it cleaned and whether the accounts
and the turn are as before. The backup stays in `backups/`.

Things to know:

- It forces turn updates on the live world (the journey needs one, and the
  late joiner needs the world past turn 5); the restore takes the world back,
  and `status.json` is published again. The seasons' hall of fame, news files and
  mail sent by the game are inside the world backup.
- Mail: the mail catcher does not exist there, and players are never mailed.
  If `NOTIFY_EMAIL` is set you still get the administrator's notice for
  every request: the game has no switch to turn that off.
- `E2E_BASE_URL` must be the site the browsers should open. A server with a
  virtual host per domain does not serve the game at `https://localhost`.
- The accounts and passwords of the rehearsal are random and are never written
  to a file.

## Not covered

The Android app, Safari and Firefox (the iPhone profile runs in Chromium), real
mail delivery (spam filters, SPF, DKIM), the certificate renewal, the off-site
backups, a real phone's soft keyboard, two players in the same sector fighting
a battle, and runs longer than a nightly soak.
