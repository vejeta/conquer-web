# Conquer Web

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

A secure, web-based implementation of the classic Conquer strategy game using Docker containers, ttyd (terminal over HTTP), and Apache as a reverse proxy with SSL termination.


## ▶️ Play now

| Server | What is there |
|--------|---------------|
| **[conquer.vejeta.com](https://conquer.vejeta.com)** | The live game, run by the author of this project: a shared world with daily turns. [Try it](https://conquer.vejeta.com/try/) with no account (a practice world in your browser); to join, ask for an invite code at the address on the home page. In English, Spanish, German, Portuguese, Polish, Russian and Chinese. |

Running your own server? Open a pull request to add it here.

> **Everyday commands** for the administrator and players: [QUICK-REFERENCE.md](QUICK-REFERENCE.md).

## 🎮 Overview

This setup allows multiple players to access the same Conquer game instance through their web browsers, with proper authentication, rate limiting, and security features for safe public deployment.

**Important**: Conquer requires pre-generated world data to run. See the [World Generation](#-world-generation) section below for setup instructions.

## 🚀 Quick Start

**⚠️ Security Notice**: Always change default usernames and passwords before deployment!

### Option 1: Local Development
For development work on your local machine:

```bash
# Setup environment
./setup-environment.sh
# Choose option 1: Local development

# Start local development environment (loads config/local.env,
# creates the self-signed certificate and data/lib/ if missing)
./start-local.sh
```

- **URL**: https://conquer.local (landing page), https://conquer.local/play/ (game)
- **Setup**: Full Docker environment (Apache + Conquer containers)
- **SSL**: Self-signed certificate (accept browser warning)

### Option 2: VPS Production
For deployment on a VPS with existing Apache:

```bash
# Setup environment
./setup-environment.sh
# Choose option 2: VPS production

# Deploy to VPS (run as root)
sudo ./deploy-to-vps.sh
```

- **URL**: https://your-configured-domain.com (landing page), `/play/` (game)
- **Setup**: Host Apache + Conquer container
- **SSL**: Let's Encrypt certificate

## 🕹️ How Players Access the Game

- **`https://your-domain/`** – public landing page (`web/index.html`), in English
  and Spanish (browser language, EN/ES switch or `?lang=es`): the current turn,
  the next turn update with a countdown, scores, the latest world news, what
  Conquer is, how to join, how turns work and a key reference.
- **`https://your-domain/guide.html`** – the player's guide (`web/guide.html`,
  screenshots in `web/guide/`): the history of Conquer since 1987, a step-by-step
  tutorial of the whole workflow, advice for new rulers and veterans, the
  tournament formats with their `TURN_SCHEDULE` settings, and the season plan
  towards the game's 40th anniversary. Linked from the landing page. In
  Spanish at `guide.es.html`.
- **`https://your-domain/try/`** – Conquer compiled to WebAssembly, running
  entirely in the visitor's browser: a private practice world with its own
  turns, no account needed; plain static files (see `wasm/README.md`).
- **`https://your-domain/tutorial.html`** – the first turn of a new nation,
  key by key, with the real screens, a terminal recording and a narrated
  video; in Spanish at `tutorial.es.html`, with the Spanish video (see
  `tools/tutorial/README.md`).
- **`https://your-domain/hall.html`** – the hall of fame of finished seasons.
- **`https://your-domain/game.html`** – the game page opened by "Play now". It embeds
  the terminal and adds an on-screen key bar (movement, Esc, Enter, Ctrl-L...) that
  is shown by default on phones and tablets. On small screens the terminal font is
  scaled down so the game always gets its 80x24 screen.
- **`https://your-domain/play/`** – the game terminal itself (ttyd). Every player
  signs in with **their own account** (see *Player accounts* below).
- **`https://your-domain/status/status.json`** – public game status, written by the
  game container at startup and after every turn update.

After signing in, players see a menu instead of a raw game prompt:

1. **Play** – checks that the terminal is at least 80x24, then opens the
   player's own nation (only the nation password is asked). Quitting the game
   returns to the menu.
2. **How to join / how turns work**
3. **Key reference**
4. **Scores**
5. **Full help** – the in-game help screens
6. **My orders for this turn are done** (see *Early turns when everyone is done*)
7. **Practice world** – a private copy of the default world with a ready
   nation (`trainee`, password `train1`) for every account. Players try
   anything, run its turns themselves and start again at will; it never
   touches the real game and never blocks its turn updates. Practice worlds
   live in `data/practice/`.

The **Coach** button above the game (or `game.html?coach`) opens a
step-by-step guide next to the terminal: the same first turn as the
tutorial page (`/tutorial.html`), with buttons that press the keys for the
player. It follows the game on its own, moving to the next step when the
screen changes.

The menu also shows the last turn update and the turn schedule.

**Languages.** The site, the guide, the tutorial and its video, the game
page, the coach, the player menu and the invite-code wizard are in English
and Spanish. Every text is in one catalog per language, with English shown
for anything a language does not have yet: `web/i18n/` (pages, coach),
`tools/tutorial/i18n/` (tutorial and coach steps), `conquer/i18n/` (menu and
join wizard). Pages follow `?lang=`, the language menu of the home page or
the browser; the game page passes the language to the menu (ttyd
`--url-arg`: `/play/?arg=es`, where the menu accepts only a language it has
texts for). `web/i18n/README.md` explains how to add a language, and
`tools/check-i18n.py` (run by CI) finds missing or broken texts. The game's
own screens are the original English ones. A daily or weekly
`TURN_SCHEDULE` is shown in each visitor's language and local time; a
`TURN_SCHEDULE_LABEL`, if set, replaces it as written, so pick its language.

## 👑 Game Administration

### Creating nations

During the test phase, nations are created by the administrator, not by players:

```bash
./add-nation.sh      # runs "conqrun -a" inside the running container
```

After the nation, the script asks for its name and creates the player's web
account linked to it (see below). Give the player that account and the nation
password.

### Nation passwords, god's included

The game asks each nation for its own password; god's is the game
administrator's. To set one without knowing the old one (a forgotten god
password, a player who lost theirs):

