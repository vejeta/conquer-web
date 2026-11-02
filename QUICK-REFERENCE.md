# Quick reference

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

The administrator's commands, on the server, in `/home/conquer/conquer-web`.
Explanations: [DEPLOYMENT.md](DEPLOYMENT.md).

```bash
# Server
sudo ./update-vps.sh                        # update (add --rebuild, or --branch NAME)
sudo systemctl restart conquer-web          # after editing config/production.env
docker logs -f conquer-vps                  # the game's log
sudo ./health-check.sh                      # quick status

# Requests (also at https://DOMAIN/admin/)
sudo ./manage-players.sh requests           # who is waiting
sudo ./manage-players.sh approve NAME       # (this one sends no email)
sudo ./manage-players.sh reject NAME        # deletes the account
sudo ./manage-players.sh invite 3           # three single-use invite codes
sudo ./manage-players.sh invites            # codes not used yet

# Accounts
sudo ./manage-players.sh list               # accounts: ? waiting, + no nation yet, * admin
sudo ./manage-players.sh add NAME --nation NATION   # create or reset (--admin: any nation)
sudo ./manage-players.sh assign NAME NATION         # (or --admin, or --found)
sudo ./manage-players.sh rename NAME NEWNAME
sudo ./manage-players.sh remove NAME
sudo ./check-web-login.sh NAME              # new password + tests the whole login
sudo ./set-nation-password.sh NATION        # nation password (god = administrator)
sudo ./add-nation.sh                        # found a nation by hand

# Turns and seasons
sudo ./run-turn.sh                          # turn update now
sudo ./new-season.sh "Season 2" [--world FILE.tar.gz] [--yes]   # hall of fame, new world
sudo ./season-end.sh "Season 1"             # hall of fame entry only

# Backups
sudo ./backup-world.sh                      # a copy of the world now
sudo ./restore-world.sh                     # pick a copy to restore; then: docker restart conquer-vps
sudo ./offsite-backup.sh                    # send a copy to BACKUP_TARGET (config/backup.env)
sudo ./offsite-backup.sh --setup-key        # SSH key and the line for the other machine
sudo ./offsite-backup.sh --install-cron     # daily at 04:17 (--remove-cron stops it)
sudo ./offsite-backup.sh --decrypt FILE.tar.gz.enc

# Mail
docker exec conquer-vps conquer-gate -test-mail you@example.com
```

Settings (turn schedule, mail, `SIGNUP=off`...) are in `config/production.env`;
every variable is described in DEPLOYMENT.md, "Configuration reference".
