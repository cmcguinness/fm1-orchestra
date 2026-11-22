# fm1-orchestra — status

Goal: control an M-VAVE FM-1 from the Mac: play music, design voices,
manage patches, drive effects.

## Layout (reorganised 2026-11-21)
Two top levels: `fm1-orchestra/` (the software: fm1ctl.py, fm1/, sysex/,
tools/, tests/) and `songs/NAME/` (everything for one song: NAME.py,
NAME.mid, NAME-slides.py, NAME.mp4, CREDITS.md, scores; gitignored
`sources/` and `build/`). `local/` (gitignored) keeps machine-only files:
non-redistributable MIDI (sugar plum, Kunst der Fuge) and fm1-bank.json.
`songs-wip/NAME/` (gitignored, 2026-11-22) holds songs in progress; fm1ctl
searches it after songs/. Now: gymnopedie-1 (Mutopia PD source, built by
build_gymnopedie.py; SOFT FLUTE melody, E.PIANO 1 chords and bass, getting
there) and jingle-bells (shelved: band, Switched-On, all-MOOGER and
all-E.PIANO versions all rejected).
Run from the root: `.venv/bin/python fm1-orchestra/fm1ctl.py ...`; `pytest`
uses pytest.ini. Videos: `fm1ctl.py video NAME`. Entries below predate the
move and use the old paths (songs/X.py, scores/, videos/, sheet-music/).

## In progress (2026-11-21): Carol of the Bells
- `songs/carol-of-the-bells/`: our own arrangement of Leontovych's Shchedryk
  (1916, PD). build_carol.py holds the four voices in a LilyPond-relative
  subset (checked against Wikipedia's "Shchedryk (song)") and arranges them
  for 8 parts at 168 bpm (144 was "too slow"). Sounds picked by ear: CELESTE
  ostinato, BELL 1 descant, VIBE 1, MARIMBA (x1.5), WARM PAD 1 (+12),
  STR.PIZZ.1 bass, VIOLA SECN pedal (+12), TUB BELLS tolling.
- Rejected: F. CHOIR, ORCH-CHIME (half-pitch carriers: sounded an octave low),
  STRINGS 2, a bass doubling an octave down.
- Pans set for `--stems`; slides drafted, including the user's requested
  "Support Ukraine" slide with a QR code for https://u24.gov.ua (new "qr"
  slide kind in fm1/video.py, segno added to requirements). Didot lacks
  Cyrillic. Stems recorded and mixed; video built (5 slides, QR last so it
  holds to the end). YouTube title/description drafted.
- `song NAME --record FILE --remix` re-mixes saved stems with the song's
  current pans (no FM-1 needed; same pans reproduce the mix byte for byte).
  stems.json now records each take's channel (older files: from the name).
- README: "Making a rendition your own" (sounds, edits, balance, tempo, key,
  phrasing, reverb, panning/remix, arrangement, video). Nothing committed yet.

## Done (2026-11-19)
- USB MIDI both ways works (`fm1ctl.py identity` gets a 41-byte reply).
- DX7 single-voice (VCED) encoder, `fm1/dx7.py`; hand-built organ voices, `fm1/voices.py`.
- MIDI-file player, `fm1/player.py`: drift-free clock, one output channel,
  reference-counted notes, drops program changes and CCs.
- BWV 565 (Mutopia, public domain) at `songs/`; opening played without errors.
  Confirmed by ear ("as good as a cheesy speaker can").
- Effects via CC, `fm1/effects.py`: firmware detected from the identity reply
  (V15 uses CC 0-23, V16 uses 70-93). Until 2026-11-20 they were sent on
  ch 1, but the unit's Effect Ch was 3, so the early reverb probably never
  arrived.
  `fm1ctl.py reverb hall`, or `play --reverb hall`.
- Celesta voice (algorithm 5, three 2-op stacks), softened after listening;
  "pretty good". Player: `--track` selects by track (channels get reused
  across tracks), forwards sustain (CC 64). `fm1ctl.py tracks FILE` lists tracks.
