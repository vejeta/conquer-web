<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->
# The story's narration

`web/story.html` plays an optional narration for each of its eight scenes.
The takes for the seven languages of the site (`web/story/<lang>/1.mp3 ... 8.mp3`
with `<lang>` = `es`, `en`, `de`, `pl`, `pt-br`, `ru`, `zh`; about 1.4-2 MB each
language) are in git. Voice: Coqui XTTS-v2, zero-shot from a reference recording
supplied by the owner, the same voice in every language, under the Coqui Public
Model License (CPML, non-commercial). Each take was picked among several seeds
by a Whisper transcription against the text (word error rate), then pitched
and mastered with ffmpeg; scenes 5 and 8 use the slowed versions of the take.
In the spoken texts the name is spelled so that the model says it as one word
(es "Cónker", en "Conquer", de/pt-br "Conker", pl "Konker", ru "Конкёр", zh "康克");
the captions on the page keep "Conquer". A language without files simply
shows the text.

While a narration plays, the music bed sinks to 35% of the player's volume
(`conquerAudio.underVoice`), and the first tap (Tap to begin) unlocks the
narration element for the whole story.

The videos `web/story/conquer-story.<lang>.mp4` (1920x1080) and
`conquer-story.<lang>.vertical.mp4` (1080x1920), one per language, are made by
`tools/story/render.py <lang>`. The index and the last scene link the video of
the page's language and fall back to the Spanish one for a language without it.
