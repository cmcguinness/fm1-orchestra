# Walkthrough: reproducing Aquarium

From the public-domain score to a recording and a video. Do [Setup](setup.md) first.

The repository already contains the generated MIDI file and song module, so you
can skip straight to step 3. Steps 1–2 regenerate the MIDI from the score.

**1. Get the score.** From IMSLP's
[Carnival of the Animals page](https://imslp.org/wiki/Le_carnaval_des_animaux_(Saint-Saëns,_Camille)),
find *Aquarium (No.7) – For Flute, Harmonica, 2 Pianos, 2 Violins, Viola and
Cello (Williams)* and download the **Engraving Files (MuseScore 3.6.2)**,
`IMSLP904565-PMLP6099-Aquarium_(No._7).mxl`. The PDF (#904564) is handy for
reading along. Nevin Williams transcribed the 1922 Durand edition and dedicated
it to the public domain. Put the files in `songs/aquarium/sources/` (gitignored).

**2. Convert the score to MIDI.**

```sh
.venv/bin/python fm1-orchestra/fm1ctl.py import-score \
    "songs/aquarium/sources/IMSLP904565-PMLP6099-Aquarium_(No._7).mxl" \
    songs/aquarium/aquarium.mid --bpm 66
```

This makes one track per staff, at sounding pitch. Dynamics, hairpins, *sf*
accents, fermatas, pizzicato and pedal marks become velocities, note lengths and
sustain. The score says only *Andantino*; 66 is our tempo choice.

**3. Load the sounds.**

```sh
.venv/bin/python fm1-orchestra/fm1ctl.py load-bank --dry-run   # which sound goes in which preset
.venv/bin/python fm1-orchestra/fm1ctl.py load-bank
```

This **overwrites preset bank D (presets 097–128)** with every sound the song
modules use. When the FM-1 shows its bank prompt, **choose D**. The Mac records
what it sent in `local/fm1-bank.json`, because the FM-1 can't be read back. Rerun
it only when the set of sounds changes.

**4. Play it.**

```sh
.venv/bin/python fm1-orchestra/fm1ctl.py song aquarium
```

Each part gets its patch by Program Change and its level by Expression (CC 11),
and the FM-1's reverb is set. Then all eight instruments play, one per FM-1 part.

**5. Record it.**

```sh
mkdir -p songs/aquarium/build
.venv/bin/python fm1-orchestra/fm1ctl.py song aquarium --record songs/aquarium/build/aquarium.wav
```

This records from the FM-1's own USB audio input (no cables or microphones),
trims silence and normalises the peak to −1 dBFS. The capture level follows
the FM-1's volume knob. macOS asks once for microphone permission for your
terminal app.

**6. Make the video.**

```sh
.venv/bin/python fm1-orchestra/fm1ctl.py video aquarium
```

This plays the slides in `songs/aquarium/aquarium-slides.py` over
`songs/aquarium/build/aquarium.wav` and writes `songs/aquarium/aquarium.mp4`.
`fm1-orchestra/fm1/video.py` renders the slides at
1920×1080 with Pillow and crossfades them over the audio with ffmpeg. It uses
the macOS fonts Didot and Avenir Next.

### What *Aquarium* uses

| FM-1 part | Instrument | Patch (library ref) |
|---|---|---|
| Voice 1 | Piano 1 | PIANO 1 (`rom1a:8`), arpeggio figures voiced by pitch |
| Voice 2 | Glass harmonica | CRYSTALBEL (`atsu_4:28`) |
| Voice 3 | Flute | FLUTE 1 (`rom1a:24`) |
| Voice 4 | Piano 2 | PIANO 1 (`rom1a:8`), voiced |
| Voices 5–6 | Violins I, II | VIOLA SECN (`bank0043:15`), Expression 100 |
| Voices 7–8 | Violas, cellos | STRINGS 2 (`rom1a:5`), Expression 100 |

Reverb: room, decay 30, mix 7. The patches were chosen by ear in side-by-side
auditions; see the comments in `songs/aquarium/aquarium.py`.