```bash
./set-nation-password.sh god
./set-nation-password.sh sahara
```

Conquer keeps at most 7 characters of a password (god needs at least 4). The
new password works at once. God's password is also asked by `add-nation.sh`
once the game is past turn 5.

### Player accounts

Players sign in to `/play/` with their own account. Apache checks it and
passes the account name to the game menu, which opens **only the nation
assigned to that account** (the player just types the nation password). An
account without an assignment opens the nation with the same name, if any.
Administrator accounts may open any nation, god included.

```bash
./manage-players.sh add kestrel --nation Elves   # create or reset (asks for a
                                                 # password, or generates one)
./manage-players.sh add admin2 --admin           # may open any nation
./manage-players.sh assign kestrel Dwarves       # change the nation
./manage-players.sh remove kestrel               # revoke access
./manage-players.sh list                         # accounts and their nations
```

#### Joining with an invite code

Players create their own account with an invite code; nobody without one
can create an account or reach the game terminal. The administrator hands
out the codes:

```bash
sudo ./manage-players.sh invite 5     # five single-use codes
sudo ./manage-players.sh invites      # the codes not used yet
```

1. The player opens **Create your account** on the home page (`signup.html`,
   or `signup.html?code=K7QM-3XPA` to fill the code in), types the code and
   chooses an account name and a password. `conquer-gate`, a small service
   in the game container, checks the code, creates the account and uses the
   code up; it slows down anyone who keeps trying wrong codes.
2. The player presses **Play now** and signs in with that account. The game
   has them found their nation with its nation builder, links it to the
   account, and from then on opens it directly.