- Sugar Plum Fairy MIDI from mfiles.co.uk ("all rights reserved") lives in
  songs/ but is gitignored, for local use only.
- Patch library: 228 public-domain DX7 banks (7,296 voices) in sysex/, from
  Dave Benson's DX7 page (see sysex/SOURCE.md). `fm1/syx.py` unpacks banks;
  `fm1ctl.py patches [search]`, `send-patch BANK:N`, `play --patch BANK:N`.
- Pianos: my hand-built `piano` was "really bad" (kept, not removed); my
  `epiano` got no verdict. Of the factory patches, rom1a:8 PIANO 1 sounded best
  ("so-so" on the flat Mutopia file). Lesson: voices designed blind work for
  forgiving sounds (organ, celesta); for hard ones, start from library patches.
- Clair de Lune performance MIDI (Krueger, CC BY-SA) in songs/; credits in songs/CREDITS.md.
- Aquarium (Saint-Saens), Pajares arrangement from Kunst der Fuge, gitignored.
  dxoc12:20 GLASSHARP1 sustains forever and has 18-23x modulators: too
  harsh/whiny for the E5-F7 melody.

## Done (2026-11-20)
- Upgraded the unit to firmware V16 (M-UPGRADE 3.11 for Mac, file
  FM-1.fwsc from m-vave.com/download). M-UPGRADE showed "Create MIDI
  enumerator: -304" in its verify step, but the flash worked: identity now
  reads FM-1_016. User presets survived.
- V16 is multitimbral: 8 parts ("Voice1-8"), each with its own preset, MIDI
  channel, level, pan, on/off; 20 notes shared. On the unit: turn PRESETS
  to open the list, then SELECT to reach FX / Voice1-8; K1-K4 = MIDI Ch,
  Level, Pan, On/Off.
- A single-voice dump goes to the part SELECTED on the unit, whatever its
  channel or the SysEx channel nibble. An earlier test seemed to show routing
  by channel, but Voice2 happened to be selected; the Brandenburg audition
  disproved it. Program Change on a channel does change only that part.
- `play --part CHANNEL SOUND TRACK...` (repeatable) plays tracks on separate
  parts. Effects go on the Effect Channel, `--fx-channel` (default 16, which
  the unit is set to); `--reverb-decay` / `--reverb-mix` on play.
- Song bank (`fm1/bank.py`): `fm1ctl.py load-bank [--extra SOUND]` packs
  every sound the song modules use into one 32-voice bank sent to bank D
  (presets 097-128; the user confirms the bank on the unit). Songs pick
  sounds by Program Change. `.fm1-bank.json` (gitignored) records what was
  sent, since the unit can't be read back. Slots stay put when sounds change.
  Bank D also holds about 20 Moog audition candidates (presets 099-117).
- Per-part `expression` (CC 11, V16) sets part volume; always sent at setup.
- Score import (`fm1/score.py`, `fm1ctl.py import-score SCORE.mxl OUT.mid --bpm N`):
  MusicXML (music21) -> MIDI, one track per staff. It carries dynamics,
  hairpins, sf, fermatas, pizz./arco and pedal marks; octave lines come in
  at sounding pitch from MuseScore exports.
- Aquarium from the score: `songs/aquarium.py` + `aquarium.mid`, from
  Nevin Williams' MusicXML (IMSLP #904565, PD dedication) in sheet-music/.
  8 instruments on Voices 1-8, 66 bpm (score says only Andantino). It peaks
  at 26 notes in the last ~4 s (final pedal), so the FM-1's 20-voice limit
  steals a few there. Comparing it with the Pajares MIDI showed that file
  puts the glass harmonica an octave above the score; that's why
  GLASSHARP2 (itself an octave up) whined.
- The earlier Aquarium (Pajares MIDI) was purged 2026-11-20 at the user's
  request; the score version replaced it ("really good"). Lessons kept:
  piano arpeggio shaping (Part.shape) was liked; software rubato/jitter
  (fm1/humanize.py, still in the code) was rejected by ear.
- Sounds that never release are refused (dx7.drones; GLASS 1 caused a stuck
  tone that only PLAY/STOP cleared). Parts also take `transpose`.
