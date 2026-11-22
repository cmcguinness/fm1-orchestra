# Song modules

Each song has its own folder, `songs/NAME/`, holding everything specific to it:
the song module `NAME.py`, the MIDI file `NAME.mid` it plays, the video's slides
(`NAME-slides.py`) and video, `CREDITS.md`, and any score files. Two subfolders
stay out of git: `sources/` (downloaded scores) and `build/` (recordings, stems,
slide images). The song module looks like this:

```python
from fm1.song import Part, Reverb, Song

SONG = Song(
    title="Aquarium (Saint-Saens)",
    parts=[
        Part(channel=1, sound="rom1a:8", tracks=["Piano 1"], shape=0.25),
        Part(channel=2, sound="atsu_4:28", tracks=["Glass Harmonica"]),
        # ...
        Part(channel=8, sound="rom1a:5", tracks=["Violoncellos"], expression=100),
    ],
    reverb=Reverb("room", decay=30, mix=7),
)
```

**Part fields:**
- `channel`: the FM-1 part's MIDI channel.
- `tracks`: track names (substrings) or numbers.
- `sound`: a patch with optional `edits`, or `None` to keep the part's sound.
- `velocity`: a multiplier.
- `expression`: part volume, 0–127.
- `transpose`: semitones.
- `shape`: voices arpeggio figures, so each ripple swells to its top note.
- `accent`: strong beats louder and fast notes lighter, from the file's metre.
- `vary`: a small, repeatable velocity variation.
- `articulation`: the fraction of each note's length played (below 1 = detached).
- `pan`: -1 (left) to 1 (right), applied only by `--stems` recordings.

**Song fields:** `reverb`, `pedal`, `speed`, `transpose` and `humanize` (an
experimental phrase rubato; it didn't suit Aquarium).

A module can also define `perform(session)` to take over playback entirely.

Everything is checked before any MIDI is sent: two parts on one channel, a part
on the effect channel, a misspelled track, a sound missing from the bank. Sounds
that **never stop sounding** after release are refused, with a suggested fix:
an audible operator whose envelope's final level isn't zero leaves a stuck tone.