The page shows `ADMIN_CONTACT` to visitors without a code. After turn 5 the
game only lets the administrator add nations, so sign-up then asks players
to write to them. `SIGNUP=off` in the environment file closes it.
`sudo ./manage-players.sh list` shows new accounts that have not founded
their nation yet with `+`.

Assignments are stored with the world, in `data/lib/.players`
(`account:nation`, `*` for administrators), so backups and restores keep them.
Worlds without that file (deployments older than this feature) keep the old
behaviour where any account can type any nation name: assign the existing
accounts, starting with `./manage-players.sh assign ADMIN --admin`.

The accounts live in `data/auth/htpasswd` locally and in
`/etc/apache2/conquer-web.htpasswd` on the VPS (use `sudo` there); changes
apply immediately. `TTYD_USERNAME`/`TTYD_PASSWORD` from the environment file
create the administrator's account the first time (`start-local.sh`,
`deploy-to-vps.sh`) as an administrator account, which can open any nation
with its nation password. Failed sign-ins are counted by the fail2ban filter
from `setup-security.sh`.

ttyd trusts the account name Apache sends, so only Apache may reach it: port
7681 is not published in the local setup and is bound to `127.0.0.1` on the
VPS (anyone with a shell on the VPS could reach it directly).

### Turn updates

Turns are resolved automatically by cron inside the game container. Configure
the schedule in `config/local.env` or `config/production.env`:

```bash
TZ=Europe/Madrid
TURN_SCHEDULE="0 20 * * 0"                     # weekly, Sundays at 20:00
# TURN_SCHEDULE_LABEL="..."                    # optional: your own words instead
                                               # of the worked-out schedule
# TURN_SCHEDULE="0 20 * * *"                   # daily at 20:00
# TURN_SCHEDULE=off                             # manual updates only
```

Every turn update:

1. **Makes room for the update.** Conquer refuses to update while anyone is in
   the game, so the menu stops accepting new games, players still in the game
   get a warning on screen every minute and, after `TURN_GRACE_MINUTES`
   (default 5), their session is ended. The game saves their orders when it is
   stopped this way, and the menu tells them they were disconnected.
2. **Backs up the world** to `data/backups/`, keeping the last `TURN_BACKUPS`
   archives (default 10, `0` disables). Restore one with
   `./restore-world.sh world_turnN_YYYYMMDD_HHMMSS.tar.gz`.
3. **Runs the update**, retrying every `TURN_RETRY_MINUTES` (default 10) up to
   `TURN_MAX_RETRIES` times (default 18) if it still cannot run.
4. **Reports the result**: the landing page and the player menu show a notice
   if the last update failed, and `TURN_WEBHOOK_URL` (optional) receives a
   message after every update. The payload has both `text` (Slack, Mattermost)
   and `content` (Discord) fields.

Details appear in the container logs (`./logs.sh`).

#### Early turns when everyone is done

When a player quits the game, the menu asks whether their orders for the turn
are done (option 6 changes it later). The menu banner and the landing page
show how many nations are done. Once **every nation assigned to a player
account** (see *Player accounts*) is done, the turn update starts right away
instead of waiting for the schedule, which remains the deadline for the
slower players. Set `TURN_EARLY=off` to only count the nations without
running early updates. Marks from an earlier turn never count.

To run a turn immediately:

```bash
./run-turn.sh
```

After changing the schedule, recreate the container so it picks up the new
settings: `./rebuild.sh --quick` (it loads the environment file).

### World data persistence

The live world is stored on the host in `data/lib/` and mounted into the
container, so rebuilding or upgrading the image keeps player progress. On first
start the container copies the default world shipped in the image (`conquer/lib/`)
into `data/lib/`.

The game runs as an **unprivileged user** (`conquer`, uid `CONQUER_UID`,
default 1000): the entrypoint only uses root to prepare the volumes and cron,
then ttyd, the menu, the game and every turn update run as that user. `data/`
is owned by that uid on the host; set `CONQUER_UID` to your own uid (`id -u`)
so the backup scripts can read it without `sudo`.

