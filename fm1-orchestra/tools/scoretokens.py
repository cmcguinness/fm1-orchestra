"""A compact, editable text form of a (simple) MusicXML score, one bar per line.

Used to correct optical music recognition (OMR) output by hand: each bar of
each part is a list of tokens, a correction replaces a bar's tokens, and the
result is written back out as MusicXML with music21.

Token grammar (whitespace separated, in time order):
  note    C#4:8      pitch (step, optional # ## b bb n, octave) ':' duration
  rest    r:4        a rest; r:1 with no other events is a whole-bar rest
  chord   [G3,D4]:4  several pitches sounding together
  duration  1 2 4 8 16 32 (whole ... 32nd), one or two '.' for dots
  suffixes on a note/rest, in any order:
            ~ tie to the next note      ' staccato     ! staccatissimo
            ( slur starts                ) slur ends   ^ fermata
            > accent                     t trill
  dynamic @f @p @pp @mf ...   applies at the next note or rest

Only single-voice bars are supported, which is all this project needs.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

TYPE_QL = {"whole": Fraction(4), "half": Fraction(2), "quarter": Fraction(1),
           "eighth": Fraction(1, 2), "16th": Fraction(1, 4), "32nd": Fraction(1, 8)}
DEN_TYPE = {1: "whole", 2: "half", 4: "quarter", 8: "eighth", 16: "16th", 32: "32nd"}
TYPE_DEN = {v: k for k, v in DEN_TYPE.items()}
ALTER = {"": None, "n": 0, "#": 1, "##": 2, "b": -1, "bb": -2}
ALTER_TXT = {None: "", 0: "", 1: "#", 2: "##", -1: "b", -2: "bb"}
SUFFIXES = "~'!()^>t"
DYNAMICS = ("ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "sf", "sfz", "fp")

_PITCH = re.compile(r"^([A-G])(##|#|bb|b|n)?(-?\d)$")
_EVENT = re.compile(r"^(r|\[[^\]]+\]|[A-G](?:##|#|bb|b|n)?-?\d):(\d+)(\.{0,2})([" + re.escape(SUFFIXES) + r"]*)$")


@dataclass
class Event:
    pitches: list[tuple[str, int, int]]      # (step, alter, octave); empty = rest
    den: int                                 # 4 = quarter, 8 = eighth ...
    dots: int = 0
    marks: str = ""                          # suffix characters
    dynamic: str | None = None               # dynamic that starts on this event
    whole_bar: bool = False                  # whole-bar rest

    @property
    def ql(self) -> Fraction:
        base = Fraction(4, self.den)
        return base * (2 - Fraction(1, 2 ** self.dots))

    @property
    def is_rest(self) -> bool:
        return not self.pitches

    def midi(self) -> list[int]:
        steps = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        return [12 * (o + 1) + steps[s] + a for s, a, o in self.pitches]


def pitch_text(step: str, alter: int, octave: int) -> str:
    return f"{step}{ALTER_TXT[alter]}{octave}"


def event_text(e: Event) -> str:
    if e.whole_bar:
        head, dur = "r", "1"
    else:
        head = "r" if e.is_rest else (pitch_text(*e.pitches[0]) if len(e.pitches) == 1
                                      else "[" + ",".join(pitch_text(*p) for p in e.pitches) + "]")
        dur = f"{e.den}{'.' * e.dots}"
    marks = "".join(c for c in SUFFIXES if c in e.marks)
    out = f"{head}:{dur}{marks}"
    return (f"@{e.dynamic} " + out) if e.dynamic else out


def bar_text(events: list[Event]) -> str:
    return " ".join(event_text(e) for e in events)


def parse_pitch(txt: str) -> tuple[str, int, int]:
    m = _PITCH.match(txt)
    if not m:
        raise ValueError(f"bad pitch {txt!r}")
    return m.group(1), ALTER[m.group(2) or ""] or 0, int(m.group(3))


def parse_bar(txt: str) -> list[Event]:
    """Parse a bar of tokens.  Pitches are sounding pitches (F#4), not
    relative to the key signature."""
    events: list[Event] = []
    pending_dyn = None
    for tok in txt.split():
        if tok.startswith("@"):
            if tok[1:] not in DYNAMICS:
                raise ValueError(f"unknown dynamic {tok!r}")
            pending_dyn = tok[1:]
            continue
        m = _EVENT.match(tok)
        if not m:
            raise ValueError(f"bad token {tok!r} in {txt!r}")
        head, den, dots, marks = m.groups()
        if int(den) not in DEN_TYPE:
            raise ValueError(f"bad duration in {tok!r}")
        if head == "r":
            pitches = []
        elif head.startswith("["):
            pitches = [parse_pitch(p) for p in head[1:-1].split(",")]
        else:
            pitches = [parse_pitch(head)]
        events.append(Event(pitches, int(den), len(dots), marks, pending_dyn))
        pending_dyn = None
    if pending_dyn:
        raise ValueError(f"dynamic with no following note in {txt!r}")
    if len(events) == 1 and events[0].is_rest and events[0].den == 1 and not events[0].dots:
        events[0].whole_bar = True
    return events


def bar_length(events: list[Event], whole_bar: Fraction = Fraction(4)) -> Fraction:
    if len(events) == 1 and events[0].whole_bar:
        return whole_bar
    return sum((e.ql for e in events), Fraction(0))


# ---------------------------------------------------------------- reading OMR

@dataclass
class Part:
    pid: str
    name: str
    clef: tuple[str, int]                    # ('G', 2), ('C', 3), ('F', 4)
    bars: list[list[Event]] = field(default_factory=list)
    notes: list[list[str]] = field(default_factory=list)   # per bar: reader warnings


def _load_xml(path: Path) -> ET.Element:
    if path.suffix == ".mxl":
        with zipfile.ZipFile(path) as z:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            root_file = container.find(".//rootfile").get("full-path")
            return ET.fromstring(z.read(root_file))
    return ET.parse(path).getroot()


def read_musicxml(path: Path) -> list[Part]:
    """Read a single-voice-per-part MusicXML score (as Audiveris writes it)
    into token form.  Durations come from <type>/<dot> (what is printed);
    a whole-bar rest is a rest marked measure="yes" or a lone whole rest."""
    root = _load_xml(Path(path))
    names = {sp.get("id"): (sp.findtext("part-name") or sp.get("id"))
             for sp in root.iter("score-part")}
    parts = []
    for p in root.iter("part"):
        part = Part(p.get("id"), names.get(p.get("id"), p.get("id")), ("G", 2))
        for meas in p.iter("measure"):
            events: list[Event] = []
            warnings: list[str] = []
            pending_dyn = None
            for el in meas:
                if el.tag == "attributes":
                    clef = el.find("clef")
                    if clef is not None and not part.bars:
                        part.clef = (clef.findtext("sign"), int(clef.findtext("line") or 0))
                elif el.tag == "direction":
                    for dyn in el.iter("dynamics"):
                        for d in dyn:
                            if d.tag in DYNAMICS:
                                pending_dyn = d.tag
                elif el.tag == "backup":
                    warnings.append("backup (second voice) ignored")
                    break
                elif el.tag == "note":
                    if el.find("grace") is not None:
                        warnings.append("grace note ignored")
                        continue
                    pitch = el.find("pitch")
                    rest = el.find("rest")
                    if el.findtext("voice", "1") != "1":
                        warnings.append("voice > 1 ignored")
                        continue
                    typ = el.findtext("type")
                    dots = len(el.findall("dot"))
                    whole_bar = rest is not None and (rest.get("measure") == "yes" or typ is None)
                    den = TYPE_DEN.get(typ, 1)
                    if el.find("time-modification") is not None:
                        warnings.append("tuplet")
                    marks = ""
                    for t in el.iter("tied"):
                        if t.get("type") == "start":
                            marks += "~"
                    for s in el.iter("slur"):
                        marks += "(" if s.get("type") == "start" else ")" if s.get("type") == "stop" else ""
                    for tag, ch in (("staccato", "'"), ("staccatissimo", "!"), ("fermata", "^"),
                                    ("accent", ">"), ("trill-mark", "t")):
                        if el.find(f".//{tag}") is not None:
                            marks += ch
                    pt = None
                    if pitch is not None:
                        pt = (pitch.findtext("step"), int(float(pitch.findtext("alter") or 0)),
                              int(pitch.findtext("octave")))
                    if el.find("chord") is not None and events and pt:
                        events[-1].pitches.append(pt)
                        continue
                    events.append(Event([pt] if pt else [], den, dots, marks, pending_dyn,
                                        whole_bar=whole_bar))
                    pending_dyn = None
            part.bars.append(events)
            part.notes.append(warnings)
        parts.append(part)
    return parts


# ---------------------------------------------------------------- writing

def _beam_eighths_by_half(measure) -> None:
    """Sixteenths are beamed by the quarter; four plain eighths filling a half
    bar get one beam, as engravers (and this edition) print them."""
    for start in (0.0, 2.0):
        window = [n for n in measure.notesAndRests if start <= n.offset < start + 2]
        if (len(window) == 4 and all(n.isNote or n.isChord for n in window)
                and all(n.duration.type == "eighth" and not n.duration.dots for n in window)):
            for n, kind in zip(window, ("start", "continue", "continue", "stop")):
                n.beams.beamsList = []
                n.beams.append(kind)


def write_musicxml(parts: list[Part], out: Path, *, title: str, composer: str,
                   fifths: int, time_sig: str, pickup: Fraction,
                   credits: list[str] = (), rights: str = "") -> None:
    """Build a music21 score from token bars and write uncompressed MusicXML.
    Bar 0 is a pickup of length `pickup` (MusicXML measure number 0)."""
    import music21 as m21

    score = m21.stream.Score()
    score.metadata = m21.metadata.Metadata()
    score.metadata.title = title
    score.metadata.composer = composer
    if rights:
        score.metadata.copyright = rights
    for c in credits:
        score.insert(0, m21.text.TextBox(c))
    clefs = {("G", 2): m21.clef.TrebleClef, ("C", 3): m21.clef.AltoClef,
             ("F", 4): m21.clef.BassClef}
    for part in parts:
        p = m21.stream.Part(id=part.pid)
        p.partName = part.name
        inst = m21.instrument.Instrument()
        inst.partName = part.name
        inst.instrumentName = part.name
        inst.partId = part.pid                # stable ids keep rebuilt files diffable
        inst.instrumentId = f"{part.pid}-I1"
        p.insert(0, inst)
        slur_open: list = []
        tie_from = None
        for n, events in enumerate(part.bars):
            m = m21.stream.Measure(number=n)
            if n == 0:
                m.insert(0, clefs[part.clef]())
                m.insert(0, m21.key.KeySignature(fifths))
                ts = m21.meter.TimeSignature(time_sig)
                ts.beamSequence.partition(int(ts.barDuration.quarterLength))   # beam by the quarter
                m.insert(0, ts)
                m.paddingLeft = float(ts.barDuration.quarterLength - pickup)
            at = Fraction(0)
            for e in events:
                if e.dynamic:
                    m.insert(float(at), m21.dynamics.Dynamic(e.dynamic))
                if e.whole_bar:
                    r = m21.note.Rest()
                    r.fullMeasure = True
                    r.quarterLength = 4.0
                    m.insert(0, r)
                    at += 4
                    continue
                d = m21.duration.Duration(type=DEN_TYPE[e.den], dots=e.dots)
                if e.is_rest:
                    el = m21.note.Rest(duration=d)
                else:
                    ps = []
                    for step, alter, octave in e.pitches:
                        pt = m21.pitch.Pitch(step=step, octave=octave)
                        if alter:
                            pt.accidental = m21.pitch.Accidental(alter)
                        ps.append(pt)
                    el = m21.note.Note(ps[0], duration=d) if len(ps) == 1 else m21.chord.Chord(ps, duration=d)
                    if tie_from is not None:
                        el.tie = m21.tie.Tie("stop")
                    if "~" in e.marks:
                        el.tie = m21.tie.Tie("continue" if tie_from is not None else "start")
                    tie_from = el if "~" in e.marks else None
                    if "(" in e.marks:
                        slur_open.append(el)
                    if ")" in e.marks and slur_open:
                        p.insert(0, m21.spanner.Slur(slur_open.pop(), el))
                for ch, art in (("'", m21.articulations.Staccato), ("!", m21.articulations.Staccatissimo),
                                (">", m21.articulations.Accent)):
                    if ch in e.marks:
                        el.articulations.append(art())
                if "^" in e.marks:
                    el.expressions.append(m21.expressions.Fermata())
                if "t" in e.marks:
                    el.expressions.append(m21.expressions.Trill())
                m.insert(float(at), el)
                at += e.ql
            p.append(m)
        last = p.getElementsByClass(m21.stream.Measure)[-1]
        last.rightBarline = m21.bar.Barline("final")
        score.insert(0, p)
    for p in score.parts:
        for m in p.getElementsByClass(m21.stream.Measure):
            m.makeBeams(inPlace=True)
            _beam_eighths_by_half(m)
    score.makeNotation(inPlace=True)
    score.write("musicxml", fp=str(out), makeNotation=False)
    if pickup:
        # music21 marks every measure explicit; the pickup bar is an implicit (uncounted) one
        text = Path(out).read_text()
        Path(out).write_text(text.replace('<measure implicit="no" number="0">',
                                          '<measure implicit="yes" number="0">'))
