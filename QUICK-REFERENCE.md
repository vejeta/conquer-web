# Quick reference

The everyday commands, for the game administrator (on the server) and for
players (in the browser). The full explanations are in [README.md](README.md),
[DEPLOYMENT.md](DEPLOYMENT.md) and the [player's guide](web/guide.html).

## Administrator

Run these on the server, in the project directory (`/home/conquer/conquer-web`
on the VPS).

**Who needs `sudo`.** The game itself runs as an unprivileged user inside its
container; `sudo` is only for the server's side of the administration:

- `update-vps.sh`, `manage-players.sh`, `add-nation.sh` and
  `check-web-login.sh` write files the web server owns
  (`/etc/apache2/conquer-web.htpasswd`, `/var/www/…`) or restart services:
  they need `sudo`.
- The rest only talk to the game container (`docker exec`): they work with
  `sudo` or as a user in the `docker` group. Membership of that group is
  as powerful as root, so giving it to your everyday account saves typing,
  not risk; `sudo` keeps a trace of each command.
- Players never run anything: they play in the browser.

### Keep the server up to date

| Command | What it does |
|---------|--------------|
| `sudo ./update-vps.sh` | Saves a copy of accounts, settings and world, pulls the code, rebuilds the game when it changed, installs the web pages, checks the result |
| `sudo ./update-vps.sh --rebuild` | The same, always rebuilding the game |
| `sudo ./update-vps.sh --branch master` | Switches the server to another branch (once; later updates follow it) |
| `sudo systemctl restart conquer-web` | Restarts the game, for example after changing `config/production.env` |
| `sudo ./health-check.sh` | Checks Docker, the game container and the site |
| `sudo ./logs.sh` | Follows the game container's log |

Passwords (web accounts, nations) and the world survive all of these.

### Let a player in

**With an invite code** (the player creates their own account on the site,
then founds their nation; new nations can join until turn 5):

```bash
sudo ./manage-players.sh invite         # a single-use code for one player
sudo ./manage-players.sh invites        # the codes not used yet
```

Send the player the code, or the link `https://YOUR-SITE/signup.html?code=THE-CODE`.
They choose **Create your account**, then **Play now** with that account.

**Or create the nation yourself**:

```bash
sudo ./add-nation.sh                    # the game's nation builder, then the web account
```

Give the player the web account with its password, and the nation password.

### Accounts and passwords

A player has two passwords: the **web account** (asked by the site, managed
by `manage-players.sh`) and the **nation password** (asked by the game).

| Command | What it does |
|---------|--------------|
| `sudo ./manage-players.sh list` | Web accounts and the nation each opens |
| `sudo ./manage-players.sh add NAME --nation NATION` | Creates or resets a web account (Enter at the password prompt generates one) |
| `sudo ./manage-players.sh add NAME --admin` | An administrator account: opens any nation, god included |
| `sudo ./manage-players.sh assign NAME NATION` | Links an account to another nation |
| `sudo ./manage-players.sh assign NAME --found` | The account founds a new nation the next time it plays (its old nation, if any, stays in the world without a player) |
| `sudo ./manage-players.sh rename NAME NEWNAME` | Renames an account; the password and the nation stay |
| `sudo ./manage-players.sh remove NAME` | Deletes an account |
| `sudo ./set-nation-password.sh NATION` | Sets a nation's password without the old one |
| `sudo ./set-nation-password.sh god` | Sets the god (game administrator) password. The worlds of this repository come with god locked: set it right after deploying and after `new-season.sh` (both ask); `update-vps.sh` warns while it is not set. It opens every nation, so make it hard to guess |
| `sudo ./check-web-login.sh NAME` | Gives an account a **new** generated password and tests the whole login; use it when a login fails |

Nation passwords keep at most 7 characters (god needs at least 4).

### Turns

| Command | What it does |
|---------|--------------|
| `sudo ./run-turn.sh` | Runs the turn update now (refused while players are in the game) |
| `TURN_SCHEDULE=0 20 * * *` | In `config/production.env`: when turns run (cron format, here every day at 20:00); restart the game after changing it |
| `TZ=Europe/Madrid` | The time zone of `TURN_SCHEDULE`; the website shows each visitor the turn time in their own time |
| `TURN_SCHEDULE_LABEL=` | Leave empty: the schedule is worked out from `TURN_SCHEDULE` and `TZ`. Your own words go here only if you want them shown as written |
| `TURN_EARLY=on` | The update runs as soon as every nation marks its orders done |

A copy of the world is taken before every update (`data/backups/`).

### World and seasons

| Command | What it does |
|---------|--------------|
| `sudo ./backup-world.sh` | A copy of the world now |
| `sudo ./restore-world.sh` | Lists the copies and restores one |
| `sudo ./new-season.sh "Season 1: …"` | Ends the season and starts the next: hall of fame, a copy of the old world, a new world (`--world FILE.tar.gz` for your own); players keep their accounts and found new nations |
| `sudo ./season-end.sh "Season 1: …"` | Keeps the final scores of a season in the hall of fame |
| `sudo ./generate-world.sh` | Makes a new world (see README.md, "The default world") |

### Copies on another machine

The copies above stay on the server. `offsite-backup.sh` sends the world,
the accounts, the settings and the Apache site to another machine every day:

```bash
cp config/backup.env.template config/backup.env   # set BACKUP_TARGET=user@host:/path
sudo ./offsite-backup.sh --setup-key              # prints a line for the other machine's ~/.ssh/authorized_keys
sudo ./offsite-backup.sh                          # one copy now, to check
sudo ./offsite-backup.sh --install-cron           # then one every day at 04:17
```

| Command | What it does |
|---------|--------------|
| `sudo ./offsite-backup.sh --decrypt FILE` | Opens an encrypted copy (with `BACKUP_PASSWORD_FILE`) |
| `tar xzf conquer-*.tar.gz` | Unpacks a copy: `world.tgz` (restore with `restore-world.sh`), the accounts, the settings, the Apache files |
| `sudo ./offsite-backup.sh --remove-cron` | Stops the daily copies |

The other machine needs SSH and `rsync`. `BACKUP_TARGET` may also be a
directory, for example another disk.

### Other settings in `config/production.env`

| Setting | What it does |
|---------|--------------|
| `CONQUER_MEM_LIMIT=1g`, `CONQUER_PIDS_LIMIT=512` | Most memory and processes the game container may use |
| `ADMIN_CONTACT=` | Your address, shown under "How to join" on the home page and in the menu |
| `SIGNUP=on` | Sign-up with invite codes on the site (`off` closes it) |

After changing this file, `sudo systemctl restart conquer-web`: the game
reads it when it starts, and the home page shows the new values then.

## Players

Everything happens in the browser, at the address of the site.

1. **Join**: ask the administrator (address under "How to join") for an
   invite code. Choose **Create your account** on the home page, type the
   code and choose your account name and password. Then **Play now** with
   that account: the game has you found your nation.
2. **Play**: **Play now**, your account, option **1** of the menu, your
   nation password.
3. **Learn**: **Try it free** on the home page (a practice world, no account),
   "Your first turn, step by step", the **Coach** button above the game, and
   option **7** of the menu (your own practice world).

In the game:

| Keys | What they do |
|------|--------------|
| `y k u` / `h l` / `b j n` | Move the cursor (NW N NE / W E / SW S SE) |
| `7 8 9` / `4 6` / `1 2 3` | The same moves on the number pad (the game has always taken them) |
| Arrow keys | The same moves, in the browser: the page sends them as those letters (and, with NumLock off, Home, PgUp, End and PgDn as the diagonals) |
| `p`, `m` | Pick the next unit, move it |
| `D` | Draft troops |
| `C`, `r` | Construct, redesignate a sector |
| `B`, `P` | Budget, production |
| `S` | Diplomacy |
| `N`, `R`, `W` | Newspaper, read mail, write mail |
| `?` | Help |
| `q` | Quit: the menu then asks if your orders for the turn are done |
| `Ctrl` + `L` | Redraw a garbled screen |

The game needs a window of at least 80×24 characters. On phones, the key bar
under the game has the common keys and a **Keyboard** button for typing.
