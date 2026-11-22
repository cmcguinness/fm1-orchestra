"""Build carol-of-the-bells.mid: our 8-part bell arrangement of Leontovych.

    .venv/bin/python songs/carol-of-the-bells/build_carol.py [--bpm 168]

The notes are Mykola Leontovych's four-voice setting of Shchedryk (1916,
public domain), transcribed below in LilyPond's relative notation, checked
against the setting given in Wikipedia's "Shchedryk (song)" article. The
arrangement on top (which instrument plays what, when, how loud, octave
doublings, the tolling bells) is ours and, like the rest of this repository,
CC0.

Form, as Leontovych wrote it: one bar of the four-note ostinato, a 31-bar
body played twice (first and second endings), 68 bars in all. The voices
enter one by one over the ostinato, the melody climbs to the top for the
"d c d bes" bars, and it dies away to a single echo of the ostinato.
"""

import argparse
import re
from pathlib import Path

import mido

HERE = Path(__file__).resolve().parent
OUT = HERE / "carol-of-the-bells.mid"
TPB = 480
BAR = 3 * TPB                       # 3/4

# --- Leontovych's four voices: intro | body (played twice) | 1st | 2nd ending.
# "{n ... }" is LilyPond's \repeat unfold n: the group is read once and then
# repeated at the same pitches (relative octaves don't creep upward).
VOICES = {
    "soprano": ("c''", [
        "bes4 a8 bes g4",
        "{15 bes4 a8 bes g4 } {4 d'4 c8 d bes4 } "
        "g'4 g8 g f es | d4 d8 d c bes | c4 c8 c d c | g4 g8 g g4 | "
        "d8 e fis g a bes | c d c4 bes | d,8 e fis g a bes | c d c4 bes | "
        "{4 bes4 a8 bes g4 }",
        "bes4 a8 bes g4",
        "g2.~ | g2.~ | g2. | d'4 c8 d g,4",
    ]),
    "alto": ("c'", [
        "r2.",
        "r2. r2. r2. {2 g'2. f es d } {4 g4 g8 g g4 } {4 bes4 a8 bes g4 } "
        "{4 g4 g8 g g4 } d2. e4 fis g d2. e4 fis g d2. c f es",
        "d2 r4",
        "d2.~ d~ d bes'4 a8 bes g4",
    ]),
    "tenor": ("c'", [
        "r2.",
        "{7 r2. } es2. bes c g "
        "c4 c8 c c4 d4 d8 d d4 es4 es8 es es4 d4 d8 d d4 "
        "d2. e f4 es d g8 f es4 d "
        "d4 es8 es d c d4 d8 d d4 es es8 es f es d4 d8 d d4 "
        "{4 bes4 a8 bes g4 } g2.~ g~ g~ g~",
        "g2 r4",
        "{3 bes4 a8 bes g4 } r2.",
    ]),
    "bass": ("c", [
        "r2.",
        "{11 r2. } es4 es8 es es4 g g8 g g4 c c8 c c4 g g8 g g4 "
        "{4 g g8 g g4 } {4 bes a8 bes g4 } "
        "d2. d d~ d2 es4 f2. es d c",
        "g2 r4",
        "g2.~ g~ g r2.",
    ]),
}

STEPS = {"c": 0, "d": 1, "e": 2, "f": 3, "g": 4, "a": 5, "b": 6}
SEMIS = [0, 2, 4, 5, 7, 9, 11]
NOTE = re.compile(r"^([a-gr])((?:is|es)*)([',]*)(\d*)(\.?)(~?)$")


