<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->
# The story's narration

`web/story.html` plays an optional narration for each of its eight scenes.
The files are not in git: the owner renders the eight Spanish takes offline
and drops them here:

```
web/story/es/1.mp3 ... web/story/es/8.mp3      (.ogg also works)
web/story/<lang>/<n>.mp3                        (any other language, same names)
```

When `story/<lang>/<n>.mp3` (or `.ogg`) exists, the page plays it with the
scene and moves on when it ends. When it does not, the scene is timed by the
length of its text and the page is silent apart from the music of
`web/audio.js`. A language without files simply has no narration.

The deploy copies this directory from the build box; the audio and video
files are ignored by git (`.gitignore`).
