# Handover: state of the work (November 2026)

Read this first when picking the project up in a new session.

## Branches

- `master`: production. Everything up to PR #10 is merged (design system,
  touch layer, orchestral sound, app mode, form login, nations overview,
  the 8-scene story with narration and videos in 7 languages, Open Graph
  tags, nation password hints). The VPS follows `master`
  (`./update-vps.sh --branch master` once, then `./update-vps.sh`).
- The Android app moved to its own private repository,
  `vejeta/conquer-cefrium`, with this repository as a submodule pinned to
  a commit of `master`. Its CI builds the APK as the `app-debug.apk`
  artifact; signed with the committed debug keystore, so installs update in
  place. The old `android` branch here (PR #9, closed) is no longer used.

## Conventions

- Commit identity: `git -c user.name="Juan Manuel Méndez Rey" -c user.email="vejeta@gmail.com"`;
  no trailers, no tool or model names anywhere in the repository.
- Work in worktrees from `origin/<branch>`; never rewrite `master`; the
  owner merges PRs.
- Narration voice: XTTS-v2 zero-shot from an owner-supplied reference
  (CPML licence, non-commercial); "Conquer" is spoken as one word stressed
  on the O (prompt spellings per language in `web/story/README.md`).
  Music: `tools/sound/build.py` renders `web/sound/` from the FluidR3
  SoundFont (not in the repo).

## Privacy changes of November 2026 (branch `claude/cool-feynman-97nv7c`)

The site keeps no personal data beyond what is technically needed.

- **No player email, no free text.** The sign-up form, the gate, the admin
  page and the mails no longer have them; `.requests` holds account, time and
  language; the gate runs `conquer-signup scrub` at start to strip what older
  requests held. The only mail left is the notice to the administrator.
- **Account pages.** `web/account.html` (change password, new recovery code),
  `web/recover.html` (forgot password with the recovery code), `web/recovery.js`
  (the modal that shows a code once). Gate side: `conquer/gate/account.go`;
  files: `conquer/scripts/signup.sh` commands `passwd`, `recovery-init`,
  `recovery-renew`, `reset`, hashes in `lib/.recovery` (mode 600). Apache:
  `<Location "/account/api/">` (same sign-in as `/play/`, sets
  `X-WEBAUTH-USER`); `update-vps.sh` adds it to existing virtual hosts.
  Limits: 5 wrong passwords/codes an hour per address and per account; fail2ban
  jail `conquer-recover` reads `conquer_recover.log`. Admin reset by hand:
  `sudo ./manage-players.sh password NAME`.
- **Logs 7 days:** `setup-logrotate.sh` (run by `update-vps.sh` and
  `deploy-to-vps.sh`) installs `/etc/logrotate.d/conquer-web`.
- **Privacy notice** rewritten short (`web/privacy.es.html` is the binding one;
  keep both in step, `tests/test_privacy.py`).
- **Donations.** The Liberapay address (https://liberapay.com/Conquer/donate)
  is `DONATE_URL` in `web/site.js`: change it there only (and in the README
  "Donations" section). Elements with `data-donate` get it; they are hidden in
  app mode (`html.in-app`, see `site.js`), because Google Play does not allow
  donation links in the app.
- What to run on the VPS after merging: see DEPLOYMENT.md "Update".

## Open items

- Device tests of the app: story on first launch, Back arrow, settings,
  sounds at the Doors, bridge `home`.
- Owner to listen to the non-Spanish narrations (previews were sent) and
  to the beds; retouch on request.
- Bridge between the pages and the app (conquerAudio, conquerRace,
  cefriumQuery messages): keep it stable or update conquer-cefrium with it.
- Delete the `android` branch here when nothing else needs it.
- Clean up local worktrees (`git worktree prune` after removing the
  `.claude/worktrees/*` directories that are no longer needed).
- Story and tutorial `tutorial/trailer.*.mp4` are no longer linked from
  the index; remove or keep.
