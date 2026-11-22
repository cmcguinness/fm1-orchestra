# Making a rendition your own

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