Every player and the administrator share that user. Because Conquer ties
nations to Unix users, the container makes it the owner of the god nation on
startup (`conqowner`), otherwise `add-nation.sh` could only ever create one
nation.

## 🔧 Configuration

### Authentication Setup

`TTYD_USERNAME`/`TTYD_PASSWORD` define the administrator's web account, created
on first start; players get their own accounts with `./manage-players.sh`.
Configure them during setup or by editing environment files:

**Local Development** (`config/local.env`):
```bash
TTYD_USERNAME=your_dev_username
TTYD_PASSWORD=your_dev_password
MAX_CLIENTS=10
SESSION_TIMEOUT=3600
```

**VPS Production** (`config/production.env`):
```bash
TTYD_USERNAME=your_username
TTYD_PASSWORD=your_strong_password
MAX_CLIENTS=5
SESSION_TIMEOUT=1800
```

### Changing Settings

**🔐 IMPORTANT**: Change default credentials before first use!

1. **Change a password** with `./manage-players.sh add NAME` (it resets an
   existing account); no restart is needed.
2. **Other settings**: edit the environment file (see above) and restart:
   - Local: `./rebuild.sh --quick`
   - VPS: `sudo systemctl restart conquer-web`

### Security Best Practices

- ✅ **Use strong passwords** - At least 12 characters with mixed case, numbers, symbols
- ✅ **Unique usernames** - Don't use common names like 'admin', 'user', 'conquer'
- ✅ **Change defaults** - Never use 'changeme' or default passwords in production
- ✅ **Regular updates** - Change credentials periodically

## 🌍 World Generation

Conquer requires world data to run. Generate it before first use:

```bash
# Generate world data (becomes the default world in conquer/lib/)
./generate-world.sh

# Backup the live world (data/lib/)
./backup-world.sh

# Restore the live world from a backup, then restart the container
./restore-world.sh world_backup_YYYYMMDD_HHMMSS.tar.gz
```

`generate-world.sh` replaces the default world shipped in the image. The running
game keeps using `data/lib/` until you back it up, remove it and run
`./rebuild.sh --force`.

**Map size:** Conquer stores army and capital coordinates in 8 bits, so worlds
must be at most **256x256**. Larger maps misplace armies into the sea and
players see an empty map; the container logs a warning if it detects one.

**The default world** is made for about 15 players: 112x112 sectors with 60%
water (about 4,400 land sectors), 7 computer nations (anorian, darboth,
edland, fung, goldor, woooo, sahara, listed in `conquer/lib/nations`) and the
monsters (pirates, nomads, savages, lizards). Conquer holds at most 35
nations counting god, the computer nations and the 4 monsters, so this world
leaves 23 places for players: 15 and room for late arrivals. Neighbours
meet within a few turns and have land to grow for about 25 turns. Every
computer nation in `nations` takes a player's place: keep the list short
when you generate a world for many players.

## 📁 Project Structure

```
conquer-web/
├── conquer/                    # Conquer game Docker container
│   ├── lib/                   # Default world shipped in the image
│   ├── scripts/               # Entrypoint, player menu, turn runner, status
│   └── tools/                 # conqowner (god nation owner fix)
├── web/                       # Landing page and mobile-friendly game page
├── data/lib/                  # Live world data (created at runtime, not in git)
├── data/public/               # Published status.json (created at runtime)
├── data/auth/                 # Player accounts, htpasswd (local setup)
├── apache/                     # Apache Docker container (local only)
├── vps/                       # VPS-specific configurations
├── config/                    # Environment configurations
├── docker-compose.local.yml   # Local development (Apache + Conquer)
├── docker-compose.vps.yml     # VPS production setup
├── setup-environment.sh       # Interactive setup script
├── deploy-to-vps.sh          # VPS deployment script
├── generate-world.sh         # World data generation
├── rebuild.sh                # Rebuild containers (--force, --quick options)
├── logs.sh                   # View container logs
├── stop.sh                   # Stop running containers
├── setup-security.sh         # Security hardening (fail2ban, rate limiting)
├── check-security.sh         # Security status monitoring
├── backup-world.sh           # Backup world data
├── restore-world.sh          # Restore world from backup
├── reset-to-default-world.sh # Reset to default world
├── health-check.sh           # Container health verification
├── add-nation.sh             # Create a player nation (admin)
├── manage-players.sh         # Player web accounts (admin)
├── run-turn.sh               # Run a turn update now (admin)
└── setup-local-certs.sh      # Self-signed certificate for local use
```

