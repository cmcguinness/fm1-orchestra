"""Play a Standard MIDI File out to the FM-1."""

import time
from collections.abc import Callable

import mido

SUSTAIN = 64

# Only note events reach the FM-1. The file's own program changes would load a
# factory preset over the voice we just sent, and its CCs land on the FM-1's
# effects (on V15, CC 7 "volume" is reverb mix). The sustain pedal is applied
# here in software, per track (see schedule).


def track_summary(midi: mido.MidiFile) -> list[tuple[int, str, int]]:
    """(index, name, note count) for every track."""
    return [(i, t.name.strip(),
             sum(1 for m in t if m.type == "note_on" and m.velocity))
            for i, t in enumerate(midi.tracks)]


def select_tracks(midi: mido.MidiFile, wanted: list[str]) -> list[int]:
    """Resolve track numbers or case-insensitive name substrings to indexes."""
    names = [t.name.strip() for t in midi.tracks]
    chosen: list[int] = []
    for item in wanted:
        if item.isdigit():
            if int(item) >= len(names):
                raise ValueError(f"track {item} doesn't exist (0-{len(names) - 1})")
            hits = [int(item)]
        else:
            hits = [i for i, n in enumerate(names) if item.lower() in n.lower()]
            if not hits:
                raise ValueError(f"no track named like {item!r}; tracks: {names}")
        chosen += [h for h in hits if h not in chosen]
    return chosen


def _restricted(midi: mido.MidiFile, tracks: list[int]) -> mido.MidiFile:
    """A copy holding only the chosen tracks, plus every track's tempo changes.

    Tracks are chosen by index, not channel: arrangers reuse channels across
    tracks (in one Nutcracker file the celesta and cello share channel 1).
    """
    tempo_changes: list[tuple[int, mido.MetaMessage]] = []
    for track in midi.tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if msg.type == "set_tempo":
                tempo_changes.append((tick, msg))
    conductor = mido.MidiTrack()
    last = 0
    for tick, msg in sorted(tempo_changes, key=lambda x: x[0]):
        conductor.append(msg.copy(time=tick - last))
        last = tick
    out = mido.MidiFile(type=1, ticks_per_beat=midi.ticks_per_beat)
    out.tracks = [conductor] + [midi.tracks[i] for i in tracks]
    return out


def _is_note_on(msg: mido.Message) -> bool:
    return msg.type == "note_on" and msg.velocity > 0


def _is_note_off(msg: mido.Message) -> bool:
    return msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0)


def _track_events(midi: mido.MidiFile, index: int,
                  pedal: bool) -> list[tuple[float, mido.Message]]:
    """One track's note events in seconds, with its sustain pedal applied.

    While the track's pedal is down its note-offs are held back until the pedal
    lifts. Doing this per track, not on the synth, means a pedalled piano part
    can't hold notes of an unpedalled melody sharing the same FM-1 voice, and no
    pedal message is ever sent that could be left stuck down.
    """
    events: list[tuple[float, mido.Message]] = []
    now = 0.0
    down = False
    deferred: set[int] = set()
    for msg in _restricted(midi, [index]):
        now += msg.time
        if msg.type == "control_change" and msg.control == SUSTAIN:
            if not pedal:
                continue
            down = msg.value >= 64
            if not down:
                events += [(now, mido.Message("note_off", note=n)) for n in sorted(deferred)]
                deferred.clear()
        elif _is_note_on(msg):
            if msg.note in deferred:              # re-struck while pedalled
                deferred.discard(msg.note)
                events.append((now, mido.Message("note_off", note=msg.note)))
            events.append((now, msg))
        elif _is_note_off(msg):
            if down:
                deferred.add(msg.note)
            else:
                events.append((now, mido.Message("note_off", note=msg.note)))
    events += [(now, mido.Message("note_off", note=n)) for n in sorted(deferred)]
    return events


def schedule(midi: mido.MidiFile, start: float = 0.0, end: float | None = None,
             speed: float = 1.0, tracks: list[int] | None = None,
             pedal: bool = True,
             channels: dict[int, int] | None = None) -> list[tuple[float, mido.Message]]:
    """Return (seconds-from-now, message) pairs for the chosen window.

    Only note_on/note_off come back; pedal is already folded into note timing.
    `channels` maps track index -> output channel (0-15), for playing tracks on
    different FM-1 parts. When given, it replaces `tracks`: only its tracks
    play. Otherwise every event is on channel 0.
    """
    if channels is not None:
        tracks = list(channels)
    elif tracks is None:
        tracks = list(range(len(midi.tracks)))
    events: list[tuple[float, mido.Message]] = []
    for index in tracks:
        ch = (channels or {}).get(index, 0)
        events += [(at, msg.copy(channel=ch))
                   for at, msg in _track_events(midi, index, pedal)]
    # Time order; at the same instant, offs before ons so re-strikes sound.
    events.sort(key=lambda e: (e[0], 0 if _is_note_off(e[1]) else 1))
    return [((at - start) / speed, msg) for at, msg in events
            if at >= start and (end is None or at <= end)]


def release_all(port: mido.ports.BaseOutput, channels: range | list[int] = range(16)) -> None:
    """Send a note-off for every note on the given channels.

    The FM-1 (V15 and V16) ignores All Notes Off (CC 123) and All Sound Off (CC 120);
    only individual note-offs release its voices.
    """
    for ch in channels:
        port.send(mido.Message("control_change", channel=ch, control=SUSTAIN, value=0))
        for note in range(128):
            port.send(mido.Message("note_off", channel=ch, note=note))


def play(port: mido.ports.BaseOutput, events: list[tuple[float, mido.Message]],
         channel: int | None = 0, transpose: int = 0,
         on_progress: Callable[[float], None] | None = None) -> None:
    """Send events timed against a fixed clock (no drift).

    With `channel` set, every note is remapped to it (one FM-1 part plays
    everything). With channel=None each event keeps its own channel, as set by
    schedule(channels=...), so each part plays its own tracks.
    Notes are reference-counted per channel: when two tracks hold the same
    pitch on one part (left hand and pedal on the same D, say) it sounds once
    and is released only when the last track lets go, like a single organ
    pipe. Every note on the channels used is released on exit, including after
    Ctrl-C or SIGTERM.
    """
    used = ({channel} if channel is not None
            else {m.channel for _, m in events} or {0})
    held: dict[tuple[int, int], int] = {}
    t0 = time.perf_counter()
    last_report = -1
    try:
        for at, msg in events:
            delay = t0 + at - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            note = msg.note + transpose
            if not 0 <= note <= 127:
                continue
            ch = msg.channel if channel is None else channel
            key = (ch, note)
            if _is_note_on(msg):
                held[key] = held.get(key, 0) + 1
                if held[key] == 1:
                    port.send(mido.Message("note_on", channel=ch,
                                           note=note, velocity=msg.velocity))
            elif held.get(key):
                held[key] -= 1
                if held[key] == 0:
                    del held[key]
                    port.send(mido.Message("note_off", channel=ch, note=note))
            if on_progress and int(at) != last_report:
                last_report = int(at)
                on_progress(at)
    finally:
        release_all(port, sorted(used))
