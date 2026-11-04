# Security

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

What Conquer Web protects, from whom, how, and what it does not do. It
describes the code in this repository; a server you run is only as safe as
its host and its settings, see "Hardening a server" below.

## Reporting a problem

Please do not open a public issue for a vulnerability. Use GitHub's private
reporting (Security tab of <https://github.com/vejeta/conquer-web>, "Report a
vulnerability"), or write to the maintainer (address in `AUTHORS.md`) with
what you found, how to reproduce it and which version. You get an answer
within a few days; a fix is released before details are published. Never
include a real password or a player's data in a report.

## Threat model

| Who | Trusted with | Not trusted to |
|---|---|---|
| Host root (the person running the VPS) | everything: the host, Docker, Apache, the account file, the world | (trusted) |
| The game user inside the container (`conquer`, uid 1000) | the world files, `lib/.players`, the account file, the mail settings in its environment: gate, ttyd, menu, game and cron all run as it | (trusted, and it is the boundary below) |
| Administrators of the site (accounts marked `*` in `lib/.players`) | approving or rejecting seats, making invite codes, opening any nation at its password prompt | anything on the host |
| Players (approved accounts) | their own nation, once they give its password; a practice world of their own | other nations, other accounts, the files, a shell |
| Visitors (nobody, or a pending account) | asking for a seat; the public pages and status; no terminal (a pending account is turned away by the menu) | everything else |

The main boundary is between a player and the game user. Players get a
terminal menu, never a shell: if they could break out of it they would be the
game user and could edit the world, the accounts and the administrators. The
controls below exist to keep that boundary, and to keep visitors from
becoming players without the administrator's approval.

## Controls, layer by layer

### Browser and Apache (`vps/virtualhost.conf.template`, `apache/local.conf`)

- HTTPS only; the plain HTTP vhost redirects (and serves Let's Encrypt
  challenges). TLS 1.2+ with AEAD ciphers, HSTS (one year), no session tickets.
- Headers: `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`,
  `Referrer-Policy`, and a Content-Security-Policy (`default-src 'self'`,
  `frame-ancestors 'self'`, `object-src 'none'`, `base-uri 'self'`,
  `form-action 'self'`; inline scripts are still allowed, the pages use them).
- `/play/` and `/admin/` require a valid account: a sign-in page of the site
  (`/login.html`, mod_auth_form form login against the same htpasswd file) and a
  session cookie. They are the last `<Location>` blocks of the vhost; CI checks
  that `/play/` stays last, because a later block could silently lift the
  password.
- Session cookie `conquer_session`: `httponly` (scripts cannot read it),
  `secure` (https only), `samesite=lax`, `path=/`. Its content is the account and
  the password encrypted (AES-256, mod_session_crypto) with the passphrase in
  `/etc/apache2/conquer-web.session` (mode 600, never in git; changing it signs
  everybody out). Plain sign-in: a browser-session cookie (no expiry on the
  server side either); "Remember me": 30 days from the login (`/login/long`,
  `SessionMaxAge 2592000`). `/logout` replaces the cookie with an expired empty
  one; a copied cookie keeps working until it expires or the passphrase changes.
  `SessionCookieRemove On` hides the cookie from the game and the gate.
- Identity: Apache sets `X-WEBAUTH-USER` from the signed-in account after
  `RequestHeader unset X-WEBAUTH-USER early`, so a header sent by a client never
  survives. ttyd (`-H X-WEBAUTH-USER`) answers 407 to a request without it; the
  gate treats the header as the administrator's identity. Only Apache may reach
  ports 7681 and 7682: the local setup does not publish them, the VPS setup
  binds them to `127.0.0.1`.
- Cross-site WebSocket hijacking: a browser sends a player's saved password
  with a WebSocket that any web page opens. Apache refuses a WebSocket to
  `/play/` whose `Origin` is not this site (403, before any proxying).
- Requests: 1 MB body limit, 60 s timeout, sensitive file names and
  `.git`/`.env` denied, noisy bots blocked.
- The pages put server text in the DOM with `textContent` (account names,
  emails and messages on the administrator page, nation names and news on the
  landing page); the news pages escape HTML.

### Sign-up service (`conquer/gate`, Go, standard library only)

- Public: `POST /join/api/request` and `/signup`. Administrator: `/admin/api/*`,
  allowed only when `X-WEBAUTH-USER` names an account marked exactly `*`.
- Account names: letters, digits, `. _ -`, 1 to 32 characters, **starting with a
  letter or digit** (so never an option for `htpasswd`, never `.` or `..`);
  `god root admin conquer join` are reserved. The same rule is in the gate,
  `signup.sh` and `manage-players.sh`, and `tests/test_security.py` checks it.
- A request cannot take an existing name (account file and `.players` are both
  checked under a lock), cannot be `*`, and approving or rejecting works only on
  accounts marked `?` (waiting).
- Passwords: 8 to 72 bytes on one line, passed to `htpasswd -niB -C 10` on
  standard input (never in a command line or a log), stored as bcrypt.
- Sizes: request body 8 KB, message 500 characters on one line, email 120
  characters with no whitespace, quotes, commas, angle brackets; language from a
  fixed list.
- Rate limits per client address (the one Apache adds last to
  `X-Forwarded-For`): 20 requests per 10 minutes, 5 wrong or malformed invite
  codes per hour, 120 administrator actions per 10 minutes. At most 200
  requests wait for approval at once, after which the page says sign-up is
  closed.
- Against a script filling that queue (`abuse.go`): a second limiter lets one
  address make **3 pending accounts per 24 hours** (counted only when the
  account was created, so typos do not use it up; invite codes are not
  requests); a hidden `website` field that people never fill (a request that
  fills it is dropped); a minimum fill time (the form fetches
  `GET /join/api/token`, a timestamp signed with HMAC-SHA-256 together with the
  client address, and sends it back in `X-Form-Token`; a request that is
  missing the token, forged, from another address, older than 48 hours or
  younger than 3 seconds is dropped); and one waiting request per email
  address (case ignored). A dropped request gets the normal "pending" answer so
  a script cannot tell, and the gate logs it (`signup dropped: ...`). The
  signing key is kept in `lib/.gate-secret` (mode 600). Settings:
  `SIGNUP_DAILY_LIMIT` (3), `SIGNUP_MIN_FILL` in seconds (3; 0 turns the token
  check off), `SIGNUP_EXPIRE_DAYS` (30).
- Requests nobody decides are removed after 30 days, with their account in the
  account file and `.players` (`conquer-signup expire`, run by the gate two
  minutes after it starts and then every 24 hours; logged as `expire: ...`).
- POSTs are refused when the browser's `Origin` is another site.
- Invite codes: 8 characters from a 32-letter alphabet read from
  `/dev/urandom` (40 bits), stored in `lib/.invites`, used once (removed under
  the lock together with the account creation), guessable only at five tries an
  hour per address.
- Mail (`notify.go`): the recipient is the administrator's configured address,
  or the visitor's address after approval; subject is one encoded line, no
  header can be injected (addresses and text cannot carry a line break), the
  body is plain text. SMTP uses STARTTLS or implicit TLS with certificate
  verification unless `SMTP_STARTTLS=off`. The webhook gets only the account
  name and the admin URL.

### Scripts and the terminal menu (`conquer/scripts`)

- No shell for players: ttyd runs `conquer-menu` directly, not a shell. The menu
  reads a key at a time and calls fixed programs. A Ctrl-C ends the menu and the
  ttyd session; there is no shell to fall back to.
- The pager for the scores runs with `LESSSECURE=1` and `LESSKEY=/dev/null`, so
  `!`, `|`, `v`, `:e` and `s` do nothing (checked by hand, and CI-checked that
  every pager call sets it). The game itself has no shell escape: its few
  `system()` calls use fixed commands and names the game builds.
- The nation builder runs under `env -i`, with CPU and file size limits and a
  time limit, once per account, for accounts marked `+`.
- Values from the network reach the scripts as arguments or standard input, never
  through `eval` or a shell string. Everything that goes into the tab- or
  colon-separated files (`.players`, `.requests`, `.invites`, the account file)
  is validated first: names by the rule above, free text collapsed to one line.
- The language of the menu (`/play/?arg=`) is used only if it matches a language
  code that has a catalog file.
- Practice worlds live in `practice/<account>`; the directory name is sanitized
  and never `.` or `..` (the menu deletes and recreates it).
- Nation names are typed by the player and the game accepts any printable
  character. `conquer-join` links a nation to the account only if the name is
  letters, digits, `. _ -` (up to 9): a name like `*:x` would otherwise read as
  an administrator in `.players`. Otherwise the account waits until the
  administrator assigns the nation.
- State files are updated under `flock`; the account file is rewritten in
  place so the bind mount keeps working.

### Container (`docker-compose.*.yml`, `conquer/Dockerfile`, `entrypoint.sh`)

- The entrypoint runs as root only to prepare volumes and cron; ttyd, the gate,
  the menu, the game and every turn update run as uid 1000 (`setpriv`). PID 1
  holds no capability (CI checks it).
- `cap_drop: ALL` with only what the root part of the entrypoint needs,
  `no-new-privileges`, `pids_limit`, `mem_limit`, log rotation.
- ttyd: at most `MAX_CLIENTS` terminals at once (25 in the production
  template), pinned release with a checked SHA-256. `SESSION_TIMEOUT` is
  ttyd's WebSocket ping interval, not an idle timeout.
- The menu (`menu.sh`) limits what a terminal can hold: an account still
  waiting for approval (`?` in `lib/.players`) gets a message and the
  terminal closes at once, so waiting accounts cannot occupy the places; one
  terminal per account (`flock` on `/run/conquer/session-ACCOUNT.lock`: a
  second tab is told the account is open elsewhere and closes); a menu with
  no key for 15 minutes (`MENU_IDLE_TIMEOUT`, seconds) closes itself. The game
  itself, once started, is not timed.
- The gate is a static Go binary built in a separate stage; the image has no
  compiler.
- Backups made before each turn are mode 600 in a 700 directory (they hold the
  nations' password hashes, emails and unused invite codes).

### Host

- Ports published on `127.0.0.1` only (VPS). The account file is owned by the
  game user and the `www-data` group, mode 640.
- `manage-players.sh` and the other tools that run as root on files the game
  user owns refuse symbolic links in the world directory.
- `update-vps.sh` runs git as the owner of the checkout, and its backups are in
  a 700 directory under `/root`; `offsite-backup.sh` encrypts what it sends.
- `check-security.sh`, `setup-security-basic.sh` and `setup-security.sh` install
  and report fail2ban.

### Data published on purpose

`status/status.json`, `history.json` and the news pages hold the turn, the
schedule, nation names, race, class, alignment, scores, and the news with the
captured-sector list left out. They never hold account names, emails, requests
or the invite codes. `ADMIN_CONTACT`, if you set it, is public.

### CI

`ci.yml` has read-only repository permissions, no secrets, no `set -x`; its
only password is the throwaway `ci-password` of a container that exists for the
run. It checks the Apache sign-in rule (redirect to the sign-in page, session
cookie flags, logout), a forged identity header or cookie, the
WebSocket origin check, the container's capabilities and the sign-up and
approval flows. A step fails if the password shows up in a container log.

## Known limits

- **Session cookie.** It holds the encrypted password (mod_auth_form does not
  keep server-side sessions), so a stolen cookie works until it expires, a
  logout does not revoke a copy of it, and "Remember me" lasts 30 days: it
  is the browser's saved password again, but httponly and encrypted. There is
  no second factor and no lockout inside the application; a logout link
  can be followed from another site (samesite=lax allows top-level GET) and
  only signs the visitor out.
  Brute force is limited only by fail2ban if you install it (below). Use long
  passwords; the sign-up page asks for 8 or more, bcrypt uses the first 72 bytes.
- **Everything in the container is one user.** The gate, ttyd, the menu, the game,
  cron and the mail password (`SMTP_PASSWORD` is in the container environment)
  share uid 1000. A way out of the menu would give the world, the account file
  and the administrators' marks. The second line of defense is that the
  container has no capabilities and cannot gain any.
- **The identity header is trusted from whoever can reach ports 7681 and 7682.**
  That is Apache only, on the local Docker network or on the VPS loopback. Other
  local users of the VPS, or another container on the same Docker network, could
  send `X-WEBAUTH-USER` themselves.
- **No idle timeout inside the game.** The menu closes after 15 minutes
  without a key, but a game that was started keeps its place until the browser
  closes it; `SESSION_TIMEOUT` is only a ping interval.
- **No shared-secret header between Apache and the gate/ttyd.** The network
  position above is the only check on `X-WEBAUTH-USER`.
- **The container's root filesystem is writable** (it is not `read_only`),
  though the game user can write only to its own directories.
- **The lock files live in `/run/conquer`,** a directory the game user owns, so
  a process of that user can hold the join and account locks.
- **Waiting accounts still sign in to Apache.** A visitor's account exists
  (`?`) as soon as the request is made and passes the Apache login; the menu
  turns it away, but each connection takes a `MAX_CLIENTS` place for a moment.
  Approved players can still hold `MAX_CLIENTS` places with one account each.
- **Accounts can be guessed from the sign-up page** ("name taken"), as on any
  site that lets you choose a name.
- **Passwords in the game.** Conquer keeps at most 7 characters of a nation's
  password as a DES `crypt` hash in the world file. Anyone who reads a world
  file or a backup can guess them offline. God's password is the strongest case,
  see below. Treat `data/lib` and `data/backups` as secrets.
- **The shipped worlds.** `conquer/lib` and `conquer/practice-world` ship with
  god and every sample nation locked (`conqpasswd -l`), so no password opens
  them; CI checks this. The one exception is `trainee` in the practice world,
  which is public on purpose (`train1`).
- **Personal data.** Emails and messages are kept in `lib/.requests` until the
  request is decided, and in backups. The gate logs the account name and the
  client address of sign-ups and refusals.
- **Git history.** The first commits held a self-signed certificate key for
  `conquer.local` and, in the first world files, a god password hash. Neither is
  in use; do not reuse that password anywhere.
- **The administrator page** is protected by the same account system as the
  game; one stolen administrator password approves seats and makes invite codes.

## Hardening a server

- Keep the game user's uid equal to the owner of `data/` so backup scripts need
  no root, and keep `data/` and `/etc/apache2/conquer-web.htpasswd` unreadable
  to other users (`chmod 700 data`).
- Install fail2ban: `sudo ./setup-security-basic.sh` (standard Apache filters:
  failed logins, bad bots) or `sudo ./setup-security.sh`, then
  `./check-security.sh` to see the bans. The authentication jail should watch
  `conquer_*_error.log` for `AH01617`/`AH01618` and ban after about five misses.
  Do not ban on every `200` or `206` of the access log: the tutorial videos are
  served in ranges.
- Set `SMTP_STARTTLS` on (the default), and give the mail account only the right
  to send.
- Put a limit on connections per account or per address in front of `/play/` if
  you see abuse (`mod_qos`, `mod_evasive`, or the firewall).
- Set the god password after the first start: `./set-nation-password.sh god`.
- Update the base image and rebuild now and then (`./update-vps.sh --rebuild`);
  ttyd and the Debian image are pinned, not auto-updated.
- Back up `data/` and the account file; restore only archives you made. An
  archive made by the game user is treated as untrusted when restored as root.

## Late nations and god's password

The game's nation builder (`conqrun -a`) asks for the super user (god)
password once the game is past turn 5, so that on a classic multi-user host
not just anybody with a shell can add a nation to a running world. This
server does not use that prompt: `conquer/patches/0004` adds `conqrun -A`,
which behaves like `-a` (same locks) but does not ask, and the terminal
menu runs it for accounts the administrator approved.

This does not weaken the world:

- Inside the container everything runs as the one game user, who can edit
  the world files directly. The password prompt never protected the world
  from that user, only from players with shell access on a multi-user host.
- Players never get a shell. They reach `conqrun` only through
  `conquer-join`, which runs the builder only for an account marked `+` in
  `lib/.players` (approved at `/admin/` or with `manage-players.sh approve`)
  and only once per account.
- Approval is therefore the only gate. Keep administrator accounts and the
  approval page protected as described above; `conqrun -a` still asks for
  god's password if someone runs it past turn 5.

A nation that starts late gets the game's own extra points
(`newlogin.c`, "points added for starting late").

## Checklist

- [ ] HTTPS works, HSTS header present, `/play/` and `/admin/` redirect (302) to `/login.html` without a session; the cookie is httponly, secure and same-site
- [ ] God password set on the server (`conqpasswd -q god` says "set")
- [ ] fail2ban installed and `./check-security.sh` clean
- [ ] Administrator accounts few, with long passwords
- [ ] `data/` and the account file not readable by other host users
- [ ] Backups (`data/backups`, off-site) work and a restore was tried
- [ ] `docker compose ps` shows the game ports bound to `127.0.0.1` (VPS) or not published (local)
