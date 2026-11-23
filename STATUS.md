# fm1-orchestra — status

Goal: play orchestral music on an M-VAVE FM-1 from a Mac: load DX7 patches,
send each instrument to its own FM-1 part, set balance and effects, record
the result from the FM-1's USB audio, and make a slide-show video of it.

## Layout
- `fm1-orchestra/`: the software (fm1ctl.py, fm1/, sysex/, tools/, tests/).
- `docs/`: setup, the Aquarium walkthrough, commands, song modules,
  customizing a rendition, how it works. README.md is the short front page.
- `songs/NAME/`: everything for one song: NAME.py (the song module),
  NAME.mid, NAME-slides.py, CREDITS.md, scores and build scripts.
  Gitignored per song: `sources/` (downloads), `build/` (recordings, stems,
  slide images) and NAME.mp4 (videos are built locally, not kept in git).
- `songs-wip/` (gitignored): songs in progress; fm1ctl searches it after
  `songs/`.
- `local/` (gitignored): files that stay on one machine, such as MIDI we
  may not redistribute and `fm1-bank.json`, the record of the song bank.

Run from the root: `.venv/bin/python fm1-orchestra/fm1ctl.py ...`;
`pytest` (49 tests, no hardware needed).

## Songs
| Song | Source | Video |
|---|---|---|
| Aquarium (Saint-Saëns) | Nevin Williams' MusicXML, IMSLP, PD dedication | https://youtu.be/cEGUEfn2RJw |
| Brandenburg 2/III (Bach) | Mutopia 1680, PD; trumpet +12 | built locally |
| Brandenburg 3/I (Bach) | Audiveris OMR of Chris Sawer's Mutopia score (CC BY 3.0), 94 hand corrections | built locally |
| Carol of the Bells (Leontovych) | our own arrangement, `build_carol.py` | built locally |

`clair-de-lune/` and `toccata-and-fugue/` hold MIDI files without song
modules yet.

## What works
- USB MIDI both ways; DX7 single-voice and 32-voice bank SysEx; patch
  library browsing and field edits (`BANK:N,op1.r1=80,fb=3`, LFO/globals,
  transpose); named library sounds in `fm1/sounds.py` (berlin-bass).
  `patches` flags patches whose transpose byte shifts their octave, and ones
  rejected by ear (`REJECTED` in `fm1/sounds.py`; `--hide-rejected`).
- Song bank: `load-bank` packs every song's sounds into bank D (presets
  097-128); songs select them by Program Change.
- Song modules: per-part sound, tracks, velocity, expression (CC 11),
  transpose, phrasing (accent, vary, articulation, shape), pan.
- Score import: MusicXML -> MIDI with dynamics, hairpins, pedal, pizz./arco.
- Recording from FM-1 Audio (sounddevice), trimmed and normalised; `--stems`
  records each part alone and mixes them panned (the FM-1 ignores CC 10);
  `--remix` re-pans saved stems without the synth.
- Live playing: `play-keys` passes a MIDI keyboard on the Mac through to one
  FM-1 part, with a song part's sound or any patch.
- Videos: `fm1ctl.py video NAME` (Pillow + ffmpeg; title, bullets, table and
  QR-code slides) over `build/NAME.wav`.

## Known facts about the FM-1 (firmware V16)
- Multitimbral: 8 parts ("Voice1-8"), 20 notes shared. Each part has its own
  preset, MIDI channel, level, pan and on/off, set on the unit (PRESETS,
  then SELECT to the Voice; K1-K4 = MIDI Ch, Level, Pan, On/Off).
- A single-voice dump lands in the edit buffer of the part selected on the
  unit, whatever the MIDI channel. Program Change affects only its channel.
- It ignores All Notes Off (CC 123), All Sound Off (CC 120) and pan (CC 10).
  `fm1ctl.py panic` sends individual note-offs; on the unit, hold PLAY/STOP.
- No reply to DX7 dump requests; exports start on the unit (GLOBE -> Export).
- The panel ENV (Attack/Decay/Sustain/Release) has no MIDI control and is not
  in SysEx; reproduce its effect with the patch's own envelope rates.
- Effects listen on the Effect Channel (default 16): V15 uses CC 0-23, V16
  CC 70-93. On V16, notes 0-26 on the Effect Channel light key LEDs; CC 7 is
  master volume.
- Sustain pedal is applied in software per track (a shared synth pedal
  holds other parts' notes).
- Patches that never release (an operator with L4 > 0) are refused; they
  cause stuck tones.
- Some patches sound an octave off (a transpose byte, or carriers at
  ratio 0.5/2); fix with a Part's `transpose=±12`.
- CoreMIDI sometimes fails to create a client (-304) right after another
  closes; a retry works.
- Judge sounds from the headphone jack or a USB recording, not through a
  microphone or a small speaker.
- python-rtmidi has no wheels for Python 3.13/3.14 on macOS; use 3.12.

## Lessons
- Voices designed from scratch work for forgiving sounds (organ, celesta);
  for hard ones (piano, strings, brass), start from library patches.
- Realistic string patches never sounded like strings; Switched-On synth
  strings (MOOG ROGUE, MOOGER) did.
- An inharmonic modulator peaking at note-on gives a metallic "tap"; tune it
  to a whole ratio or slow its attack.
- Software rubato and timing jitter were rejected by ear; velocity phrasing
  (accent, vary, articulation) was liked.

## Next steps (rough order)
1. Song modules for Clair de Lune and the Toccata.
2. Expose the other effects (filter, delay, distortion, chorus, phaser).
3. Live parameter changes (F0 43 1n pp qq vv F7).
4. A librarian: send `.syx` banks, receive exports from the unit.
