"""Making a sequenced performance breathe: phrase rubato, breaths, jitter.

Applied to scheduled events (absolute seconds), before the --start/--end
window is cut, so a phrase shapes the same way wherever playback starts.

Rubato: within each phrase the local pace follows 1 + depth*cos(2*pi*u)
(u = 0..1 across the phrase): broader at the edges, moving in the middle.
That integrates to a closed-form, monotonic time map that keeps each phrase's
length, so the piece doesn't drift:

    t' = a + (b - a) * (u + depth / (2*pi) * sin(2*pi*u))

Phrases are cut where a chosen track (usually the melody) rests.
"""

import math
import random
from bisect import bisect_right
from dataclasses import dataclass

import mido


@dataclass
class Humanize:
    rubato: float = 0.12        # 0..0.5: depth of the phrase arch
    breath: float = 0.0         # seconds added at each phrase boundary
    jitter_ms: float = 0.0      # +/- spread of note starts
    velocity: float = 0.0       # +/- fraction of velocity variation
    phrase_track: str | None = None   # track name/number whose rests mark phrases
    phrase_gap: float = 1.5     # a rest this long (seconds) ends a phrase
    seed: int = 1               # same seed, same performance

    def validate(self) -> None:
        if not 0 <= self.rubato <= 0.5:
            raise ValueError("humanize rubato must be 0-0.5")
        if not 0 <= self.breath <= 2:
            raise ValueError("humanize breath must be 0-2 seconds")
        if not 0 <= self.jitter_ms <= 50:
            raise ValueError("humanize jitter_ms must be 0-50")
        if not 0 <= self.velocity <= 0.5:
            raise ValueError("humanize velocity must be 0-0.5")


def phrase_bounds(onsets: list[float], gap: float, end: float) -> list[float]:
    """Phrase boundaries [0, ..., end] at rests longer than `gap`.

    A boundary sits at the start of the note after the rest, so the breath
    and the broadening fall before the new phrase begins.
    """
    onsets = sorted(onsets)
    bounds = [0.0]
    for prev, nxt in zip(onsets, onsets[1:]):
        if nxt - prev > gap and nxt > bounds[-1]:
            bounds.append(nxt)
    if end > bounds[-1]:
        bounds.append(end)
    return bounds


def warp_time(t: float, bounds: list[float], depth: float, breath: float) -> float:
    """Map score time to performed time (monotonic for depth < 1)."""
    i = max(0, min(bisect_right(bounds, t) - 1, len(bounds) - 2))
    a, b = bounds[i], bounds[i + 1]
    shift = breath * i                    # one breath per boundary passed
    if b <= a or t >= b:                  # past the last boundary: continuous with u = 1
        return t + shift
    u = (t - a) / (b - a)
    return a + (b - a) * (u + depth / (2 * math.pi) * math.sin(2 * math.pi * u)) + shift


def apply(events: list[tuple[float, mido.Message]], h: Humanize,
          phrase_onsets: list[float]) -> list[tuple[float, mido.Message]]:
    """Humanized copy of time-sorted (seconds, message) events."""
    if not events:
        return events
    end = events[-1][0]
    bounds = (phrase_bounds(phrase_onsets, h.phrase_gap, end) if phrase_onsets
              else [0.0, end])
    rng = random.Random(h.seed)
    # sounding note -> (start offset, performed start) per strike
    pending: dict[tuple[int, int], list[tuple[float, float]]] = {}
    out = []
    for at, msg in events:
        t = warp_time(at, bounds, h.rubato, h.breath)
        is_on = msg.type == "note_on" and msg.velocity > 0
        key = (msg.channel, msg.note)
        if is_on:
            offset = rng.uniform(-h.jitter_ms, h.jitter_ms) / 1000 if h.jitter_ms else 0.0
            t = max(0.0, t + offset)
            pending.setdefault(key, []).append((offset, t))
            if h.velocity:
                v = msg.velocity * (1 + rng.uniform(-h.velocity, h.velocity))
                msg = msg.copy(velocity=max(1, min(127, round(v))))
        elif pending.get(key):
            # Release moves with its note, and always lands after that note's
            # start, so jitter can't reorder a short note into a stuck one.
            offset, started = pending[key].pop(0)
            t = max(started + 0.001, t + offset)
        out.append((t, msg))
    out.sort(key=lambda e: (e[0], 0 if not (e[1].type == "note_on" and e[1].velocity) else 1))
    return out
