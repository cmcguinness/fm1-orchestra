# Commands

Everything is done through one program, `fm1-orchestra/fm1ctl.py`. Each
command below is its first argument. Run it from the repository root with the
project's Python (set up in [Setup](setup.md)):

```sh
.venv/bin/python fm1-orchestra/fm1ctl.py COMMAND [ARGUMENTS] [OPTIONS]
```

For example:

```sh
.venv/bin/python fm1-orchestra/fm1ctl.py songs                         # list the songs
.venv/bin/python fm1-orchestra/fm1ctl.py song aquarium --start 60      # play from 1:00
.venv/bin/python fm1-orchestra/fm1ctl.py patches bell                  # search the patches
.venv/bin/python fm1-orchestra/fm1ctl.py song --help                   # one command's options
```

`fm1ctl.py --help` lists the commands, and `fm1ctl.py COMMAND --help` gives
one command's arguments and options. Commands that talk to the synth need the
FM-1 connected by USB.

| Command | What it does |
|---|---|
| `ports`, `identity` | List MIDI ports; ask the FM-1 for its firmware version |
| `voices` | List the built-in voices, designed in code (celesta, epiano, flute, piano, plenum), and the named library sounds (berlin-bass) |
| `song NAME`, `songs` | Play a song module (`songs/NAME/NAME.py`); list them |
| `video NAME` | Build `songs/NAME/NAME.mp4`: its slides over `build/NAME.wav` |
| `play FILE.mid` | Play any MIDI file. `--part CH SOUND TRACK...` sends tracks to parts; `--voice`/`--patch` pick one sound. It uses a song module that names the file, unless `--no-song` |
| `load-bank` | Pack every song module's sounds (plus `--extra SOUND`) into one 32-voice bank and send it |
| `import-score SCORE.mxl OUT.mid --bpm N` | Convert MusicXML to a performance MIDI file |
| `tracks FILE.mid` | List a MIDI file's tracks (for choosing parts) |
| `patches [SEARCH]` | Search the DX7 library in `fm1-orchestra/sysex/` (7,296 voices) |
| `send-patch BANK:N`, `send-voice NAME` | Send one sound to the part selected on the unit |
| `reverb room\|hall\|plate\|off` | Set the FM-1's reverb |
| `play-keys` | Play the FM-1 live from a MIDI keyboard plugged into the Mac (see below) |
| `panic`, `note` | Release every note on every channel; play a test chord |

`play` and `song` also take `--start`, `--end`, `--speed`, `--transpose`,
`--reverb`, `--no-pedal` and `--record FILE` (`.wav .flac .mp3 .m4a .aiff`).
`song NAME --record FILE --stems` records each part alone and mixes the takes
in stereo with each part's `pan` (the FM-1 ignores MIDI pan); the takes and
their start points are kept beside `FILE`, in `<FILE name>-stems/`, for re-mixing.
`--remix` re-mixes them with the song's current pans, without playing anything.

A **sound** is a library patch `BANK:N` (see `patches`), optionally with field
edits, e.g. `dxoc12:21,op1.r1=80,op3.out=0`. A built-in voice name or a
named library sound (`fm1ctl.py voices`) also works. A named sound is a short
name for a library patch plus edits, kept in `fm1-orchestra/fm1/sounds.py`:
`berlin-bass` is the DX7's factory BASS 2 with a delayed vibrato, the fretless
line of Berlin's "Take My Breath Away". More edits can follow a name, e.g.
`berlin-bass,lfo.pmd=20`.

Edit fields: `opN.` plus `r1`-`r4`, `l1`-`l4` (envelope), `out`, `coarse`,
`fine`, `detune`, `kvs`, `rs`, `ams`, `mode`, `bp ld rd lc rc` (keyboard
scaling); globals `alg`, `fb`, `sync`, `lfo.speed`, `lfo.delay`, `lfo.pmd`,
`lfo.amd`, `lfo.sync`, `lfo.wave`, `pms`, and `transpose` (0-48, 24 = none).

Many library patches carry a transpose byte that shifts them an octave or two
down (or up). The FM-1 honours it, so such a patch sounds in the wrong octave
next to the others. `patches` marks these as `[transpose -12: ...]`; add
`,transpose=24` to the sound to play it at pitch.

## Playing from a keyboard

The FM-1 can't host a USB keyboard, so `play-keys` passes the keyboard's notes
on from the Mac until you press ctrl-C, then releases anything still sounding.

```sh
fm1ctl.py play-keys --keyboard LPK25                              # part 1, its current sound
fm1ctl.py play-keys --keyboard LPK25 --sound rom1a:11 --channel 2 # E.PIANO 1 on part 2
fm1ctl.py play-keys --keyboard LPK25 --song aquarium --part 1     # a song part's sound and level
```

`--keyboard` is part of the input's name (see `ports`); it can be left out when
the keyboard is the only MIDI input besides the FM-1. Whatever channel the
keyboard sends on, the notes go to `--channel`. A sound in the song bank is
picked by Program Change, so it works on any part; any other sound is sent to
the part selected on the unit. `--transpose`, `--reverb` and `--show` (print
what's sent) also work. Notes, the sustain pedal, the mod wheel, pitch bend,
aftertouch and program changes pass; other CCs don't, since they could change
the FM-1's effects.

## Options for every command

These go **before** the command name, e.g.
`fm1ctl.py --port "FM-1" song aquarium`:

| Option | Default | Meaning |
|---|---|---|
| `--port PORT` | `FM-1` | Part of the MIDI port's name, if yours differs (see `ports`) |
| `--library FOLDER` | `fm1-orchestra/sysex` | Folder of DX7 `.syx` banks |
| `--songs FOLDER` | `songs` (plus `songs-wip`) | Folder of song folders |
| `--fx-channel N` | 16 | The FM-1's Effect Ch (GLO page), where effect CCs go |
