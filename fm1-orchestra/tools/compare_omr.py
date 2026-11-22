"""Check a MusicXML score of Brandenburg 3/I: bar lengths, and differences
from a locator MIDI file.

    python fm1-orchestra/tools/compare_omr.py SCORE.(mxl|musicxml) [--midi local/brandenburg3/brandenburg3-kunstderfuge.mid]
                                [--bars 0-136] [--explained FILE] [--part N]

The MIDI is only used to point at bars that may be misread; it is not a
source of notes.  Its tracks 1..10 are taken to be the score's parts in order.
Alignment: each track's first note-on is the start of the pickup, half a beat
before bar 1, so bar = 0 for beat < 0, else floor(beat / 4) + 1.

A bar is reported when its (onset, pitch) list differs from the MIDI's.  When
every pitch differs by the same whole number of octaves and the onsets agree,
the difference is reported as an octave shift.  --explained names a file of
"part bar" lines (e.g. the corrections log's edition-difference table) whose
bars are listed separately instead of as unexplained differences.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoretokens import bar_length, read_musicxml  # noqa: E402

PICKUP = Fraction(1, 2)
LAST_BAR = 136
FINAL = Fraction(7, 2)


def expected_length(n: int) -> Fraction:
    return PICKUP if n == 0 else FINAL if n == LAST_BAR else Fraction(4)


def score_bars(parts, last_bar=LAST_BAR):
    """Per part: {bar: sorted [(onset in quarters from the barline, midi pitch)]}.
    Tied continuations are not new onsets."""
    out = []
    for part in parts:
        bars = {}
        tied = set()
        for n, events in enumerate(part.bars[:last_bar + 1]):
            at = Fraction(0) if n else (PICKUP - bar_length(events))
            rows = []
            for e in events:
                if e.whole_bar:
                    break
                for p in e.midi():
                    if p not in tied:
                        rows.append((at, p))
                tied = set(e.midi()) if "~" in e.marks else set()
                at += e.ql
            bars[n] = sorted(rows)
        out.append(bars)
    return out


def midi_bars(path: Path, nparts: int):
    import mido
    mid = mido.MidiFile(path)
    tpb = mid.ticks_per_beat
    out = []
    for track in mid.tracks[1:nparts + 1]:
        ons, t = [], 0
        for msg in track:
            t += msg.time
            if msg.type == "note_on" and msg.velocity:
                ons.append((t, msg.note))
        start = ons[0][0] if ons else 0
        bars = defaultdict(list)
        for tick, note in ons:
            beat = Fraction(tick - start, tpb) - PICKUP
            if beat < 0:
                bars[0].append((beat + PICKUP, note))
            else:
                n = int(beat // 4) + 1
                bars[n].append((beat - 4 * (n - 1), note))
        out.append({n: sorted(v) for n, v in bars.items()})
    return out


def classify(a, b) -> str | None:
    """None when equal; 'octave+N' / 'octave-N' for a uniform octave shift; else 'diff'."""
    if a == b:
        return None
    if len(a) == len(b) and a and all(x[0] == y[0] for x, y in zip(a, b)):
        shifts = {y[1] - x[1] for x, y in zip(a, b)}
        if len(shifts) == 1 and (s := shifts.pop()) % 12 == 0:
            return f"octave{s // 12:+d}"
    return "diff"


def _name(p: int) -> str:
    return ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"][p % 12] + str(p // 12 - 1)


def fmt(rows) -> str:
    return " ".join(f"{_name(p)}@{float(t):g}" for t, p in rows)


def load_explained(path: Path | None) -> set[tuple[int, int]]:
    """Lines (or markdown table rows) starting with 'part bar' numbers, e.g.
    '| 0 | 3 | ...' or '0 3 ...'.  Ranges like 1-9 are allowed for the bar."""
    out = set()
    if not path:
        return out
    for line in path.read_text().splitlines():
        m = re.match(r"^\|?\s*(\d+)\s*\|?\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*\|", line)
        if m:
            part, a = int(m.group(1)), int(m.group(2))
            b = int(m.group(3) or a)
            out.update((part, n) for n in range(a, b + 1))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("score", type=Path)
    ap.add_argument("--midi", type=Path,
                    default=Path(__file__).resolve().parents[2]
                    / "local/brandenburg3/brandenburg3-kunstderfuge.mid")
    ap.add_argument("--explained", type=Path, help="file listing explained 'part | bar' rows")
    ap.add_argument("--part", type=int, help="only this part (0-based)")
    ap.add_argument("--verbose", "-v", action="store_true", help="print the notes of differing bars")
    args = ap.parse_args(argv)

    parts = read_musicxml(args.score)
    ok = True
    print(f"{len(parts)} parts, bars per part: {sorted({len(p.bars) for p in parts})}")
    for i, part in enumerate(parts):
        bad = [n for n, b in enumerate(part.bars[:LAST_BAR + 1]) if bar_length(b) != expected_length(n)]
        if bad:
            ok = False
            print(f"part {i} ({part.name}): wrong bar length in {bad}")
        if len(part.bars) != LAST_BAR + 1:
            print(f"part {i} ({part.name}): {len(part.bars)} bars (expected {LAST_BAR + 1})")
    if ok:
        print("bar lengths: all correct")

    if not args.midi.exists():
        print(f"(no {args.midi}; skipping the locator comparison)")
        return 0 if ok else 1
    explained = load_explained(args.explained)
    sb = score_bars(parts)
    mb = midi_bars(args.midi, len(parts))
    unexplained = explained_hits = 0
    for i in range(len(parts)):
        if args.part is not None and i != args.part:
            continue
        for n in range(LAST_BAR + 1):
            kind = classify(sb[i].get(n, []), mb[i].get(n, []))
            if not kind:
                continue
            tag = "explained" if (i, n) in explained else "DIFF"
            if tag == "explained":
                explained_hits += 1
            else:
                unexplained += 1
            print(f"{tag:9} part {i} bar {n:3} {kind}")
            if args.verbose:
                print(f"    score: {fmt(sb[i].get(n, []))}")
                print(f"    midi:  {fmt(mb[i].get(n, []))}")
    print(f"locator differences: {unexplained} unexplained, {explained_hits} explained")
    return 0 if ok and not unexplained else 1


if __name__ == "__main__":
    sys.exit(main())
