"""Songs: a MIDI file plus everything needed to play it well on the FM-1.

A song module is songs/NAME/NAME.py; it defines SONG, a Song:

    from fm1.song import Part, Reverb, Song

    SONG = Song(                                # plays aquarium.mid, next to this
        title="Aquarium",
        parts=[
            Part(channel=1, sound="rom1a:8", tracks=["Piano"], velocity=0.75),
            Part(channel=3, sound="dxoc12:21", edits={"op1.r1": 80},
                 tracks=["Harmonica"], velocity=2.5),
        ],
        reverb=Reverb("hall", decay=75, mix=25),
    )

The MIDI file defaults to the module's name with .mid (aquarium.py plays
aquarium.mid); set midi="..." to use another file. Each Part goes to the FM-1 part ("Voice1-8" on the unit) whose MIDI Ch is
`channel`. A module may also define `perform(session)` to take over playing;
the default is `session.setup(); session.play(session.events())`.
"""

import importlib.util
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import mido

from . import syx
from .dx7 import drones
from .humanize import Humanize
from . import humanize as humanize_mod
from . import articulate as articulate_mod
from .effects import REVERB_SPACES, effect_messages, firmware_version
from .player import play, schedule, select_tracks
from .voices import VOICES

EXPRESSION = 11         # CC: per-channel part volume on V16
FIGURE_GAP = 0.25       # seconds: a longer gap ends an arpeggio figure
PROGRAM_SETTLE = 0.05   # seconds for the FM-1 to load a preset


@dataclass
class Part:
    channel: int                        # 1-16: the FM-1 part's MIDI Ch
    tracks: list[str]                   # track names (substring) or numbers
    sound: str | None = None            # built-in voice, "BANK:N", or None: keep
    edits: dict[str, int] = field(default_factory=dict)   # e.g. {"op1.r1": 80}
    velocity: float = 1.0               # multiplies the part's note velocities
    expression: int = 127               # part volume, 0-127 (CC 11, firmware V16)
    transpose: int = 0                  # semitones, this part only
    shape: float = 0.0                  # 0-0.5: voice arpeggio figures (top louder, bottom softer)
    articulation: float = 1.0           # 0.2-1: fraction of each note's length played (detached < 1)
    accent: float = 0.0                 # 0-0.5: metric accents (downbeats louder, fast notes softer)
    vary: float = 0.0                   # 0-0.2: small repeatable velocity variation
    pan: float = 0.0                    # -1 left .. 1 right; used only by stem recording
                                        # (the FM-1 ignores MIDI pan, CC10)


@dataclass
class Reverb:
    space: str                          # room, hall, plate, or off
    decay: int = 92
    mix: int = 50


@dataclass
class Song:
    parts: list[Part]
    midi: str = ""                      # relative to the module, or absolute;
                                        # "" = the module's name + .mid
    title: str = ""
    reverb: Reverb | None = None
    pedal: bool = True
    speed: float = 1.0
    transpose: int = 0
    humanize: Humanize | None = None    # phrase rubato, breaths, jitter
    notes: str = ""
    folder: Path = Path(".")            # set by the loader

    @property
    def midi_path(self) -> Path:
        return (self.folder / self.midi).resolve()


@dataclass
class Sound:
    """A sound resolved for one part."""
    key: str                            # canonical name, see sound_key
    label: str
    vced: list[int]                     # 155 bytes
    program: int | None = None          # its Program Change in the song bank


def sound_key(spec: str, edits: dict[str, int] | None = None) -> str:
    """Canonical name for a sound: 'dxoc12:21,op1.r1=80' (edits sorted)."""
    parts = [spec.strip().lower()] + [f"{k.strip().lower()}={int(v)}"
                                      for k, v in sorted((edits or {}).items())]
    return ",".join(parts)


def _resolve(spec: str, edits: dict[str, int] | list[str],
             library: Callable[[], list[syx.Patch]]) -> tuple[str, list[int]]:
    edit_list = ([f"{k}={v}" for k, v in edits.items()] if isinstance(edits, dict)
                 else list(edits))
    if spec in VOICES:
        if edit_list:
            raise ValueError(f"edits apply to library patches, not built-in voice {spec!r}")
        voice = VOICES[spec]()
        return voice.name.strip(), voice.to_vced()
    if ":" not in spec:
        raise ValueError(f"unknown sound {spec!r}: use a built-in voice "
                         f"({', '.join(sorted(VOICES))}) or BANK:N")
    patch = syx.edit(syx.find(library(), spec), edit_list)
    return f"{patch.ref} {patch.name}" + (" (edited)" if edit_list else ""), patch.vced


