<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->
# tools/sound

`build.py` renders the game's sound set to `web/sound/*.ogg` (Vorbis, 44.1 kHz,
about 96 kbps). The OGG files are generated and committed; `web/audio.js` plays them.

```
pip install numpy scipy        # and ffmpeg with libvorbis
python3 tools/sound/build.py                 # everything (about 3 minutes)
python3 tools/sound/build.py map-human ui-tap
python3 tools/sound/build.py --keep /tmp/wav --report map-human   # keep the WAVs; print levels, energy above 6 kHz and the loop seam
```

Everything is played by a SoundFont sampler (`sf2.py`, in numpy) through a long
convolution reverb (`music.py`); the shipped files contain no oscillators and
no synthesised noise. `score.py`, `sfx.py`, `voice.py` and `rain.py` are the
modules of the story's renderer, kept as they were because `music.py` imports
them; `build.py` uses only `Score` from `score.py`.

## The SoundFont

`FluidR3_GM.sf2` (Frank Wen, MIT-style licence: free to use, copy and
distribute, including in works that are sold, with the licence notice kept) is
**not in the repository**. Put it at `~/.cache/conquer-sf2/FluidR3_GM.sf2` or
point `$CONQUER_SF2` at it. The rendered recordings are derived works of its
samples, which that licence allows; its text:
<https://packages.debian.org/fluid-soundfont-gm> (its copyright file)

## The music

Original, no borrowed melody: two eight-bar phrases (A, B) in A aeolian, 6/8, 54
to 66 bpm. A soprano "ah" (the SoundFont's choir, legato) sings the melody over
Celtic-harp arpeggios, a low strings drone and high strings, in a cathedral-sized
reverb. Each race colours it: humans a low horn and a far brush snare, elves a
flute, glockenspiel and more strings (up a tone), dwarves low brass, timpani and
bell strokes like an anvil (down a fifth), orcs low voices, taiko and heavy brass
(down a major third). Timpani and taiko appear only in the dwarf and orc beds,
the combat bed and a few effects.

Each loop is four phrases that rise and fall in level (quiet, building, full,
receding), 58 to 64 s long (builder and report 47 to 48 s, combat 40 s,
app-home 30 s).

## Seamless loops

A loop of L seconds is rendered with 8 s of tail: the notes still ringing at L
and the reverb's decay run past the end. `fold()` adds that tail back onto the
start of the file, so the beginning already contains the end of the music, exactly
as if it had been going round for ever. No cross-fade is needed; `--report`
prints the jump between the last and the first sample, which is smaller than the
typical step between neighbouring samples. Beds are low-passed at 6 kHz
(4th order) and levelled to -24 dBFS RMS (-3 dBFS peak limit).

## Files

Beds (loops): `map-human`, `map-elf`, `map-dwarf`, `map-orc`, `builder`,
`report`, `combat`, `app-home`. Effects: `ui-tap`, `move`, `bump`, `open`,
`close`, `news`, `message`, `turn`, `combat-hit`, `found`, `approved`,
`app-doors-open`, `app-doors-fail`.
