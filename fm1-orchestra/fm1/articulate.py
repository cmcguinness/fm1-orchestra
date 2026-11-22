"""Performance shaping that leaves timing of note starts alone.

- accents: velocity follows the metre. Downbeats lean in, other main beats a
  little less, offbeat eighths stay level, faster notes are lighter.
- articulation: notes are released early (detached playing) instead of being
  held for their full written length.
- vary: a small, repeatable variation in velocity so repeats aren't identical.

Metric position comes from the MIDI file's own tempo map and first time
signature, so accents stay in step whatever the playback speed.
"""

import random
from bisect import bisect_right

import mido

MIN_NOTE = 0.04             # seconds: articulation never shortens a note below this
EPS = 0.02                  # beats: tolerance when deciding a note sits on a beat


class BeatClock:
    """Maps score seconds to beats (quarter notes) through a MIDI tempo map."""

    def __init__(self, midi: mido.MidiFile):
        tpb = midi.ticks_per_beat
        changes: dict[int, int] = {0: 500000}
        sig = (4, 4)
        found_sig = False
        for track in midi.tracks:
            tick = 0
            for msg in track:
                tick += msg.time
                if msg.type == "set_tempo":
                    changes[tick] = msg.tempo
                elif msg.type == "time_signature" and not found_sig:
                    sig, found_sig = (msg.numerator, msg.denominator), True
        self.numerator, self.denominator = sig
        # Segment starts in seconds and beats, with each segment's tempo.
        self.seconds, self.beats, self.tempos = [], [], []
        last_tick, sec = 0, 0.0
        tempo = 500000
        for tick in sorted(changes):
            sec += mido.tick2second(tick - last_tick, tpb, tempo)
            tempo = changes[tick]
            self.seconds.append(sec)
            self.beats.append(tick / tpb)
            self.tempos.append(tempo)
            last_tick = tick

    def beat(self, seconds: float) -> float:
        i = max(0, bisect_right(self.seconds, seconds) - 1)
        return self.beats[i] + (seconds - self.seconds[i]) * 1e6 / self.tempos[i]

    def weight(self, seconds: float) -> float:
        """Metric weight: 1 downbeat, 0.5 other beats, 0 half-beats, -0.5 faster."""
        unit = 4 / self.denominator                  # beat length in quarters
        bar = self.numerator * unit
        pos = self.beat(seconds) % bar

        def on(grid: float) -> bool:
            r = pos % grid
            return r < EPS or grid - r < EPS
        if on(bar):
            return 1.0
        if on(unit):
            return 0.5
        if on(unit / 2):
            return 0.0
        return -0.5


def accent(events, depth: dict[int, float], clock: BeatClock, to_score,
           vary: dict[int, float] | None = None, seed: int = 1):
    """Scale note-on velocities by metric weight (and optional variation).

    depth/vary map channel -> amount; to_score maps an event time to score
    seconds (the MIDI file's own clock).
    """
    rng = random.Random(seed)
    vary = vary or {}
    out = []
    for at, msg in events:
        ch = msg.channel
        if msg.type == "note_on" and msg.velocity and (depth.get(ch) or vary.get(ch)):
            factor = 1 + depth.get(ch, 0) * clock.weight(to_score(at))
            if vary.get(ch):
                factor *= 1 + rng.uniform(-vary[ch], vary[ch])
            msg = msg.copy(velocity=max(1, min(127, round(msg.velocity * factor))))
        out.append((at, msg))
    return out


def articulate(events, length: dict[int, float]):
    """Release notes early: each note lasts `length` of its written duration.

    length maps channel -> fraction (1 = as written). Notes are paired first-in
    first-out per channel and pitch, a release never moves before its note's
    start plus MIN_NOTE, and the result is re-sorted (releases before starts
    at the same instant, so repeated notes re-strike).
    """
    if not any(v < 1 for v in length.values()):
        return events
    starts: dict[tuple[int, int], list[float]] = {}
    out = []
    for at, msg in events:
        key = (msg.channel, msg.note)
        is_on = msg.type == "note_on" and msg.velocity
        frac = length.get(msg.channel, 1.0)
        if is_on:
            starts.setdefault(key, []).append(at)
        elif starts.get(key) and frac < 1:
            began = starts[key].pop(0)
            # Shorten only: MIN_NOTE keeps very short notes audible, but a note
            # is never held past its written end (it could swallow a re-strike).
            at = min(at, began + max(MIN_NOTE, (at - began) * frac))
        elif starts.get(key):
            starts[key].pop(0)
        out.append((at, msg))
    out.sort(key=lambda e: (e[0], 1 if e[1].type == "note_on" and e[1].velocity else 0))
    return out