def _check_releases(spec: str, vced: list[int]) -> None:
    held = drones(vced)
    if held:
        fix = ",".join(f"op{n}.l4=0" for n in held)
        raise ValueError(f"{spec}: operator(s) {held} keep sounding after release "
                         f"(a stuck tone only a panic stops). Use {spec},{fix}")


def resolve_vced(spec: str, edits: dict[str, int] | list[str],
                 library: Callable[[], list[syx.Patch]]) -> list[int]:
    """Built-in voice key or BANK:N (plus edits) -> 155 VCED bytes.

    Refuses sounds that never release (see dx7.drones)."""
    vced = _resolve(spec, edits, library)[1]
    _check_releases(spec, vced)
    return vced


def resolve_sound(spec: str, edits: dict[str, int],
                  library: Callable[[], list[syx.Patch]]) -> Sound:
    """Built-in voice key or BANK:N (plus edits) -> Sound. Raises ValueError.

    `library` is called only when a bank patch is needed (loading is slow-ish).
    """
    label, vced = _resolve(spec, edits, library)
    _check_releases(spec, vced)
    return Sound(sound_key(spec, edits), label, vced)


def validate(song: Song, midi: mido.MidiFile, fx_channel: int) -> list[list[int]]:
    """Check the song against its file; return each part's track indexes."""
    if not song.parts:
        raise ValueError("a song needs at least one part")
    seen_channels: set[int] = set()
    owner: dict[int, int] = {}
    resolved = []
    for part in song.parts:
        if not 1 <= part.channel <= 16:
            raise ValueError(f"part channel must be 1-16, got {part.channel}")
        if part.channel == fx_channel:
            raise ValueError(f"part channel {part.channel} is the effect channel; "
                             "the FM-1 treats notes there as LED commands")
        if part.channel in seen_channels:
            raise ValueError(f"channel {part.channel} is used by two parts")
        seen_channels.add(part.channel)
        if part.velocity <= 0:
            raise ValueError(f"part velocity scale must be > 0, got {part.velocity}")
        if not 0.2 <= part.articulation <= 1:
            raise ValueError(f"part articulation must be 0.2-1, got {part.articulation}")
        if not 0 <= part.accent <= 0.5:
            raise ValueError(f"part accent must be 0-0.5, got {part.accent}")
        if not 0 <= part.vary <= 0.2:
            raise ValueError(f"part vary must be 0-0.2, got {part.vary}")
        if not -1 <= part.pan <= 1:
            raise ValueError(f"part pan must be -1 (left) to 1 (right), got {part.pan}")
        if song.humanize and (part.accent or part.vary or part.articulation < 1):
            raise ValueError("accent/vary/articulation can't be combined with humanize")
        if not 0 <= part.shape <= 0.5:
            raise ValueError(f"part shape must be 0-0.5, got {part.shape}")
        if not -48 <= part.transpose <= 48:
            raise ValueError(f"part transpose must be -48..48, got {part.transpose}")
        if not 0 <= part.expression <= 127:
            raise ValueError(f"part expression must be 0-127, got {part.expression}")
        tracks = select_tracks(midi, part.tracks)
        for t in tracks:
            if t in owner:
                raise ValueError(f"track {t} is in two parts "
                                 f"(channels {owner[t]} and {part.channel})")
            owner[t] = part.channel
        resolved.append(tracks)
    if song.humanize:
        song.humanize.validate()
        if song.humanize.phrase_track is not None:
            select_tracks(midi, [song.humanize.phrase_track])
    if song.reverb:
        if song.reverb.space not in (*REVERB_SPACES, "off"):
            raise ValueError(f"reverb space must be one of {[*REVERB_SPACES, 'off']}")
        for name in ("decay", "mix"):
            if not 0 <= getattr(song.reverb, name) <= 100:
                raise ValueError(f"reverb {name} must be 0-100")
    return resolved


