# fm1-orchestra

Play orchestral music on an **M-VAVE FM-1**, a small six-operator FM synthesizer
that speaks Yamaha DX7 SysEx, from a Mac over USB MIDI.

fm1-orchestra turns the FM-1 into an eight-part FM orchestra. It loads DX7 patches
into the synth, sends each instrument of a piece to its own FM-1 part, sets
balance and effects, and records the result straight from the FM-1's USB audio.
Pieces are described by small Python *song modules*. A score in MusicXML can be
converted into a playable MIDI file, dynamics included.

**Example:** [Saint-Saëns' "Aquarium" played by a $100 FM synth](https://youtu.be/cEGUEfn2RJw)
on YouTube: *Aquarium* from *The Carnival of the Animals*, played by the FM-1
from a public-domain transcription of the score. The
[walkthrough](docs/aquarium-walkthrough.md) rebuilds it from nothing.

## Quick start

You need macOS, an FM-1 on firmware V16 connected by USB, Python 3.12,
[uv](https://docs.astral.sh/uv/) and `ffmpeg` (Homebrew). Details, and the
one-time settings on the FM-1 itself, are in [docs/setup.md](docs/setup.md).

```sh
git clone https://github.com/cmcguinness/fm1-orchestra.git
cd fm1-orchestra
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
brew install ffmpeg

.venv/bin/python fm1-orchestra/fm1ctl.py identity    # should print FM-1_016
.venv/bin/python fm1-orchestra/fm1ctl.py load-bank   # then choose bank D on the FM-1
.venv/bin/python fm1-orchestra/fm1ctl.py song aquarium
```

Every command takes `--help`.

## Documentation

| Page | What's in it |
|---|---|
| [Setup](docs/setup.md) | Requirements, installing, the FM-1's channel and effect settings, upgrading to firmware V16 |
| [Walkthrough: Aquarium](docs/aquarium-walkthrough.md) | Score to MIDI, loading sounds, playing, recording and making the video |
| [Commands](docs/commands.md) | Every `fm1ctl.py` command and its options |
| [Song modules](docs/song-modules.md) | How a song is described: parts, sounds, levels, phrasing |
| [Making a rendition your own](docs/customizing.md) | Changing sounds, balance, tempo, key, reverb, stereo panning, the arrangement |
| [How it works](docs/how-it-works.md) | FM-1 quirks worth knowing, and the project layout |

## Songs

| Song | Folder |
|---|---|
| Saint-Saëns, *Aquarium* (The Carnival of the Animals) | [`songs/aquarium/`](songs/aquarium/) |
| Bach, Brandenburg Concerto No. 2, III | [`songs/brandenburg2/`](songs/brandenburg2/) |
| Bach, Brandenburg Concerto No. 3, I, Switched-On style | [`songs/brandenburg3/`](songs/brandenburg3/) |
| Leontovych, *Carol of the Bells* (Shchedryk), our FM bell arrangement | [`songs/carol-of-the-bells/`](songs/carol-of-the-bells/) |

Each folder's `CREDITS.md` says where its music comes from.

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