def parse(start: str, segments: list[str]) -> list[list[tuple[int | None, int, bool]]]:
    """Relative-mode notes -> per segment [(midi or None for a rest, ticks, tied)].

    Only the notation used above: notes, rests, accidentals is/es, octave
    marks, durations (sticky, as in LilyPond), dots, ties, bar checks."""
    m = NOTE.match(start)
    # Diatonic steps: c (no marks) is step 21 = MIDI 48, so c' = middle C.
    prev = 3 * 7 + STEPS[m.group(1)] + 7 * m.group(3).count("'") - 7 * m.group(3).count(",")
    dur = TPB
    out = []
    for text in segments:
        notes = []
        groups = []                                 # open {n groups: (n, start index)
        for tok in text.replace("|", " ").split():
            if tok.startswith("{"):
                groups.append((int(tok[1:]), len(notes)))
                continue
            if tok == "}":
                n, begin = groups.pop()
                notes.extend(notes[begin:] * (n - 1))
                continue
            tok = re.sub(r"^(e|a)s", r"\1es", tok)     # Dutch names: es = e-flat, as = a-flat
            m = NOTE.match(tok)
            if not m:
                raise ValueError(f"can't read {tok!r}")
            letter, acc, marks, num, dot, tie = m.groups()
            if num:
                dur = 4 * TPB // int(num)
                if dot:
                    dur = dur * 3 // 2
            elif dot:
                raise ValueError(f"dot without a duration in {tok!r}")
            if letter == "r":
                notes.append((None, dur, False))
                continue
            step = STEPS[letter]
            octave = round((prev - step) / 7)           # nearest: within a fourth
            pitch_step = octave * 7 + step + 7 * marks.count("'") - 7 * marks.count(",")
            prev = pitch_step
            semis = (pitch_step // 7) * 12 + SEMIS[pitch_step % 7]
            semis += acc.count("is") - acc.count("es")
            notes.append((semis + 12, dur, bool(tie)))   # step 21 (c, octave 3) -> MIDI 48
        out.append(notes)
    return out


def ticks(notes) -> int:
    return sum(d for _, d, _ in notes)


def voice_lines() -> dict[str, list[tuple[int | None, int, bool]]]:
    """Each voice laid out through the whole form, ties merged."""
    lines = {}
    for name, (start, segs) in VOICES.items():
        intro, body, first, second = parse(start, segs)
        for seg, bars in ((intro, 1), (body, 31), (first, 1), (second, 4)):
            if ticks(seg) != bars * BAR:
                raise ValueError(f"{name}: a segment is {ticks(seg) / BAR:g} bars, expected {bars}")
        seq = intro + body + first + body + second
        merged = []
        for note in seq:
            if merged and merged[-1][2] and merged[-1][0] == note[0]:
                p, d, _ = merged[-1]
                merged[-1] = (p, d + note[1], note[2])
            else:
                merged.append(note)
        lines[name] = merged
    return lines


TOTAL_BARS = 1 + 31 + 1 + 31 + 4
SECOND = 1 + 31 + 1                 # bar index where the second time begins


def level(bar: int) -> float:
    """Our dynamics, 0-1, by bar (0-based): grow through each time, the second
    time bigger, then the dying close."""
    if bar < SECOND:
        pos = bar / SECOND
        return 0.35 + 0.35 * pos                    # p -> mf
    if bar < TOTAL_BARS - 4:
        pos = (bar - SECOND) / 31
        return 0.6 + 0.4 * min(1, pos * 1.6) if pos < 0.85 else 1.0 - (pos - 0.85) * 2.4
    return [0.45, 0.32, 0.22, 0.16][bar - (TOTAL_BARS - 4)]


def events(line, transpose=0, gain=1.0, bars=None, staccato=1.0):
    """(tick, note, velocity, length) for a voice line, limited to `bars`
    (a predicate on the 0-based bar number)."""
    out, at = [], 0
    for pitch, dur, _ in line:
        bar = at // BAR
        if pitch is not None and (bars is None or bars(bar)):
            vel = max(1, min(127, round(127 * level(bar) * gain)))
            out.append((at, pitch + transpose, vel, max(30, int(dur * staccato))))
        at += dur
    return out


def tolling(gain=1.0):
    """Our addition: a low bell tolled on G at the start of each phrase from the
    second time on, and once at the very end."""
    out = []
    for bar in range(SECOND, TOTAL_BARS - 4, 4):
        vel = max(1, min(127, round(127 * level(bar) * gain)))
        out.append((bar * BAR, 43, vel, BAR * 2))          # G2
    out.append(((TOTAL_BARS - 4) * BAR, 43, round(127 * 0.4 * gain), BAR * 3))
    return out


def arrangement():
    v = voice_lines()
    first, second = (lambda b: b < SECOND), (lambda b: b >= SECOND)
    return {
        # Track names must not contain one another (parts match by substring).
        # The ostinato and melody (Leontovych's soprano): bells all the way through.
        "Ostinato": events(v["soprano"], gain=0.9),
        # Second time: the soprano an octave up, glittering on top.
        "Descant": events(v["soprano"], 12, 0.6, second),
        # Inner voices: mallets the first time, a choir the second.
        "Alto": events(v["alto"], gain=0.8),
        "Tenor": events(v["tenor"], gain=0.8),
        "Choir": events(v["alto"], 0, 0.7, second) + events(v["tenor"], 0, 0.7, second),
        "Bass": events(v["bass"], gain=0.9),
        "Pedal": events(v["bass"], 0, 0.7, second),   # an octave down was too low
        "Tolling bell": tolling(0.8),
    }


def tempo_map(bpm: float) -> list[tuple[int, int]]:
    """(tick, microseconds per quarter): steady, then a ritardando over the
    last bar, as in the source's closing tempo marks."""
    base = round(60_000_000 / bpm)
    last = (TOTAL_BARS - 1) * BAR
    return [(0, base), (last, round(base * 1.4)), (last + TPB * 2, round(base * 2.2))]


def build(bpm: float, out: Path) -> None:
    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    meta = mido.MidiTrack([mido.MetaMessage("track_name", name="Carol of the Bells"),
                           mido.MetaMessage("time_signature", numerator=3, denominator=4),
                           mido.MetaMessage("key_signature", key="Gm")])
    at = 0
    for tick, tempo in tempo_map(bpm):
        meta.append(mido.MetaMessage("set_tempo", tempo=tempo, time=tick - at))
        at = tick
    meta.append(mido.MetaMessage("end_of_track", time=TOTAL_BARS * BAR - at))
    mid.tracks.append(meta)
    for name, notes in arrangement().items():
        msgs = []
        for tick, note, vel, length in notes:
            msgs.append((tick, 1, mido.Message("note_on", note=note, velocity=vel)))
            msgs.append((tick + length, 0, mido.Message("note_off", note=note)))
        msgs.sort(key=lambda m: (m[0], m[1]))
        track = mido.MidiTrack([mido.MetaMessage("track_name", name=name)])
        at = 0
        for tick, _, msg in msgs:
            track.append(msg.copy(time=tick - at))
            at = tick
        mid.tracks.append(track)
    mid.save(out)
    print(f"wrote {out} ({TOTAL_BARS} bars, {mid.length:.1f} s at {bpm:g} bpm)")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bpm", type=float, default=168, help="quarter notes a minute (default 168)")
    ap.add_argument("--out", type=Path, default=OUT, help="MIDI file to write")
    a = ap.parse_args(argv)
    if a.bpm <= 0:
        ap.error("--bpm must be positive")
    build(a.bpm, a.out)


if __name__ == "__main__":
    main()