class Session:
    """One performance of a song: everything checked before any MIDI is sent.

    Build it, then open the port and call perform(). Song modules that define
    their own perform(session) use the pieces: setup(), events(), play().
    """

    def __init__(self, song: Song, library: Callable[[], list[syx.Patch]],
                 fx_channel: int = 16, port_hint: str = "FM-1",
                 module: ModuleType | None = None, bank=None):
        self.song = song
        self.module = module
        self.fx_channel = fx_channel
        self.port_hint = port_hint
        self.midi = mido.MidiFile(song.midi_path)
        self.part_tracks = validate(song, self.midi, fx_channel)
        self.sounds = [resolve_sound(p.sound, p.edits, library) if p.sound else None
                       for p in song.parts]
        # Parts get their sounds by Program Change from the song bank (a
        # bank.Manifest): on V16 a voice dump only reaches the part selected
        # on the unit, never a chosen part.
        missing = []
        for sound in filter(None, self.sounds):
            sound.program = bank.program(sound.key) if bank else None
            if sound.program is None:
                missing.append(sound.key)
        if missing:
            raise ValueError(f"not in the song bank on the FM-1: {', '.join(missing)}. "
                             "Add the song module (or --extra) and run `fm1ctl.py load-bank`")
        self.out: mido.ports.BaseOutput | None = None
        # Set by perform(); events() and play() fall back to them, so a custom
        # perform(session) honours --start/--end/--speed/--transpose for free.
        self.window: dict = dict(start=0.0, end=None, speed=None)
        self.transpose: int | None = None
        self.on_progress: Callable[[float], None] | None = None

    def describe(self) -> list[str]:
        lines = []
        for part, tracks, sound in zip(self.song.parts, self.part_tracks, self.sounds):
            names = ", ".join(self.midi.tracks[i].name.strip() or f"#{i}" for i in tracks)
            label = (f"{sound.label} [preset {sound.program + 1:03}]" if sound
                     else "(sound on the unit)")
            scale = f" x{part.velocity:g}" if part.velocity != 1 else ""
            if part.expression != 127:
                scale += f" expr {part.expression}"
            if part.transpose:
                scale += f" {part.transpose:+d} st"
            if part.articulation < 1:
                scale += f" art {part.articulation:g}"
            if part.accent:
                scale += f" acc {part.accent:g}"
            if part.pan:
                scale += f" pan {part.pan:+g}"
            lines.append(f"Ch {part.channel:2}: {label:30} <- {names}{scale}")
        return lines

    def setup(self) -> None:
        """Pick each part's sound and volume, then set the effects.

        Expression is always sent (127 by default) so a part never keeps a
        level left over from another song.
        """
        for part, sound in zip(self.song.parts, self.sounds):
            self.out.send(mido.Message("control_change", channel=part.channel - 1,
                                       control=EXPRESSION, value=part.expression))
            if sound:
                self.out.send(mido.Message("program_change", channel=part.channel - 1,
                                           program=sound.program))
                time.sleep(PROGRAM_SETTLE)
        if self.song.reverb:
            self.set_reverb(self.song.reverb)

    def set_reverb(self, reverb: Reverb) -> None:
        firmware = firmware_version(self.port_hint, self.out)
        if firmware is None:
            raise RuntimeError("the FM-1 didn't report its firmware; can't pick effect CCs")
        ch = self.fx_channel - 1
        if reverb.space == "off":
            msgs = effect_messages(firmware, "reverb", on=False, channel=ch)
        else:
            msgs = effect_messages(firmware, "reverb", channel=ch,
                                   space=REVERB_SPACES[reverb.space],
                                   decay=reverb.decay, mix=reverb.mix)
        for msg in msgs:
            self.out.send(msg)

    def events(self, start: float | None = None, end: float | None = None,
               speed: float | None = None) -> list[tuple[float, mido.Message]]:
        """The song's notes, each on its part's channel, velocities scaled."""
        start = self.window["start"] if start is None else start
        end = self.window["end"] if end is None else end
        speed = speed or self.window["speed"]
        channels = {t: p.channel - 1
                    for p, tracks in zip(self.song.parts, self.part_tracks) for t in tracks}
        scale = {p.channel - 1: p.velocity for p in self.song.parts}
        shift = {p.channel - 1: p.transpose for p in self.song.parts}
        speed = speed or self.song.speed
        h = self.song.humanize
        if h:
            # Shape the whole piece, then cut the window in performed time.
            full = schedule(self.midi, 0.0, None, speed, pedal=self.song.pedal,
                            channels=channels)
            onsets = []
            if h.phrase_track is not None:
                track = select_tracks(self.midi, [h.phrase_track])
                onsets = [at for at, m in schedule(self.midi, 0.0, None, speed,
                                                   tracks=track, pedal=False)
                          if m.type == "note_on" and m.velocity]
            shaped = humanize_mod.apply(full, h, onsets)
            bounds = (humanize_mod.phrase_bounds(onsets, h.phrase_gap, full[-1][0])
                      if onsets and full else [0.0, full[-1][0] if full else 0.0])

            def performed(score_seconds: float) -> float:
                return humanize_mod.warp_time(score_seconds / speed, bounds,
                                              h.rubato, h.breath)
            lo = performed(start) if start else 0.0
            hi = performed(end) if end is not None else None
            events = [(at - lo, m) for at, m in shaped
                      if at >= lo and (hi is None or at <= hi)]
        else:
            events = schedule(self.midi, start, end, speed,
                              pedal=self.song.pedal, channels=channels)
        shaped = self._figure_velocities(speed)
        offset = (start or 0.0) / speed if not h else 0.0
        out = []
        for at, msg in events:
            ch = msg.channel
            if shaped and msg.type == "note_on" and msg.velocity:
                v = shaped.get((ch, msg.note, round(at + offset, 3)))
                if v is not None:
                    msg = msg.copy(velocity=v)
            if shift[ch]:
                note = msg.note + shift[ch]
                if not 0 <= note <= 127:
                    continue                    # both on and off drop, so nothing sticks
                msg = msg.copy(note=note)
            if msg.type == "note_on" and msg.velocity and scale[ch] != 1:
                msg = msg.copy(velocity=max(1, min(127, round(msg.velocity * scale[ch]))))
            out.append((at, msg))
        accents = {p.channel - 1: p.accent for p in self.song.parts if p.accent}
        vary = {p.channel - 1: p.vary for p in self.song.parts if p.vary}
        if accents or vary:
            base = start or 0.0
            out = articulate_mod.accent(out, accents, articulate_mod.BeatClock(self.midi),
                                        lambda at: at * speed + base, vary)
        lengths = {p.channel - 1: p.articulation for p in self.song.parts
                   if p.articulation < 1}
        return articulate_mod.articulate(out, lengths)

    def _figure_velocities(self, speed: float) -> dict[tuple[int, int, float], int]:
        """Shaped velocities for parts with `shape`, keyed (channel, note, time).

        Each track is cut into figures (notes less than FIGURE_GAP apart);
        inside a figure, velocity follows pitch: the top note gets +shape,
        the bottom -shape, so a ripple swells to its peak and falls away.
        Timing is untouched. Time keys are unshaped schedule times, which
        the humanized path doesn't use (shape + humanize isn't supported).
        """
        out: dict[tuple[int, int, float], int] = {}
        for part, tracks in zip(self.song.parts, self.part_tracks):
            if not part.shape:
                continue
            for track in tracks:
                ons = [(at, m) for at, m in schedule(self.midi, 0.0, None, speed,
                                                     tracks=[track], pedal=False)
                       if m.type == "note_on" and m.velocity]
                figure: list[tuple[float, mido.Message]] = []
                for i, (at, m) in enumerate(ons + [(float("inf"), None)]):
                    if figure and (m is None or at - figure[-1][0] > FIGURE_GAP):
                        notes = [x.note for _, x in figure]
                        lo, hi = min(notes), max(notes)
                        for fat, fm in figure:
                            pos = (fm.note - lo) / (hi - lo) if hi > lo else 0.5
                            v = fm.velocity * (1 + part.shape * (2 * pos - 1))
                            out[(part.channel - 1, fm.note, round(fat, 3))] = \
                                max(1, min(127, round(v)))
                        figure = []
                    if m is not None:
                        figure.append((at, m))
        return out

    def play(self, events, transpose: int | None = None,
             on_progress: Callable[[float], None] | None = None) -> None:
        if transpose is None:
            transpose = self.song.transpose if self.transpose is None else self.transpose
        play(self.out, events, None, transpose, on_progress or self.on_progress)

    def perform(self, start: float = 0.0, end: float | None = None,
                speed: float | None = None, transpose: int | None = None,
                on_progress: Callable[[float], None] | None = None) -> None:
        self.window = dict(start=start, end=end, speed=speed)
        self.transpose = transpose
        self.on_progress = on_progress
        custom = getattr(self.module, "perform", None)
        if custom:
            custom(self)
        else:
            self.setup()
            self.play(self.events())