- Monitoring: Rogue Amoeba Loopback (source FM-1 Audio, monitor to the
  Onyx/speakers). An ffmpeg/sox pass-through broke up (two USB clocks).
- Brandenburg 3/I rebuilt from a publishable score (the Kunst der Fuge
  sequence is personal-use only): Audiveris OMR of Chris Sawer's Mutopia
  edition (IMSLP #57477, CC BY 3.0; PDF footer says PD), proofread on the
  iMac (task bwv1048-omr) with 94 corrections, every one checked against the
  printed page (scores/). songs/brandenburg3.mid now comes from
  scores/bwv1048-1.musicxml at 100 bpm; the KdF file is kept locally as
  brandenburg3-kunstderfuge.mid for tools/compare_omr.py. Bright MOOG ROGUE
  (fade removed, parts an octave up), cellos at 85. Video:
  videos/brandenburg3.mp4 (5:28).
- Video: videos/aquarium.mp4 (1080p, 2:23), a 7-slide show over a USB recording.
  Published 2026-11-20: https://youtu.be/cEGUEfn2RJw
  `videos/make_video.py videos/aquarium.py --audio videos/build/aquarium.wav --out videos/aquarium.mp4`
  (slides in videos/aquarium.py; Pillow + ffmpeg; Didot/Avenir Next fonts).
- Recording now captures with sounddevice (by device number). ffmpeg's
  AVFoundation input dropped ~5% of samples (first take was 2:15 for a 2:24
  performance), and sox can't open "FM-1 Audio" because an input and an output
  share that name. The Loopback device passes nothing to recording apps.
- `--record FILE` on play/song (`fm1/record.py`): the FM-1 is a USB audio
  interface ("FM-1 Audio", 2 ch, 44.1 kHz). ffmpeg captures it; silence is
  trimmed and the peak normalised to -1 dBFS (`--no-normalize` keeps the
  captured level). The level follows the FM-1's volume knob. Needs ffmpeg.
- Brandenburg 3, I (Kunst der Fuge MIDI, gitignored), Switched-On Bach style
  ("it's really good"): 8 parts, MOOG ROGUE (dxoc14:8) on violins, MOOGER
  (mike2:4) / ROGUE alternating on violas, ROGUE cellos, MOOGER bass; violas
  expression 100, low parts 50; room reverb, decay 15, mix 3 (hall was
  "way too much"). Unit: Voice1-8 on MIDI Ch 1-8.
- Aquarium, "wow, this sounds great" / "amazing":
  `fm1ctl.py song aquarium` (songs/aquarium.py; glass now on ch 2). The glass's rising runs
  (about 30 ms per note, around 1:40) were inaudible: GLASSHARP2's main carrier OP1 has
  attack rate 47 and velocity sensitivity only 2, so louder velocities barely
  helped. Raising OP1's attack to 80 fixed it ("that did it"). Not the speaker:
  the same scale played slowly was clear.
- Song modules (`fm1/song.py`): `songs/NAME.py` defines `SONG = Song(...)`
  with parts (channel, sound, edits, tracks, velocity), reverb, pedal,
  speed and transpose. It can define `perform(session)` to take over playing.
  `fm1ctl.py song aquarium`, `fm1ctl.py songs`; `play FILE` uses a song module
  that names the file unless given --voice/--patch/--part/--track/--no-song.
  `--part` on the command line builds the same Song object.
- `--velocity CHANNEL SCALE` scales a part's velocities; sounds accept field
  edits, `BANK:N,op1.r1=80,fb=3` (`fm1/syx.py` edit()).

## Done (2026-11-21)
- Brandenburg 2/III, the Firing Line theme: `songs/brandenburg2.py` + Mutopia's
  public-domain MIDI (trumpet part coded an octave low, so +12). Video:
  videos/brandenburg2.mp4 (2:49), from a panned stem mix.
- Phrasing (`fm1/articulate.py`): Part `accent` (metric velocity from the
  file's tempo map and time signature), `vary` (repeatable velocity jitter),
  `articulation` (notes released early, never lengthened). Liked; unlike
  humanize, start times aren't touched.
- DX7 LFO/global edits: lfo.speed/delay/pmd/amd/sync/wave, pms, sync.
- Trumpet (TRUMPET 7, brass3:19), many rounds by ear: less feedback, a
  high-note roll-off, envelopes that hit then soften, vibrato (V3). Its
  "hitting metal" attack was op5, a modulator at inharmonic 3.18 peaking at
  note-on: tuned to 3, burst cut, op6 blip removed. The panel's ENV Attack
  10% then cured the tapping; ENV isn't MIDI-controllable or in SysEx, so it
  was rebuilt as slower R1s in the patch (picked by ear).
- Real-string patches (nine violins, four solo, four viola, five cello) never
  sounded like strings; the strings went Switched-On (ROGUE/MOOGER). RECORDERS
  was shrill (full-depth tremolo, no high roll-off); SOFT FLUTE at 127.
- Pan: the FM-1 IGNORES CC 10 (tested 2026-11-21 on the trumpet, by ear on
  USB audio). `song NAME --record FILE --stems` records each part alone and
  mixes with Part `pan` (`fm1/stems.py`, constant-power pan, stems mono-folded).
  Takes align on Recorder.mark() (PortAudio clock); note onsets after the
  mark spread 36-46 ms over five takes, so parts sit within ~10 ms.

## Known facts about the FM-1
- It IGNORES All Notes Off (V15 and V16) (CC 123) and All Sound Off (CC 120). Only
  individual note-offs release voices: `fm1ctl.py panic` does that on all
  channels; the player does it on exit, and handles SIGTERM/SIGHUP so a
  killed player still cleans up.
- Sustain pedal is applied in software per track (deferred note-offs); the
  synth never receives CC 64. A shared synth pedal made pedalled piano parts
  hold an unpedalled melody forever (the Aquarium drone, 2026-11-19).
- No reply to DX7 dump requests (F0 43 2n 00/09 F7). Exports start on the unit (GLOBE → Export).
- Single-voice dump lands in the edit buffer of the part selected on the unit; SAVE to keep it.
- Pan (CC 10) is IGNORED (tested 2026-11-21 over USB audio). Pan exists only
  on the unit (PRESETS list, SELECT to the Voice, K3, then SAVE -> Globe);
  for recordings use `--stems`.
- The panel's ENV (Attack/Decay/Sustain/Release, 0-100%) is an extra
  envelope stored on the unit: no MIDI control, not in SysEx exports.
- Listening setup gotcha (2026-11-20): "headphones" were the Onyx monitoring
  the Lewitt mic, which picked up the Anker speaker playing the FM-1. Heard
  that way, everything sounded band-passed. Judge sounds from the FM-1's
  headphone jack or its USB audio (record with --record).
- V16 panic on the unit: hold PLAY/STOP. On V16, notes 0-26 on the Effect
  Channel light the key LEDs instead of playing; CC 7 = master volume.
- CoreMIDI sometimes fails to create a client (error -304) right after another
  client closes; retrying works. M-UPGRADE hit the same error.
- Python 3.13/3.14 have no python-rtmidi wheel; the venv is 3.12.

## Next steps (in rough order)
1. Song modules for the earlier pieces (Toccata, Sugar Plum, Clair de Lune).
   Then use more parts: strings/flute in Aquarium, accompaniment for Sugar Plum,
   Toccata with real organ reverb. Up to 8 parts, 20 notes total.
2. V16 keeps FX separately from presets (128 FX groups), so loading a voice no
   longer changes the effects.
3. Humanize option for playback (tempo shaping, articulation); the user
   found the strict grid "mechanical and metronomical".
4. Confirm the reverb by ear; expose the other effects (filter, delay, distortion, chorus, phaser) in the CLI.
5. Live parameter change (F0 43 1n pp qq vv F7). The "globals shifted by 2" claim needs testing.
6. Librarian: load and send DX7 `.syx` banks, receive exports from the unit.
7. Web editor with sliders.
