# VPS runbook

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

How to run Conquer Web on a Debian VPS: Apache on the host (HTTPS, accounts,
static pages) in front of one Docker container that holds the game. The
commands you type every day are in [QUICK-REFERENCE.md](QUICK-REFERENCE.md);
hardening is in [SECURITY.md](SECURITY.md).

Contents: [First install](#first-install) · [Update](#update) ·
[Configuration reference](#configuration-reference) ·
[Apache virtual host](#apache-virtual-host) ·
[Email notifications](#email-notifications) ·
[Players and requests](#players-and-requests) · [Turns](#turns) ·
[Seasons](#seasons) · [Backups](#backups) · [God password](#god-password) ·
[Troubleshooting](#troubleshooting)

## First install

You need a Debian server with root access, ports 80 and 443 open, and a
domain name whose A record points to it (check with `dig game.example.com`).
The paths are fixed: the project lives in `/home/conquer/conquer-web`, owned
by the user `conquer`, who runs the systemd service.

**1. Packages and user** (Debian's own `docker-compose` 1.29 is what the
systemd unit expects, at `/usr/bin/docker-compose`):

```bash
sudo apt update
sudo apt install -y apache2 git rsync docker.io docker-compose certbot \
    python3-certbot-apache apache2-utils curl
sudo adduser conquer
sudo usermod -aG docker conquer
```

**2. The project and its settings**, as `conquer` (log in again after the
`usermod`, so the group applies):

```bash
sudo -iu conquer
git clone https://github.com/vejeta/conquer-web.git
cd conquer-web
./setup-environment.sh          # choose 2, VPS production
```

It asks for the domain, an email for Let's Encrypt, the administrator's
username and password (a strong one; it can generate it), and an address
players see under "How to join". It writes `config/production.env` (never
committed). Review it with the [configuration reference](#configuration-reference).

**3. Deploy**, as a sudoer:

```bash
cd /home/conquer/conquer-web && sudo ./deploy-to-vps.sh
```

It enables the Apache modules, installs the web pages in
`/var/www/DOMAIN`, creates the administrator's web account (marked as an
administrator), gets the Let's Encrypt certificate through the running
Apache (so renewals work with Apache up), writes the virtual host from
`vps/virtualhost.conf.template`, builds the game image, installs and starts
the `conquer-web` systemd service, asks for the [god password](#god-password)
and checks the result.

**4. Afterwards**: open `https://DOMAIN/`, sign in at `/admin/` with the
administrator account, check `sudo ./health-check.sh`, allow only SSH, 80
and 443 in the firewall, and run `sudo ./setup-security.sh` (fail2ban and
rate limiting, see SECURITY.md). Then set up [backups](#backups). Certbot's
systemd timer renews the certificate (`systemctl list-timers certbot.timer`,
`sudo certbot renew --dry-run`); the deploy script installs a hook that
reloads Apache after each renewal.

Service control: `sudo systemctl status|restart|stop conquer-web`, logs with
`docker logs -f conquer-vps` or `sudo journalctl -u conquer-web`.

## Update

```bash
cd /home/conquer/conquer-web
sudo ./update-vps.sh              # rebuilds the game only if it changed
sudo ./update-vps.sh --rebuild    # always rebuilds it
sudo ./update-vps.sh --branch master   # follow another branch from now on
```

It never changes web passwords, nation passwords or the world. In order:

1. Saves `config/production.env`, the accounts file and the world in
   `/root/conquer-backups/TIMESTAMP/` (the last 10 are kept).
2. Pulls the branch the checkout follows (`git pull --ff-only`, run as the
   checkout's owner; `--branch` switches once and refuses local changes).
3. Rebuilds the game container and restarts the service if `conquer/` or
   `docker-compose.vps.yml` changed since the last build it made, or with
   `--rebuild`.
4. Installs the web pages in `/var/www/DOMAIN` (the `status/` folder is the
   game's and is left alone).
5. Checks the Apache virtual host and tells you what is missing: the
   `Cache-Control` rule for pages, `'wasm-unsafe-eval'` in the
   Content-Security-Policy (added for you, with `apache2ctl configtest` and
   a rollback if Apache refuses it), `/join/api/` and `/admin/`
   ([virtual host](#apache-virtual-host)). Missing proxy and admin blocks are
   only reported: copy them from the template yourself.
6. Checks that the running container is the current version, warns if the
   god password is not set, and that `https://DOMAIN/` answers 200.

A script that ends with a red line (`❌`) needs attention before you tell
anybody the site is up: see [Troubleshooting](#troubleshooting).

## Configuration reference

`config/production.env` is read by the systemd service and the scripts; after
editing it, `sudo systemctl restart conquer-web` (the game reads it at start,
and the home page shows the new values then). `config/production.env.template`
has the same list. Keep the file readable only by the `conquer` user: it holds
the administrator password and the mail password.

**Site**

| Variable | Meaning |
|----------|---------|
| `DOMAIN` | The site's domain; names the web root, the virtual host and the certificate |
| `ENVIRONMENT`, `APACHE_HTTP_PORT`, `APACHE_HTTPS_PORT`, `CERT_TYPE`, `CERT_PATH`, `APACHE_CONFIG`, `DOCKER_COMPOSE_FILE` | Written by `setup-environment.sh` for the local setup and `health-check.sh`; the VPS scripts do not use them, leave them as they are |
| `LETSENCRYPT_EMAIL` | Address Let's Encrypt writes to (used by `deploy-to-vps.sh`) |
| `LETSENCRYPT_WEBROOT`, `LETSENCRYPT_STAGING` | Not used by the VPS scripts (certbot runs with `--apache`) |
| `STATUS_DIR` | Where the container writes `status.json`, served at `/status/`; `deploy-to-vps.sh` sets it to `/var/www/DOMAIN/status` |

**Access**

| Variable | Meaning |
|----------|---------|
| `TTYD_USERNAME`, `TTYD_PASSWORD` | The first administrator account; read once by `deploy-to-vps.sh` to create it. Change a password later with `manage-players.sh add NAME` |
| `MAX_CLIENTS` | Players allowed in the terminal at once (ttyd `-m`) |
| `SESSION_TIMEOUT` | Seconds between ttyd's keep-alive pings (ttyd `-P`) |
| `TTYD_FONT_SIZE` | Terminal font size in the browser |
| `CONQUER_UID` | uid of the game user inside the container; set it to the owner of `data/` on the host (`id -u conquer`) so scripts can read `data/` |

**Turns** (see [Turns](#turns))

| Variable | Meaning |
|----------|---------|
| `TZ` | Time zone of `TURN_SCHEDULE`; the site shows each visitor the time in their own |
| `TURN_SCHEDULE` | When turns run, cron format (`"0 20 * * 0"` Sundays 20:00; `off` for manual updates only) |
| `TURN_SCHEDULE_LABEL` | The schedule in your words; leave empty to have it worked out |
| `TURN_RETRY_MINUTES`, `TURN_MAX_RETRIES` | The update waits while players are in the game: retry interval and number of attempts |
| `TURN_GRACE_MINUTES` | Minutes players still in the game are warned before they are disconnected (orders are saved) |
| `TURN_BACKUPS` | World copies kept in `data/backups`, one before each update (`0` disables) |
| `TURN_WEBHOOK_URL` | Webhook told the result of each update (Slack, Mattermost, Discord) |
| `TURN_EARLY` | `on`: the update runs as soon as every player's nation has marked its orders done; the schedule stays the deadline |

**Joining and notifications** (see [Email notifications](#email-notifications))

| Variable | Meaning |
|----------|---------|
| `SIGNUP` | `on`: requests and invite codes work at `/signup.html`; `off` closes them |
| `ADMIN_CONTACT` | Shown under "How to join" and in the menu; if it is an address it is also the default `NOTIFY_EMAIL` |
| `NOTIFY_EMAIL` | Where new requests are announced |
| `NOTIFY_LANG` | Language of your mails and webhook text: `en`, `es`, `de`, `pl`, `pt-br`, `ru`, `zh` |
| `SMTP_HOST` | Mail server, `host:port`; nothing is sent while empty |
| `SMTP_USER`, `SMTP_PASSWORD` | Mail account (empty for no login) |
| `SMTP_FROM` | Sender address of the mails |
| `SMTP_STARTTLS` | `on` or `off` |
| `SIGNUP_WEBHOOK_URL` | Webhook announcing each new request (default `TURN_WEBHOOK_URL`) |
| `SITE_URL` | Address of the site in mails (default `https://DOMAIN`) |

## Apache virtual host

`deploy-to-vps.sh` writes `/etc/apache2/sites-available/DOMAIN.conf` from
`vps/virtualhost.conf.template` (replacing `DOMAIN_NAME`). Later updates do
not rewrite it, so when the template gains a block, compare and copy it:

```bash
sed "s/DOMAIN_NAME/game.example.com/g" vps/virtualhost.conf.template \
    | diff - /etc/apache2/sites-available/game.example.com.conf
sudo apache2ctl configtest && sudo systemctl reload apache2
```

Blocks that must exist in the HTTPS host (`update-vps.sh` checks the marked ones):

- `RequestHeader unset X-WEBAUTH-USER early`, so a client cannot forge who it is.
- WebSocket rewrite and `ProxyPass /play/` to `127.0.0.1:7681`.
- `ProxyPass /join/api/` to `127.0.0.1:7682/join/api/` (open, like the sign-up page). *checked*
- `/admin/`: `RedirectMatch permanent ^/admin$ /admin/`, `AliasMatch "^/admin/$"` to `admin.html`, `ProxyPass /admin/api/` to `127.0.0.1:7682/admin/api/`, and a `<Location "/admin/">` with basic auth on `/etc/apache2/conquer-web.htpasswd` and `RequestHeader set X-WEBAUTH-USER`. *checked*
- `Cache-Control: no-cache` for `html|js|css|json` files. *checked*
- `Content-Security-Policy` whose `script-src` has `'wasm-unsafe-eval'` (the practice game at `/try/` is WebAssembly). *checked*
- `/status` with `Access-Control-Allow-Origin: *`.
- `<Location "/play/">` with the same basic auth, **as the last `<Location>`** of the host: sections merge in order and a later one granting access would remove the password (CI checks this in the template).
- `admin` must not appear in the `<LocationMatch ...phpmyadmin>` list that denies access.

If you also use `certbot --apache` to edit hosts, it copies the host into a
`-le-ssl.conf` file: make changes in every file that has the domain
(`grep -rl DOMAIN /etc/apache2/sites-available`).

## Email notifications

Players ask for a seat and you approve at `/admin/`. The game can mail you
each new request and mail the player when approved. It works without mail
(requests wait in `/admin/`); a webhook (`SIGNUP_WEBHOOK_URL`) can announce
requests in Slack, Mattermost or Discord instead.

`NOTIFY_EMAIL` is where requests are announced. A player who gave an address
is mailed on approval, in the language of the page they asked from; yours is
in `NOTIFY_LANG`. Nothing is sent while `SMTP_HOST` is empty.

**Option 1 (recommended): your mailbox provider**, no mail server on the VPS:

```
NOTIFY_EMAIL=you@example.com
SMTP_HOST=smtp.example.com:587
SMTP_USER=you@example.com
SMTP_PASSWORD=...
SMTP_FROM=conquer@example.com
SMTP_STARTTLS=on
```

Gmail needs an "app password". `SMTP_FROM` must belong to the account or the
provider refuses the mail. Port 465 (implicit TLS) also works.

**Option 2: the VPS sends it** with Postfix (`sudo apt install postfix`,
"Internet site"). Make it listen on the Docker bridge and accept containers,
in `/etc/postfix/main.cf`:

```
inet_interfaces = 127.0.0.1, 172.17.0.1     # docker0: ip -4 addr show docker0
mynetworks = 127.0.0.0/8 172.16.0.0/12
```

then `sudo systemctl restart postfix` and set `SMTP_HOST=host.docker.internal:25`,
`SMTP_STARTTLS=off`, `SMTP_FROM=conquer@your-domain.com`, empty `SMTP_USER`.
Without SPF and DKIM for your domain many providers file such mail as spam,
and never open port 25 of the firewall for this.

After editing `production.env`, restart the service and try it:

```bash
docker exec conquer-vps conquer-gate -test-mail you@example.com
```

## Players and requests

A player has two passwords: the **web account** (asked by the site, in
`/etc/apache2/conquer-web.htpasswd`) and the **nation password** (asked by the
game). Who plays which nation is in `data/lib/.players`; `sudo ./manage-players.sh list`
shows each account with its nation, `*` for administrators, `?` waiting for
approval, `+` approved but with no nation yet.

**Requests.** A player presses **I want to play** (`/signup.html`) and gets an
account that waits. You see the request at `/admin/` (accounts marked `*`
only), or:

```bash
sudo ./manage-players.sh requests
sudo ./manage-players.sh approve NAME      # no email from here; /admin/ mails the player
sudo ./manage-players.sh reject NAME       # deletes the account
```

An approved player presses **Play now** and the menu has them found their
nation with the game's builder, at any turn (after turn 5 the builder is
`conqrun -A`, which needs no super user password because you approved the
account, and the game gives a late nation extra points). `SIGNUP=off` closes
requests.

**Invite codes** approve at once: `sudo ./manage-players.sh invite [COUNT]`
(or at `/admin/`), `invites` lists the unused ones. Send the code, or the link
`https://DOMAIN/signup.html?code=CODE`. Each code works once.

**Administrators** can use `/admin/`: `sudo ./manage-players.sh add NAME --admin`
(or `assign NAME --admin`). They may open any nation, god's included. Other
commands: `add NAME --nation NATION`, `assign NAME NATION`,
`assign NAME --found` (found a new nation next time), `rename`, `remove`.
`sudo ./add-nation.sh` runs the game's nation builder by hand for a player
you place yourself (it asks for the god password once the game is past turn 5).
Nation passwords are changed with `sudo ./set-nation-password.sh NATION` (at
most 7 characters).

## Turns

A cron inside the container runs the update on `TURN_SCHEDULE`. Each update
makes room (the menu stops new games, players still in the game are warned
every minute and disconnected after `TURN_GRACE_MINUTES`, their orders saved),
copies the world to `data/backups/world_turnN_*.tar.gz` (`TURN_BACKUPS` kept),
runs it (retrying every `TURN_RETRY_MINUTES` up to `TURN_MAX_RETRIES` times),
and reports: a notice on the site if it failed, and `TURN_WEBHOOK_URL`.
With `TURN_EARLY=on` it also runs as soon as every player nation is done.
`sudo ./run-turn.sh` runs one now (refused while players are in the game).

## Seasons

```bash
sudo ./new-season.sh "Season 1: The return of the Usenet generals"
sudo ./new-season.sh "Season 2" --world MYWORLD.tar.gz     # your own world
```

It ends the season: puts the final scores in the hall of fame (`/hall.html`),
keeps a copy of the old world and the accounts in
`/root/conquer-backups/season-end-*/`, installs a new world (the default one,
or your file), and asks for the new world's [god password](#god-password).
Players keep their web accounts and found a new nation the next time they
play; invite codes stay valid. It is refused while an update runs or someone
is in the game, so warn the players: their nations end with the season.
`sudo ./season-end.sh "NAME"` only records the hall of fame entry.

The default world is made for about 15 players (112x112 sectors, 7 computer
nations, room for 23 players: Conquer holds at most 35 nations counting god
and the monsters). Worlds must be at most 256x256. `./generate-world.sh`
rebuilds the default world shipped in `conquer/lib/` (needed only if you
change it).

## Backups

Four kinds, from nearest to farthest:

| Copy | Where | Made by |
|------|-------|---------|
| Before every turn | `data/backups/` | the game (`TURN_BACKUPS`) |
| Before every update, and before a season ends | `/root/conquer-backups/` (accounts, settings, world) | `update-vps.sh`, `new-season.sh` |
| On demand | `backups/` | `sudo ./backup-world.sh` |
| Off-site | another machine or disk | `offsite-backup.sh`, below |

Restore a world with `sudo ./restore-world.sh` (lists the copies; or give a
file name or path), then `docker restart conquer-vps`. It keeps a copy of the
world it replaces.

**Off-site copies.** The copies above die with the server. `offsite-backup.sh`
sends a copy of the world, the web accounts, `production.env` and the Apache
host to another place: `conquer-HOST-DATE.tar.gz` (or `.enc`). Settings are
in `config/backup.env` (copy `config/backup.env.template`; it is never
committed). **Credentials, passwords, key files and the names of your
machines belong only in that file, in `/root`, and on the target, never in
the repository.**

```bash
cp config/backup.env.template config/backup.env       # set BACKUP_TARGET
sudo ./offsite-backup.sh                              # one copy now, to try it
sudo ./offsite-backup.sh --install-cron               # then one every day at 04:17
```

`BACKUP_TARGET` is one of:

- `user@host:/path` over SSH (rsync must be installed there). Run
  `sudo ./offsite-backup.sh --setup-key`: it makes a key and prints the line
  to add to `~/.ssh/authorized_keys` on the other machine
  (`BACKUP_SSH_KEY`, `BACKUP_SSH_PORT`).
- `rsync://USER@HOST/MODULE/path`, an rsync daemon, for a NAS such as a
  Synology, which does not give ordinary users SSH. Enable the NAS's rsync
  service (in DSM: File Services, rsync), give a user permission on the shared
  folder (the module is named after it), and put that user's password, alone
  on one line, in `BACKUP_RSYNC_PASSWORD_FILE` (default
  `/root/.conquer-backup-rsync`, mode 600). `BACKUP_RSYNC_PORT` is 873 unless
  changed. The daemon protocol is **not encrypted**: use it on a private
  network or VPN, restrict the port to this server, and set
  `BACKUP_PASSWORD_FILE` so the copies themselves are encrypted.
- a directory (another disk, a mounted share).

`BACKUP_KEEP` (default 30) copies stay at the target; older ones are removed
by name, which carries the date. For rsync targets pruning uses rsync itself:
an empty directory is synchronised with `--delete` and a filter that lists
only the old names, so it cannot touch anything else. The server keeps the
last three copies for itself in `/root/conquer-backups/offsite/`.

With `BACKUP_PASSWORD_FILE` set the copies are encrypted (AES-256): keep that
password somewhere else too. To open a copy:

```bash
sudo ./offsite-backup.sh --decrypt conquer-HOST-DATE.tar.gz.enc    # writes the .tar.gz
tar xzf conquer-HOST-DATE.tar.gz         # world.tgz, accounts, production.env, apache/
sudo ./restore-world.sh /path/to/conquer-HOST-DATE/world.tgz
```

`sudo ./offsite-backup.sh --remove-cron` stops the daily copies.

## God password

God's password opens every nation. The game stores only a short hash, which
could be guessed from a published world, so the worlds in this repository
ship with god **locked**: no password opens it until you set yours.
`deploy-to-vps.sh` and `new-season.sh` ask for it; `update-vps.sh` and the
container log warn while it is missing.

```bash
sudo ./set-nation-password.sh god              # set or replace it (at least 4 characters, at most 7 kept)
sudo ./set-nation-password.sh god --if-locked  # only if none is set yet
```

Choose something hard to guess. The same script resets any nation's
password without the old one.

## Troubleshooting

**The container does not start**: `docker logs conquer-vps`, then
`sudo systemctl status conquer-web`.

**`fatal: detected dubious ownership in repository`**: you ran `git` as root
in a checkout owned by `conquer`. Run git as the owner
(`sudo -u conquer git pull`); `update-vps.sh` does that itself.

**docker-compose 1.29 refuses a number** (for example `pids_limit: "512"`):
that version passes `${VARIABLES}` to Docker as text. Numeric settings in the
compose files (`pids_limit`, `mem_limit`) must be literal numbers;
`tests/test_compose.py` checks it.

**`❌ The game container is not the current version`**: it was built before an
update. `sudo ./update-vps.sh --rebuild`.

**`/try/` stays blank, or the console says WebAssembly is blocked**: the
Content-Security-Policy lacks `'wasm-unsafe-eval'`. `update-vps.sh` adds it;
if it says Apache refused, edit it by hand in every file that has the policy
(`grep -r Content-Security-Policy /etc/apache2/`) and check with
`curl -sI https://DOMAIN/try/ | grep -i content-security`.

**`/admin/` answers 401**: Apache did not accept the account (wrong
password, account removed). `sudo ./check-web-login.sh NAME` gives it a new
password and says which layer rejects the login. **It answers 403**: you
are signed in but the account is not an administrator
(`sudo ./manage-players.sh assign NAME --admin`), or the virtual host still
has `admin|` in its `LocationMatch` deny list.

**The sign-up page cannot send requests**, or `/admin/` shows no data: the
virtual host lacks `/join/api/` or `/admin/api/` (`update-vps.sh` says so).

**Players cannot sign in**: `sudo ./check-web-login.sh NAME`; the accounts file
is `/etc/apache2/conquer-web.htpasswd`.

**Certificate does not renew** (`Could not bind TCP port 80`): it was got with
`--standalone`. Get it again through Apache with
`sudo certbot certonly --apache --cert-name DOMAIN -d DOMAIN --force-renewal`;
`deploy-to-vps.sh` does this for you.

**Apache**: `sudo apache2ctl configtest`, `sudo tail -f /var/log/apache2/error.log`.
**Mail**: `docker exec conquer-vps conquer-gate -test-mail you@example.com`
prints the reason it failed.

Older helpers still in the repository and not needed here: `logs.sh`,
`reset-to-default-world.sh`, `setup-security-basic.sh`.
