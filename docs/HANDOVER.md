# Handover: state of the work (November 2026)

Read this first when picking the project up in a new session.

## Branches

- `master`: production baseline up to PR #8 (join flow, mails, late join,
  security runbook, off-site copies).
- `claude/cool-feynman-97nv7c` (PR #10, open): everything since: design
  system and race artefacts, touch layer, sound v2 (sampled orchestral
  beds and effects in `web/sound/`, `web/audio.js`), app mode, form
  login, nations overview, the 8-scene story (`web/story.html`, narration
  in 7 languages under `web/story/<lang>/`, videos
  `web/story/conquer-story.<lang>.mp4` and `.vertical.mp4`), Open Graph
  tags, nation password hints (2-7 characters). CI green. The VPS deploys
  this branch with `./update-vps.sh`.
- `android` (PR #9, draft): the Cefrium app under `android/`, merged
  regularly from the web branch (settings sheet, native sounds, Back
  controls, story on first launch). CI builds the APK as the
  `app-debug.apk` artifact of the `android` job; signed with the committed
  debug keystore, so installs update in place.

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
- Merge PR #10 into `master`, then rebase or merge `android` on top.
- Clean up local worktrees (`git worktree prune` after removing the
  `.claude/worktrees/*` directories that are no longer needed).
- Story and tutorial `tutorial/trailer.*.mp4` are no longer linked from
  the index; remove or keep.
