# Conquer engine patches

Fixes for the game engine ([vejeta/conquer](https://github.com/vejeta/conquer))
that are not in its repository yet. The Dockerfile applies them after
cloning the sources:

- a patch that applies is applied;
- a patch that is already in the sources (it applies in reverse) is skipped,
  so nothing breaks once it is merged upstream;
- any other patch fails the build, so it is noticed and refreshed.

| Patch | Fixes |
|-------|-------|
| 0001 | Crashes when `LOGIN` or the god nation's owner is not a user on the system (e.g. inside a container), and buffer overflows with long `-d`/`-n` arguments |
| 0002 | `conqrun -m` accepting maps larger than 256x256, which corrupts army and capital positions |
| 0003 | `LOGIN` (the administrator's login) overridable at build time |

Delete a patch once its fix is merged upstream. To refresh one against a
newer engine, apply it in a clone of the game repository, resolve the
conflicts, commit and export it again with `git format-patch`.