## 🔍 Management

### Local Development

```bash
# Start services (loads config/local.env)
./start-local.sh

# View logs
./logs.sh

# Rebuild containers (with cache)
./rebuild.sh

# Rebuild containers (force, no cache)
./rebuild.sh --force

# Quick restart (config changes only)
./rebuild.sh --quick

# Check status
./health-check.sh

# Stop services
./stop.sh
```

### VPS Production

```bash
# Check service status
sudo systemctl status conquer-web

# View logs
sudo journalctl -u conquer-web -f

# Restart service
sudo systemctl restart conquer-web

# Stop service
sudo systemctl stop conquer-web
```

## 🔒 Security Features

- **Authentication**: Username/password protection with brute force protection
- **Rate Limiting**: fail2ban and configurable concurrent user limits
- **Session Management**: Automatic session timeouts
- **SSL/TLS**: HTTPS encryption (Let's Encrypt for VPS)
- **Container Isolation**: Game runs in isolated Docker container
- **Security Headers**: HSTS, CSP, and comprehensive security headers
- **Attack Protection**: Bot blocking, request filtering, DoS protection
- **Monitoring**: Comprehensive logging and security alerts

### Enhanced Security (Optional)

After basic deployment, enhance security with:

```bash
# Run security hardening script
sudo ./setup-security.sh

# Check security status
./check-security.sh
```

See [SECURITY.md](SECURITY.md) for detailed security configuration.

## 🛠️ Development

### Local Setup

1. **Install Dependencies**: Docker, Docker Compose
2. **Generate World**: `./generate-world.sh`
3. **Setup Environment**: `./setup-environment.sh` (choose option 1)
4. **Start Development**: `./start-local.sh`
5. **Access Game**: https://conquer.local

### VPS Deployment

1. **Prepare VPS**: Debian/Ubuntu with Apache installed
2. **Clone Project**: `git clone https://github.com/vejeta/conquer-web.git`
3. **Setup Environment**: `./setup-environment.sh` (choose option 2)
4. **Deploy**: `sudo ./deploy-to-vps.sh`
5. **Configure DNS**: Point domain to VPS IP

## 📚 Documentation

- [VPS Deployment Guide](DEPLOYMENT.md) - Detailed VPS setup instructions
- [Security Hardening Guide](SECURITY.md) - Advanced security configuration
- [World Management](generate-world.sh) - World data generation and backup
- [License Information](LICENSE.md) - GPL v3+ licensing details

## 🐛 Troubleshooting

### Container Issues
```bash
# Check container logs
docker logs conquer-local        # Local
docker logs conquer-vps          # VPS

# Rebuild containers (loads the environment file)
./rebuild.sh --force
```

### VPS Service Issues
```bash
# Check systemd service
sudo systemctl status conquer-web

# Check detailed logs
sudo journalctl -u conquer-web -n 50

# Test Apache configuration
sudo apache2ctl configtest
```

### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Test the automatic renewal
sudo certbot renew --dry-run
```

## 📄 License

This project is licensed under the GPL v3 or later. See [LICENSE.md](LICENSE.md) for details.

## 👥 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## 🙏 Acknowledgments

- **Conquer Game**: Original strategy game implementation
- **ttyd**: Terminal over HTTP technology
- **Docker**: Containerization platform
- **Let's Encrypt**: Free SSL certificates