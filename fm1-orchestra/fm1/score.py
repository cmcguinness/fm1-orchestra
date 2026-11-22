"""Turning a MusicXML score into a performance MIDI file.

The score is read with music21. Each staff becomes a named track, and
"performance" markings become MIDI:
  - dynamics (ppp-ff) set velocity; sf lifts only the notes it sits on,
    relative to the surrounding level (sf inside pp is an accent, not a forte)
  - hairpins ramp velocity to the next marked dynamic (or two steps)
  - fermatas lengthen their notes
  - pizz. ... arco shortens string notes to a pluck
  - pedal marks become sustain (CC 64) on both staves of that instrument
Notes are taken at sounding pitch (MuseScore's MusicXML already has octave
lines applied). The tempo is a single metronome mark given by the caller,
since many scores (like "Andantino") don't state one.
"""

from bisect import bisect_right
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import mido

VELOCITY = {"ppp": 20, "pp": 32, "p": 45, "mp": 58, "mf": 72, "f": 88, "ff": 104, "fff": 118}
LEVELS = list(VELOCITY.values())
SF_LIFT = 28                # sf = the surrounding level + this (an accent, not forte)
PIZZ_QUARTERS = 0.25        # a pizzicato note lasts a sixteenth at most
FERMATA = 1.75              # fermata lengthening factor
TICKS = 480


@dataclass
class Staff:
    name: str
    instrument: str
    notes: list[tuple[float, float, int, int]] = field(default_factory=list)  # (on, dur, pitch, vel) in quarters
    pedal: list[tuple[float, float]] = field(default_factory=list)            # (down, up) in quarters


def _q(x) -> float:
    return float(Fraction(x)) if not isinstance(x, float) else x


def _offset(el, parts) -> float:
    """Offset in quarters from the start; all staves share one timeline, and a
    spanner (a hairpin between piano staves) may sit on another staff's notes."""
    for part in parts:
        try:
            return _q(el.getOffsetInHierarchy(part))
        except Exception:               # music21.sites.SitesException
            continue
    raise ValueError(f"{el} is in no staff")


def _instrument_markings(parts):
    """Dynamics, wedges, pizz spans and pedals per instrument name (staves pooled)."""
    import music21 as m21
    marks: dict[str, dict] = {}
    for part in parts:
        m = marks.setdefault(part.partName, {"dyn": [], "sf": set(), "wedges": [],
                                             "pizz": [], "pedal": []})
        for d in part.recurse().getElementsByClass(m21.dynamics.Dynamic):
            at = _q(d.getOffsetInHierarchy(part))
            if d.value in VELOCITY:
                m["dyn"].append((at, VELOCITY[d.value]))
            elif d.value in ("sf", "sfz", "fz"):
                m["sf"].add(round(at, 4))
        for w in part.recurse().getElementsByClass(m21.dynamics.DynamicWedge):
            spanned = w.getSpannedElements()
            if spanned:
                start = _offset(spanned[0], parts)
                last = spanned[-1]
                end = _offset(last, parts) + _q(last.quarterLength)
                m["wedges"].append((start, end, +1 if isinstance(w, m21.dynamics.Crescendo) else -1))
        texts = sorted((_q(t.getOffsetInHierarchy(part)), t.content.strip().lower())
                       for t in part.recurse().getElementsByClass(m21.expressions.TextExpression))
        pizz_from = None
        for at, txt in texts:
            if txt.startswith("pizz") and pizz_from is None:
                pizz_from = at
            elif txt.startswith("arco") and pizz_from is not None:
                m["pizz"].append((pizz_from, at))
                pizz_from = None
        if pizz_from is not None:
            m["pizz"].append((pizz_from, float("inf")))
        for pm in part.recurse().getElementsByClass("PedalMark"):
            spanned = pm.getSpannedElements()
            if spanned:
                down = _offset(spanned[0], parts)
                last = spanned[-1]
                up = _offset(last, parts) + _q(last.quarterLength)
                m["pedal"].append((down, up))
    for m in marks.values():
        m["dyn"].sort()
    return marks


