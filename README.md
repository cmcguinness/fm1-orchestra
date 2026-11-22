# fm1-orchestra

Play orchestral music on an **M-VAVE FM-1**, a small six-operator FM synthesizer
that speaks Yamaha DX7 SysEx, from a Mac over USB MIDI.

fm1-orchestra turns the FM-1 into an eight-part FM orchestra. It loads DX7 patches
into the synth, sends each instrument of a piece to its own FM-1 part, sets
balance and effects, and records the result straight from the FM-1's USB audio.
Pieces are described by small Python *song modules*. A score in MusicXML can be
converted into a playable MIDI file, dynamics included.

**Example:** [Saint-Saëns' "Aquarium" played by a $100 FM synth](https://youtu.be/cEGUEfn2RJw)
on YouTube (also in [`songs/aquarium/aquarium.mp4`](songs/aquarium/aquarium.mp4)): *Aquarium*
from *The Carnival of the Animals*, played by the FM-1 from a
public-domain transcription of the score. The [walkthrough below](#reproducing-aquarium-from-scratch)
rebuilds it from nothing.

## Requirements

- **macOS.** Developed on macOS 27; the audio recording path uses CoreAudio.
- **An M-VAVE FM-1 on firmware V16** (multitimbral: 8 parts, 20 voices),
  connected by USB. V15 plays single-part pieces only; see [Firmware](#upgrading-the-fm-1-to-v16).
- **Python 3.12.** `python-rtmidi` has no wheels for 3.13/3.14 on macOS yet, and
  building it from source fails.
- **[uv](https://docs.astral.sh/uv/)** (or plain `pip`) and **[Homebrew](https://brew.sh)**
  for `ffmpeg`, which is used to trim recordings and make videos.
- Something to listen with. The FM-1 has a headphone/line jack. Its USB audio
  can also be monitored through the Mac; [Rogue Amoeba Loopback](https://rogueamoeba.com/loopback/)
  with *FM-1 Audio* as the source and your speakers as the monitor works well.

## Setup

```sh
git clone https://github.com/cmcguinness/fm1-orchestra.git
cd fm1-orchestra
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
brew install ffmpeg

.venv/bin/python fm1-orchestra/fm1ctl.py ports      # should list "FM-1" outputs and inputs
.venv/bin/python fm1-orchestra/fm1ctl.py identity   # should print FM-1_016
.venv/bin/python -m pytest            # optional: the test suite needs no hardware
```

All commands below are `.venv/bin/python fm1-orchestra/fm1ctl.py ...`, run from the
repository root; every command takes `--help`.

## Setting up the FM-1 (once)

Song modules assume this layout on the unit. These settings are global, so they
survive changing songs; save them so they survive power cycles too.

1. **Give each part its own channel.** Turn the **PRESETS** knob to open the
   preset list, then turn **SELECT** to scroll to the entries above the presets:
   *FX, Voice1 … Voice8*. With a Voice highlighted, the four knobs under the
   screen are **K1 MIDI Ch, K2 Level, K3 Pan, K4 On/Off**. Set
   **Voice *n* to MIDI channel *n*** (Voice1 → 1 … Voice8 → 8), all **On**, all
   levels equal. Don't use **ALL**. The list closes after about 3 seconds idle;
   turn PRESETS again to reopen it.
2. **Move the effect channel out of the way.** Press **GLO** and set
   **Effect Ch** to **16**. Effects are controlled by CCs on this channel, and on
   V16 notes 0–26 sent there light the key LEDs instead of playing.
3. **Save.** **SAVE → Globe**.
4. Optional: set each Voice's **Pan** (K3) to taste. The FM-1 ignores MIDI pan
   (CC 10), so pan lives on the unit; for recordings, `--stems` pans in software.

## Reproducing *Aquarium* from scratch

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

## Commands

| Command | What it does |
|---|---|
| `ports`, `identity` | List MIDI ports; ask the FM-1 for its firmware version |
| `song NAME`, `songs` | Play a song module (`songs/NAME/NAME.py`); list them |
| `video NAME` | Build `songs/NAME/NAME.mp4`: its slides over `build/NAME.wav` |
| `play FILE.mid` | Play any MIDI file. `--part CH SOUND TRACK...` sends tracks to parts; `--voice`/`--patch` pick one sound. It uses a song module that names the file, unless `--no-song` |
| `load-bank` | Pack every song module's sounds (plus `--extra SOUND`) into one 32-voice bank and send it |
| `import-score SCORE.mxl OUT.mid --bpm N` | Convert MusicXML to a performance MIDI file |
| `tracks FILE.mid` | List a MIDI file's tracks (for choosing parts) |
| `patches [SEARCH]` | Search the DX7 library in `fm1-orchestra/sysex/` (7,296 voices) |
| `send-patch BANK:N`, `send-voice NAME` | Send one sound to the part selected on the unit |
| `reverb room\|hall\|plate\|off` | Set the FM-1's reverb |
| `panic`, `note` | Release every note on every channel; play a test chord |

`play` and `song` also take `--start`, `--end`, `--speed`, `--transpose`,
`--reverb`, `--no-pedal` and `--record FILE` (`.wav .flac .mp3 .m4a .aiff`).
`song NAME --record FILE --stems` records each part alone and mixes the takes
in stereo with each part's `pan` (the FM-1 ignores MIDI pan); the takes and
their start points are kept beside `FILE`, in `<FILE name>-stems/`, for re-mixing.
`--remix` re-mixes them with the song's current pans, without playing anything.

A **sound** is a library patch `BANK:N` (see `patches`), optionally with field
edits, e.g. `dxoc12:21,op1.r1=80,op3.out=0`. A built-in voice name
(`fm1ctl.py voices`) also works.

## Song modules

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

## Making a rendition your own

Every choice in a performance (which sound plays each line, how loud, where
it sits in the stereo picture, how fast, how much reverb) lives in the song's
module, `songs/NAME/NAME.py`. Change a value there and play again. The
commands below are `.venv/bin/python fm1-orchestra/fm1ctl.py ...`.

**Hear just the part you're working on.** `song NAME --start 60 --end 75`
plays from 1:00 to 1:15. `tracks songs/NAME/NAME.mid` lists the MIDI file's
tracks, which is what each part's `tracks=[...]` refers to.

**Change an instrument's sound.**
1. Find candidates in the patch library: `patches bell`, `patches string`,
   `patches --bank rom1a` (7,296 voices from public-domain DX7 banks).
2. Put the one you want in the part: `sound="dxoc09:29"` (bank file : number).
3. Load the song bank again: `load-bank`, and choose **D** on the FM-1. It
   sends every song's sounds; `load-bank --extra BANK:N` adds others you want
   to try without editing any song.
4. Play it. If the new sound comes out an octave too high or low, add
   `transpose=12` or `transpose=-12` to the part. Many DX7 patches are built
   an octave off on purpose; the comments in the song modules note the ones
   we hit.

**Tweak a sound.** `edits={...}` changes patch parameters on the way to the
synth, e.g. `edits={"op1.r1": 40, "fb": 4, "pms": 3, "lfo.pmd": 10}`:
operator fields `opN.r1-r4 l1-l4 out coarse fine detune bp ld rd lc rc rs
kvs ams mode`, and `alg fb sync lfo.speed lfo.delay lfo.pmd lfo.amd lfo.sync
lfo.wave pms`. Run `load-bank` after changing edits. A patch whose note would
never stop sounding is refused, with a suggested fix.

**Balance the parts.** `expression=` is a part's volume (0-127, default 127).
`velocity=` scales how hard its notes are played (`1.5` is 50% harder); on FM
sounds that also makes them brighter, so use it when a part is dull as well as
quiet.

**Change the tempo.** `Song(speed=1.1)` plays 10% faster, or try it first
with `song NAME --speed 1.1`. Carol of the Bells has its tempo built into the
MIDI: run `songs/carol-of-the-bells/build_carol.py --bpm 180` to rebuild it.

**Change the key.** `Song(transpose=-2)`, or `--transpose -2` to try it.

**Phrasing.** Per part: `accent=` (0-0.5) leans on strong beats, `vary=`
(0-0.2) adds slight velocity variation, `articulation=` (0.2-1) shortens notes
for a more detached style, and `shape=` (0-0.5) swells piano arpeggios.

**Reverb.** `Song(reverb=Reverb("hall", decay=40, mix=12))`: `room`, `hall`,
`plate` or `off`, decay and mix 0-100. Try settings with
`song NAME --reverb hall --reverb-decay 40 --reverb-mix 12`.

**Stereo placement.** The FM-1 ignores MIDI pan, so panning happens when you
record stems: give each part `pan=` from -1 (left) to 1 (right), then
```sh
.venv/bin/python fm1-orchestra/fm1ctl.py song NAME --record songs/NAME/build/NAME.wav --stems
```
records each part alone and mixes them. To move parts afterwards, edit the
pans and re-mix the saved takes in seconds, without the FM-1:
```sh
.venv/bin/python fm1-orchestra/fm1ctl.py song NAME --record songs/NAME/build/NAME.wav --remix
```
(Sounds, levels, tempo and phrasing are baked into the takes; change those
and record the stems again.)

**Change the arrangement itself.** Most songs play their MIDI file as is;
edit the parts' `tracks` to move lines between instruments, or give one line
to two parts for a doubling. Carol of the Bells is arranged in code:
`arrangement()` in `build_carol.py` decides which of Leontovych's voices
each track plays, the octave doublings, and when they enter; `level()` holds
the dynamics.

**Make the video.** Edit the slides in `songs/NAME/NAME-slides.py`, record to
`songs/NAME/build/NAME.wav`, then `video NAME`.

## How it works, and FM-1 quirks worth knowing

- **Sounds are loaded by Program Change, not SysEx.** On V16 a DX7 single-voice
  dump goes to whichever part is *selected on the front panel*, whatever its
  channel. So `load-bank` puts every sound in bank D once, and songs select
  them per channel with Program Change. Bank imports always need a confirmation
  on the unit; there is no prompt-free route short of raw flash writes.
- **All Notes Off (CC 123) and All Sound Off (CC 120) don't silence anything.**
  The player sends individual note-offs for everything on exit, including after
  Ctrl-C or a SIGTERM; `panic` does the same by hand. On the unit, holding
  **PLAY/STOP** is a panic.
- **Sustain pedal** is applied in software per track (deferred note-offs), so a
  pedalled piano part can't hold notes of an unpedalled melody on the same part.
- **Effects** (V16) are CC 70–93 on the Effect Channel: filter, reverb, delay,
  distortion, chorus, phaser. Expression (CC 11) sets part volume; CC 7 is master
  volume.
- **Polyphony** is 20 voices shared by all parts. *Aquarium* exceeds it only
  under the final pedal.
- **Recording:** the FM-1 is also a USB audio interface (*FM-1 Audio*, stereo,
  44.1 kHz). `--record` captures it with `sounddevice`. ffmpeg's AVFoundation
  input silently dropped about 5% of the samples, and sox can't select the device
  because an input and an output share its name.

`STATUS.md` is the running project log: findings, decisions and open threads.

## Upgrading the FM-1 to V16

1. Download **M-UPGRADE** for macOS and the **FM-1 firmware** (`FM-1.fwsc`) from
   [m-vave.com/download](https://www.m-vave.com/download).
2. Open M-UPGRADE with the FM-1 connected, choose **Select firmware**, pick the
   `.fwsc` file and start the upgrade.
3. Afterwards `fm1ctl.py identity` should print `FM-1_016`. Presets survived the
   upgrade on our unit.

In our upgrade M-UPGRADE reported *"Create MIDI enumerator: -304"* during its
verify step, yet the flash had worked. Check with `identity` before retrying.
Upgrading firmware carries some risk; back up anything you care about first.

## Project layout

```
fm1-orchestra/            the software
  fm1ctl.py            command-line interface
  fm1/                 the library: dx7 (voice encoding), syx (patch banks),
                       song (song modules, sessions), bank (song bank), player,
                       articulate (phrasing), score (MusicXML import), record,
                       stems, video, effects, port, voices
  sysex/               228 public-domain DX7 banks (see sysex/SOURCE.md)
  tools/               score tools: OMR comparison, score tokens
  tests/               pytest suite (no hardware needed)
songs/                 one folder per song, with everything specific to it
  aquarium/            aquarium.py, .mid, -slides.py, .mp4, CREDITS.md
  brandenburg2/, brandenburg3/ (with its corrected score), clair-de-lune/,
  toccata-and-fugue/
songs-wip/             gitignored: songs in progress, laid out like songs/;
                       fm1ctl finds them too (song, songs, load-bank, video).
                       Move a folder into songs/ when it's ready to publish.
local/                 gitignored: files that stay on this machine (MIDI files
                       we may not redistribute, the record of the song bank)
```

## License

Our work in this repository (the software, song modules, arrangements,
slides, videos, documentation) is dedicated to the public domain under
[CC0 1.0 Universal](LICENSE). Use it for anything, no attribution needed.

A few files come from others and keep their own terms:
- `songs/brandenburg3/score/` and `songs/brandenburg3/brandenburg3.mid` are
  derived from Chris Sawer's Mutopia edition, licensed **CC BY 3.0**: keep
  the attribution in `songs/brandenburg3/CREDITS.md` when you reuse them.
  Our corrections are CC0 as far as they can be.
- `songs/clair-de-lune/clair-de-lune-krueger.mid` is Bernd Krüger's, licensed
  **CC BY-SA 3.0 Germany**.
- `fm1-orchestra/sysex/` is a collection of public-domain DX7 patches by many
  authors; see `fm1-orchestra/sysex/SOURCE.md`.
- The other scores and MIDI files are public domain or public-domain
  dedications; each song's `CREDITS.md` says which.

## Credits and sources

- **DX7 patches:** the public-domain collection from
  [Dave Benson's DX7 page](https://homepages.abdn.ac.uk/d.j.benson/pages/html/dx7.html),
  including Yamaha's factory banks (`fm1-orchestra/sysex/SOURCE.md`).
- **Music:** each song folder's `CREDITS.md`. *Aquarium* comes from Nevin
  Williams' public-domain transcription (IMSLP #904564/#904565). Files we may
  not redistribute go in `local/`; the song's CREDITS.md says where to download
  them. (Not yet a song: Tchaikovsky's Dance of the Sugar Plum Fairy, from
  [mfiles.co.uk](https://www.mfiles.co.uk/scores/Sugar-Plum-Fairy.htm), all
  rights reserved, kept as `local/sugar-plum-fairy/sugar-plum-fairy.mid`.)
- **Libraries:** [mido](https://mido.readthedocs.io), python-rtmidi,
  [music21](https://web.mit.edu/music21/), sounddevice, Pillow, and ffmpeg.
- **FM-1 protocol notes:** M-VAVE's V16 release notes and the community research
  in [benny-sparra/fm1-dx7-patch-importer](https://github.com/benny-sparra/fm1-dx7-patch-importer).