def load_module(path: Path) -> tuple[Song, ModuleType]:
    """Import a song module from its file and return its SONG."""
    spec = importlib.util.spec_from_file_location(f"fm1_song_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"can't load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    song = getattr(module, "SONG", None)
    if not isinstance(song, Song):
        raise ValueError(f"{path.name} doesn't define SONG = Song(...)")
    song.folder = path.parent
    if not song.midi:
        song.midi = f"{path.stem}.mid"
    if not song.title:
        song.title = path.stem
    return song, module


def song_path(folder: Path, name: str) -> Path:
    """The module for song NAME: folder/NAME/NAME.py (one folder per song)."""
    return folder / name / f"{name}.py"


def song_files(folder: Path) -> list[Path]:
    """Every song module under `folder` (song folders without one are skipped)."""
    if not folder.is_dir():
        return []
    return sorted(song_path(folder, d.name) for d in folder.iterdir()
                  if d.is_dir() and not d.name.startswith((".", "_"))
                  and song_path(folder, d.name).is_file())


def find_for_midi(folder: Path, midi_path: Path) -> Path | None:
    """The song module in the MIDI file's own song folder that plays it, if any.

    `folder` is the song folder (the MIDI file's parent)."""
    target = midi_path.resolve()
    for path in [song_path(folder.parent, folder.name)]:
        if not path.is_file():
            continue
        try:
            song, _ = load_module(path)
        except Exception:               # a broken song file shouldn't block plain play
            continue
        if song.midi_path == target:
            return path
    return None
