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
