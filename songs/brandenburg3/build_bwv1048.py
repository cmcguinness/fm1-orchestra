"""Build score/bwv1048-1.musicxml from the Audiveris OMR plus hand corrections.

    python songs/brandenburg3/build_bwv1048.py [--omr songs/brandenburg3/sources/brandenburg3-omr.mxl]

Reads score/bwv1048-1-fixes.txt, applies each correction to the OMR bars,
writes the corrected MusicXML (bars 0-136; the Adagio bar 137 is dropped) and
regenerates the generated sections of score/bwv1048-1-corrections.md.

Fixes file, one directive per line ('#' starts a comment line):
  fix PART BAR | TOKENS | how it was verified
  edition PART BAR[-BAR] | what the edition has and the locator MIDI differs in
  unsure PART BAR | what is uncertain
PART is the 0-based part index, BAR the bar number (0 = pickup).  TOKENS is
the whole corrected bar in the notation of fm1-orchestra/tools/scoretokens.py.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent                     # songs/brandenburg3/
sys.path.insert(0, str(HERE.parent.parent / "fm1-orchestra" / "tools"))
from scoretokens import bar_length, bar_text, parse_bar, read_musicxml, write_musicxml  # noqa: E402

LAST_BAR = 136
NAMES = ["Violino I", "Violino II", "Violino III", "Viola I", "Viola II", "Viola III",
         "Violoncello I", "Violoncello II", "Violoncello III", "Continuo"]
# first bar on each page of the edition (pages 1-45 hold movement 1)
PAGE_STARTS = [0, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 41, 44, 47, 50, 53, 56, 59, 62,
               65, 68, 71, 74, 77, 80, 83, 86, 89, 92, 95, 98, 101, 104, 107, 110, 113, 116,
               119, 122, 125, 128, 131, 134]
CREDIT = ("J. S. Bach, Brandenburg Concerto No. 3 in G, BWV 1048, I. Score: Chris Sawer, "
          "Mutopia Project (2004), CC BY 3.0, via IMSLP #57477. Optical recognition: Audiveris 5.11; "
          "corrected by hand against the printed score.")
RIGHTS = "Chris Sawer / Mutopia Project (2004), CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/)"


def page_of(bar: int) -> int:
    return max(i for i, s in enumerate(PAGE_STARTS) if s <= bar) + 1


def expected_length(n: int) -> Fraction:
    return Fraction(1, 2) if n == 0 else Fraction(7, 2) if n == LAST_BAR else Fraction(4)


@dataclass
class Directive:
    kind: str
    part: int
    bars: tuple[int, int]
    tokens: str
    note: str
    line: int


def read_fixes(path: Path) -> list[Directive]:
    out = []
    for no, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f.strip() for f in line.split("|")]
        head = fields[0].split()
        kind, part, bars = head[0], int(head[1]), head[2]
        a, _, b = bars.partition("-")
        rng = (int(a), int(b or a))
        if kind == "fix":
            if len(fields) != 3:
                raise ValueError(f"{path}:{no}: fix needs 'fix P B | tokens | note'")
            out.append(Directive(kind, part, rng, fields[1], fields[2], no))
        elif kind in ("edition", "unsure"):
            out.append(Directive(kind, part, rng, "", " | ".join(fields[1:]), no))
        else:
            raise ValueError(f"{path}:{no}: unknown directive {kind!r}")
    return out


def apply_fixes(parts, fixes):
    """Apply 'fix' directives in place; returns [(directive, omr_text)]."""
    applied = []
    seen = set()
    for d in fixes:
        if d.kind != "fix":
            continue
        key = (d.part, d.bars[0])
        if key in seen:
            raise ValueError(f"line {d.line}: part {d.part} bar {d.bars[0]} fixed twice")
        seen.add(key)
        events = parse_bar(d.tokens)
        n = d.bars[0]
        if bar_length(events) != expected_length(n):
            raise ValueError(f"line {d.line}: part {d.part} bar {n} lasts {bar_length(events)}")
        old = bar_text(parts[d.part].bars[n])
        if old == bar_text(events):
            raise ValueError(f"line {d.line}: part {d.part} bar {n} fix changes nothing")
        parts[d.part].bars[n] = events
        applied.append((d, old))
    return applied


def load(omr: Path, fixes_path: Path):
    parts = read_musicxml(omr)
    for p, name in zip(parts, NAMES):
        p.name = name
        del p.bars[LAST_BAR + 1:]
    fixes = read_fixes(fixes_path)
    applied = apply_fixes(parts, fixes)
    return parts, fixes, applied


def _md(s: str) -> str:
    return s.replace("|", "\\|")


def corrections_tables(fixes, applied) -> str:
    lines = ["## Corrections", "",
             "Each row replaces the whole bar. Pitches are sounding pitches (F#4 = F sharp above "
             "middle C); `:8` = eighth, `:16` = sixteenth, `.` = dotted, `~` tie, `(` `)` slur, "
             "`'` staccato, `!` staccatissimo, `t` trill, `^` fermata, `@f` dynamic. Page = page "
             "of the PDF; \"checked at 4x\" means the passage was re-read from a 4x enlargement.", "",
             "| Part | Bar | Page | OMR reading | Corrected reading | Verified by |",
             "|---|---|---|---|---|---|"]
    for d, old in sorted(applied, key=lambda x: (x[0].bars[0], x[0].part)):
        lines.append(f"| {d.part} {NAMES[d.part]} | {d.bars[0]} | {page_of(d.bars[0])} | "
                     f"`{_md(old)}` | `{_md(d.tokens)}` | {_md(d.note)} |")
    eds = [d for d in fixes if d.kind == "edition"]
    lines += ["", "## Edition differs from the locator MIDI (edition kept)", "",
              "| Part | Bars | Page | Difference |", "|---|---|---|---|"]
    for d in sorted(eds, key=lambda d: (d.bars[0], d.part)):
        b = f"{d.bars[0]}" if d.bars[0] == d.bars[1] else f"{d.bars[0]}-{d.bars[1]}"
        pg = page_of(d.bars[0])
        pg2 = page_of(d.bars[1])
        lines.append(f"| {d.part} | {b} | {pg if pg == pg2 else f'{pg}-{pg2}'} | "
                     f"{NAMES[d.part]}: {_md(d.note)} |")
    uns = [d for d in fixes if d.kind == "unsure"]
    lines += ["", "## Uncertain readings", ""]
    lines += [f"- {NAMES[d.part]} (part {d.part}), bar {d.bars[0]}, page {page_of(d.bars[0])}: {d.note}"
              for d in sorted(uns, key=lambda d: (d.bars[0], d.part))] or ["- None. Every correction above, and every edition reading in the previous "
                    "table, was confirmed on the page (enlarged where the reading was not obvious)."]
    per_part = Counter(d.part for d, _ in applied)
    lines += ["", "## Summary", "",
              f"- Corrected part-bars: {len(applied)} "
              f"(of {10 * (LAST_BAR + 1)} part-bars, bars 0-{LAST_BAR}), in "
              f"{len({d.bars[0] for d, _ in applied})} different bars.",
              "- Per part: " + ", ".join(f"{NAMES[i]} {per_part.get(i, 0)}" for i in range(10)) + ".",
              f"- Edition-difference entries (edition kept): {len(eds)} "
              f"covering {sum(d.bars[1] - d.bars[0] + 1 for d in eds)} part-bars.",
              f"- Uncertain readings: {len(uns)}."]
    return "\n".join(lines) + "\n"


MARK = "<!-- generated by build_bwv1048.py: everything below is rewritten -->"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--omr", type=Path, default=HERE / "sources/brandenburg3-omr.mxl")
    ap.add_argument("--fixes", type=Path, default=HERE / "score/bwv1048-1-fixes.txt")
    ap.add_argument("--out", type=Path, default=HERE / "score/bwv1048-1.musicxml")
    ap.add_argument("--log", type=Path, default=HERE / "score/bwv1048-1-corrections.md")
    args = ap.parse_args(argv)

    parts, fixes, applied = load(args.omr, args.fixes)
    bad = [(i, n) for i, p in enumerate(parts) for n, b in enumerate(p.bars)
           if bar_length(b) != expected_length(n)]
    if bad:
        print(f"warning: {len(bad)} bars still have the wrong length: {bad}")
    write_musicxml(parts, args.out, title="Brandenburg Concerto No. 3, I. [Allegro]",
                   composer="J. S. Bach (BWV 1048)", fifths=1, time_sig="cut",
                   pickup=Fraction(1, 2), credits=[CREDIT], rights=RIGHTS)
    head = args.log.read_text().split(MARK)[0] if args.log.exists() else "# Corrections\n\n"
    args.log.write_text(head.rstrip() + "\n\n" + MARK + "\n\n" + corrections_tables(fixes, applied))
    print(f"wrote {args.out} ({len(applied)} corrections) and {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
