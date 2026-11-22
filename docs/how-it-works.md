# How it works

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

[`STATUS.md`](../STATUS.md) summarises the project: what works, what we learned, what is next.

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
  aquarium/            aquarium.py, .mid, -slides.py, CREDITS.md (and, built
                       locally and gitignored, build/ and aquarium.mp4)
  brandenburg2/, brandenburg3/ (with its corrected score), clair-de-lune/,
  toccata-and-fugue/
songs-wip/             gitignored: songs in progress, laid out like songs/;
                       fm1ctl finds them too (song, songs, load-bank, video).
                       Move a folder into songs/ when it's ready to publish.
local/                 gitignored: files that stay on this machine (MIDI files
                       we may not redistribute, the record of the song bank)
```
