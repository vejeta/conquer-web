<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->
# The story's narration

`web/story.html` plays an optional narration for each of its eight scenes.
The Spanish takes (`web/story/es/1.mp3 ... 8.mp3`, about 1.4 MB) are in git.
Voice: Coqui XTTS-v2, zero-shot from a reference recording supplied by the
owner, under the Coqui Public Model License (CPML, non-commercial); scenes 5
and 8 use the slowed versions of the take. Other languages are not in git
(`.gitignore`): put their files in `web/story/<lang>/<n>.mp3`.

While a narration plays, the music bed sinks to 35% of the player's volume
(`conquerAudio.underVoice`), and the first tap (Tap to begin) unlocks the
narration element for the whole story.

The videos `web/story/conquer-story.es.mp4` (1920x1080) and
`conquer-story.es.vertical.mp4` (1080x1920) are made by `tools/story/render.py`.
