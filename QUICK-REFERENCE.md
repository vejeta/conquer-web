# Quick reference

The everyday commands, for the game administrator (on the server) and for
players (in the browser). The full explanations are in [README.md](README.md),
[DEPLOYMENT.md](DEPLOYMENT.md) and the [player's guide](web/guide.html).

## Administrator

Run these on the server, in the project directory (`/home/conquer/conquer-web`
on the VPS), with `sudo`.

### Keep the server up to date

| Command | What it does |
|---------|--------------|
| `sudo ./update-vps.sh` | Saves a copy of accounts, settings and world, pulls the code, rebuilds the game when it changed, installs the web pages, checks the result |
| `sudo ./update-vps.sh --rebuild` | The same, always rebuilding the game |
| `sudo systemctl restart conquer-web` | Restarts the game, for example after changing `config/production.env` |
| `./health-check.sh` | Checks Docker, the game container and the site |
| `./logs.sh` | Follows the game container's log |

Passwords (web accounts, nations) and the world survive all of these.

### Let a player in

**With an invite code** (the player creates their own account and nation;
new nations can join until turn 5):

```bash
sudo ./manage-players.sh join-account   # once: prints JOIN_ACCOUNT and JOIN_PASSWORD;
                                        # add them to config/production.env, then
sudo systemctl restart conquer-web      # the home page shows that account
sudo ./manage-players.sh invite         # a single-use code for one player
sudo ./manage-players.sh invites        # the codes not used yet
```

Send the player the code and the address of the site. They follow "How to
join" on the home page.

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
| `sudo ./manage-players.sh remove NAME` | Deletes an account |
| `sudo ./set-nation-password.sh NATION` | Sets a nation's password without the old one |
| `sudo ./set-nation-password.sh god` | Sets the god (game administrator) password |
| `sudo ./check-web-login.sh NAME` | Gives an account a **new** generated password and tests the whole login; use it when a login fails |

Nation passwords keep at most 7 characters (god needs at least 4).

### Turns

| Command | What it does |
|---------|--------------|
| `./run-turn.sh` | Runs the turn update now (refused while players are in the game) |
| `TURN_SCHEDULE=0 20 * * *` | In `config/production.env`: when turns run (cron format, here every day at 20:00); restart the game after changing it |
| `TURN_SCHEDULE_LABEL=Daily at 20:00 UTC` | How the schedule is shown to players |
| `TURN_EARLY=on` | The update runs as soon as every nation marks its orders done |

A copy of the world is taken before every update (`data/backups/`).

### World and seasons

| Command | What it does |
|---------|--------------|
| `./backup-world.sh` | A copy of the world now |
| `./restore-world.sh` | Lists the copies and restores one |
| `./season-end.sh "Season 1: …"` | Keeps the final scores of a season in the hall of fame |
| `./generate-world.sh` | Makes a new world (see README.md, "The default world") |

### Other settings in `config/production.env`

| Setting | What it does |
|---------|--------------|
| `ADMIN_CONTACT=` | Your address, shown under "How to join" on the home page and in the menu |
| `JOIN_ACCOUNT=`, `JOIN_PASSWORD=` | The shared account for players with an invite code |

## Players

Everything happens in the browser, at the address of the site.

1. **Join**: ask the administrator (address under "How to join") for an
   invite code. Press **Play now**, sign in with the joining account shown on
   the home page, type the code, choose your own player account and build
   your nation. Then close the tab and sign in again with your own account.
2. **Play**: **Play now**, your account, option **1** of the menu, your
   nation password.
3. **Learn**: **Try it free** on the home page (a practice world, no account),
   "Your first turn, step by step", the **Coach** button above the game, and
   option **7** of the menu (your own practice world).

In the game:

| Keys | What they do |
|------|--------------|
| `y k u` / `h l` / `b j n` | Move the cursor (NW N NE / W E / SW S SE) |
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
