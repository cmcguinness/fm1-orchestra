"""The song bank: every sound the song modules use, kept in one FM-1 preset bank.

On firmware V16 a single-voice dump lands in whichever part ("Voice1-8") is
selected on the unit, whatever its channel, so the Mac can't load eight parts
by dump. A Program Change does reach just the parts on its channel. So: put
all the songs' sounds in one 32-voice bank on the unit (one confirmation on
the unit when it arrives), and have each song pick its sounds by program
change.

The Mac can't read presets back from the FM-1, so a manifest file records
what was last sent and where. Slots stay put when sounds are added, so
reloading the bank never reshuffles the existing presets.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import dx7, syx
from .song import Song, resolve_vced, sound_key

LETTERS = "ABCD"
SLOTS = 32
FREE = "-- free --"


def song_sounds(songs: list[Song]) -> list[tuple[str, str, dict[str, int]]]:
    """(key, spec, edits) for every distinct sound the songs use, in order."""
    seen: dict[str, tuple[str, str, dict[str, int]]] = {}
    for song in songs:
        for part in song.parts:
            if part.sound:
                key = sound_key(part.sound, part.edits)
                seen.setdefault(key, (key, part.sound, dict(part.edits)))
    return list(seen.values())


@dataclass
class Manifest:
    bank: str                           # A-D
    slots: list[str | None]             # sound key per slot, None = free
    sent: str = ""                      # ISO date of the last send

    def program(self, key: str) -> int | None:
        """Program Change number (0-127) for a sound, if it's in the bank."""
        if key not in self.slots:
            return None
        return LETTERS.index(self.bank) * SLOTS + self.slots.index(key)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"bank": self.bank, "slots": self.slots,
                                    "sent": self.sent}, indent=2) + "\n")

    @classmethod
    def load(cls, path: Path) -> "Manifest | None":
        if not path.is_file():
            return None
        data = json.loads(path.read_text())
        slots = data["slots"]
        if data["bank"] not in LETTERS or len(slots) != SLOTS:
            raise ValueError(f"{path} is damaged; delete it and run load-bank again")
        return cls(data["bank"], slots, data.get("sent", ""))


def plan(keys: list[str], bank: str, previous: Manifest | None) -> Manifest:
    """Assign sounds to slots, keeping the slots of sounds already loaded."""
    if bank not in LETTERS:
        raise ValueError(f"bank must be one of {LETTERS}")
    if previous and previous.bank == bank:
        slots = [k if k in keys else None for k in previous.slots]
    else:
        slots = [None] * SLOTS
    for key in keys:
        if key not in slots:
            if None not in slots:
                raise ValueError(f"the songs use {len(set(keys))} sounds; a bank holds {SLOTS}")
            slots[slots.index(None)] = key
    return Manifest(bank, slots, date.today().isoformat())


def build(manifest: Manifest, sounds: dict[str, tuple[str, dict[str, int]]],
          library: Callable[[], list[syx.Patch]]) -> list[list[int]]:
    """The 32 VCEDs to send; free slots get a silent placeholder."""
    free = dx7.Voice(name=FREE)
    for op in free.operators:
        op.output_level = 0
    out = []
    for key in manifest.slots:
        if key is None:
            out.append(free.to_vced())
        else:
            spec, edits = sounds[key]
            out.append(resolve_vced(spec, edits, library))
    return out