def _velocity(at: float, m: dict) -> int:
    dyn = m["dyn"]
    i = bisect_right([d[0] for d in dyn], at) - 1
    level = dyn[i][1] if i >= 0 else VELOCITY["mf"]
    if round(at, 4) in m["sf"]:
        return min(127, level + SF_LIFT)
    for start, end, direction in m["wedges"]:
        if start <= at < end:
            base_i = bisect_right([d[0] for d in dyn], start) - 1
            base = dyn[base_i][1] if base_i >= 0 else level
            after = [v for t, v in dyn if end - 0.01 <= t <= end + 1.0]
            if after:
                target = after[0]
            else:
                idx = min(range(len(LEVELS)), key=lambda k: abs(LEVELS[k] - base))
                target = LEVELS[max(0, min(len(LEVELS) - 1, idx + 2 * direction))]
            if round(start, 4) in m["sf"]:
                base = min(127, base + SF_LIFT)   # "sf >": fade from the accent
            frac = (at - start) / (end - start) if end > start else 0
            return round(base + (target - base) * frac)
    return level


def read_score(path: Path) -> list[Staff]:
    import music21 as m21
    score = m21.converter.parse(str(path)).stripTies()
    parts = list(score.parts)
    marks = _instrument_markings(parts)
    counts: dict[str, int] = {}
    for p in parts:
        counts[p.partName] = counts.get(p.partName, 0) + 1
    seen: dict[str, int] = {}
    staves = []
    for part in parts:
        inst = part.partName
        seen[inst] = seen.get(inst, 0) + 1
        name = inst if counts[inst] == 1 else f"{inst} ({'upper' if seen[inst] == 1 else 'lower'})"
        m = marks[inst]
        staff = Staff(name, inst, pedal=list(m["pedal"]))
        for n in part.flatten().notes:
            at = _q(n.getOffsetInHierarchy(part))
            dur = _q(n.quarterLength)
            if any(isinstance(e, m21.expressions.Fermata) for e in n.expressions):
                dur *= FERMATA
            if any(a <= at < b for a, b in m["pizz"]):
                dur = min(dur, PIZZ_QUARTERS)
            vel = _velocity(at, m)
            pitches = [n.pitch] if n.isNote else list(n.pitches)
            for p in pitches:
                staff.notes.append((at, dur, p.midi, vel))
        staves.append(staff)
    return staves


def write_midi(staves: list[Staff], out: Path, bpm: float, title: str = "") -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS)
    conductor = mido.MidiTrack([mido.MetaMessage("track_name", name=title or out.stem),
                                mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm)),
                                mido.MetaMessage("time_signature", numerator=4, denominator=4)])
    midi.tracks.append(conductor)
    for staff in staves:
        events: list[tuple[int, int, mido.Message]] = []   # (tick, order, msg)
        for at, dur, pitch, vel in staff.notes:
            on = round(at * TICKS)
            off = max(on + 1, round((at + dur) * TICKS) - 2)    # tiny gap: repeated notes re-strike
            events.append((on, 1, mido.Message("note_on", note=pitch, velocity=max(1, vel))))
            events.append((off, 0, mido.Message("note_off", note=pitch)))
        for down, up in staff.pedal:
            events.append((round(down * TICKS), 2, mido.Message("control_change", control=64, value=127)))
            events.append((round(up * TICKS), 0, mido.Message("control_change", control=64, value=0)))
        events.sort(key=lambda e: (e[0], e[1]))
        track = mido.MidiTrack([mido.MetaMessage("track_name", name=staff.name)])
        last = 0
        for tick, _, msg in events:
            track.append(msg.copy(time=tick - last))
            last = tick
        midi.tracks.append(track)
    midi.save(out)
