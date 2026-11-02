<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->
# The story

`web/story.html` needs no tool: it is a page, and its music is
`web/audio.js` (the beds and effects rendered by `tools/sound`, see
`tools/sound/README.md`). The narration is optional and rendered offline by
the owner; see `web/story/README.md` for where the files go.

`render.py LANGUAGE` makes the story videos (`web/story/conquer-story.<l>.mp4`
and `.vertical.mp4`): it drives `story.html?render=1` in Chrome, builds the
music with ffmpeg from `web/sound/*.ogg` following the story's cues, mixes it
12 dB under the narration (-16 LUFS, master -14 LUFS) and encodes H.264/AAC.
