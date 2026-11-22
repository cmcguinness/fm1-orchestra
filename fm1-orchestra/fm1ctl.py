#!/usr/bin/env python3
"""Command-line control for the M-VAVE FM-1."""

import argparse
import contextlib
import shutil
import signal
import sys
import time
from pathlib import Path

import mido

from fm1 import dx7, syx
from fm1 import bank as bank_mod
from fm1 import song as song_mod
from fm1 import stems as stems_mod
from fm1.effects import (IDENTITY_REQUEST, REVERB_SPACES, effect_messages,
                         firmware_version, parse_identity)
from fm1.player import play, release_all, schedule, select_tracks, track_summary
from fm1.record import DEFAULT_DEVICE as RECORD_DEVICE, Recorder, RecordError, check_ready
from fm1.port import DEFAULT_PORT_HINT, PortNotFound, open_input, open_output
from fm1.voices import VOICES

CODE = Path(__file__).resolve().parent          # fm1-orchestra/
ROOT = CODE.parent                              # the repository: fm1-orchestra/ and songs/
DEFAULT_LIBRARY = CODE / "sysex"
DEFAULT_SONGS = ROOT / "songs"
WIP_SONGS = ROOT / "songs-wip"               # works in progress, gitignored
# What the Mac last loaded into the FM-1's song bank (it can't be read back).
LOCAL = ROOT / "local"                          # gitignored: files that stay on this machine
BANK_MANIFEST = LOCAL / "fm1-bank.json"         # what was last sent to the unit's song bank


def _channel(text: str) -> int:
    value = int(text)
    if not 1 <= value <= 16:
        raise argparse.ArgumentTypeError("channel must be 1-16")
    return value


def _positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return value


def _non_negative_float(text: str) -> float:
    value = float(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be 0 or more")
    return value


def _percent(text: str) -> int:
    value = int(text)
    if not 0 <= value <= 100:
        raise argparse.ArgumentTypeError("must be 0-100")
    return value


def _midi_file(text: str) -> Path:
    path = Path(text)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"no such file: {text}")
    return path


def _record_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--record", type=Path, metavar="FILE",
                   help="record the FM-1's USB audio to FILE (.wav .flac .mp3 .m4a .aiff); "
                        "silence trimmed, peak normalised")
    p.add_argument("--no-normalize", action="store_true",
                   help="with --record: keep the level as captured")
    p.add_argument("--record-device", default=RECORD_DEVICE, metavar="NAME",
                   help="audio input to record (default: %(default)s)")


def _window_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--start", type=_non_negative_float, default=0.0, help="start at N seconds")
    p.add_argument("--end", type=_positive_float, help="stop at N seconds")
    p.add_argument("--speed", type=_positive_float,
                   help="tempo multiplier (default: the song's, else 1)")
    p.add_argument("--transpose", type=int, help="semitones (default: the song's, else 0)")
    _record_options(p)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", default=DEFAULT_PORT_HINT,
                   help="substring of the MIDI port name (default: %(default)s)")
    p.add_argument("--library", type=Path, default=DEFAULT_LIBRARY,
                   help="folder of DX7 .syx banks (default: fm1-orchestra/sysex)")
    p.add_argument("--songs", type=Path, default=DEFAULT_SONGS,
                   help="folder of song folders, one per song (default: songs, plus "
                        "songs-wip for works in progress)")
    p.add_argument("--fx-channel", type=_channel, default=16,
                   help="the FM-1's Effect Ch (GLO page) for effect CCs (default: %(default)s)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("ports", help="list MIDI ports")
    sub.add_parser("identity", help="ask the FM-1 to identify itself")
    sub.add_parser("voices", help="list the built-in voices")

    sv = sub.add_parser("send-voice",
                        help="send a built-in voice to the edit buffer of the part selected on the FM-1")
    sv.add_argument("voice", choices=sorted(VOICES))
    sv.add_argument("--channel", type=_channel, default=1, help="1-16 (default 1)")
    sv.add_argument("--save-syx", type=Path, metavar="PATH",
                    help="also write the voice as a .syx file")

    rv = sub.add_parser("reverb", help="set the FM-1's reverb")
    rv.add_argument("space", choices=[*REVERB_SPACES, "off"])
    rv.add_argument("--decay", type=_percent, default=92, help="0-100 (default 92)")
    rv.add_argument("--mix", type=_percent, default=50, help="0-100 (default 50)")
    rv.add_argument("--channel", type=_channel,
                    help="effect channel (default: --fx-channel)")

    pa = sub.add_parser("patches", help="list or search the .syx patch library")
    pa.add_argument("search", nargs="?", help="case-insensitive name substring")
    pa.add_argument("--bank", help="only this bank (file name without .syx)")

    sp = sub.add_parser("send-patch",
                        help="send a library patch to the edit buffer of the part selected on the FM-1")
    sp.add_argument("patch", help="BANK:N, e.g. rom1a:11 (see `patches`); add edits as "
                                  "BANK:N,op1.r1=80,fb=3")
    sp.add_argument("--channel", type=_channel, default=1)

    sub.add_parser("panic", help="release every note on every channel (stuck notes)")

    n = sub.add_parser("note", help="play a test chord")
    n.add_argument("--channel", type=_channel, default=1)

    pl = sub.add_parser("play", help="play a MIDI file on the FM-1")
    pl.add_argument("file", type=_midi_file)
    sound = pl.add_mutually_exclusive_group()
    sound.add_argument("--voice", choices=sorted(VOICES),
                       help="send this built-in voice first (default: keep the current one)")
    sound.add_argument("--patch", metavar="BANK:N",
                       help="send this library patch first (edits: BANK:N,op1.r1=80)")
    pl.add_argument("--channel", type=_channel, default=1)
    _window_options(pl)
    pl.add_argument("--reverb", choices=[*REVERB_SPACES, "off"],
                    help="set reverb first")
    pl.add_argument("--reverb-decay", type=_percent, default=92,
                    help="0-100 (default %(default)s)")
    pl.add_argument("--reverb-mix", type=_percent, default=50,
                    help="0-100 (default %(default)s)")
    pl.add_argument("--no-pedal", action="store_true",
                    help="ignore the file's sustain pedal")
    pl.add_argument("--track", action="append", metavar="NAME_OR_NUMBER",
                    help="play only this track (repeatable; see the `tracks` command)")
    pl.add_argument("--part", action="append", nargs="+", metavar="ARG",
                    help="CHANNEL SOUND TRACK [TRACK ...]: play these tracks on the FM-1 "
                         "part listening on CHANNEL, after sending it SOUND (a built-in "
                         "voice, BANK:N[,op1.r1=80,...], or - to keep its sound). Repeatable; replaces "
                         "--channel/--voice/--patch/--track. Set each part's MIDI Ch on "
                         "the unit (PRESETS list, SELECT to Voice1-8)")
    pl.add_argument("--velocity", action="append", nargs=2, metavar=("CHANNEL", "SCALE"),
                    help="with --part: multiply that part's note velocities by SCALE "
                         "(e.g. 3 1.6 makes channel 3 louder). Repeatable")

    pl.add_argument("--no-song", action="store_true",
                    help="ignore any song module in the file's folder that plays this file")

    sg = sub.add_parser("song", help="play a song module from the songs folder")
    sg.add_argument("name", help="module name without .py, e.g. aquarium (see `songs`)")
    _window_options(sg)
    sg.add_argument("--reverb", choices=[*REVERB_SPACES, "off"],
                    help="override the song's reverb")
    sg.add_argument("--reverb-decay", type=_percent, default=92, help="0-100 (default %(default)s)")
    sg.add_argument("--reverb-mix", type=_percent, default=50, help="0-100 (default %(default)s)")
    sg.add_argument("--no-pedal", action="store_true", help="ignore the file's sustain pedal")
    sg.add_argument("--stems", action="store_true",
                    help="with --record: record each part alone, then mix them with each "
                         "part's pan (the FM-1 ignores MIDI pan); stems kept in "
                         "FILE's folder under <name>-stems/")
    sg.add_argument("--remix", action="store_true",
                    help="with --record FILE: re-mix the stems already recorded for FILE "
                         "with the song's current pans; plays nothing")

    sub.add_parser("songs", help="list the song modules")

    vd = sub.add_parser("video", help="build a song's 1080p slide-show video from its recording")
    vd.add_argument("name", help="song name, e.g. aquarium: uses songs/NAME/NAME-slides.py")
    vd.add_argument("--audio", type=Path,
                    help="recording to use (default: songs/NAME/build/NAME.wav)")
    vd.add_argument("--out", type=Path, help="the .mp4 to write (default: songs/NAME/NAME.mp4)")

    lb = sub.add_parser("load-bank",
                        help="send every song module's sounds to one FM-1 preset bank")
    lb.add_argument("--bank", choices=list(bank_mod.LETTERS), default="D",
                    help="preset bank to overwrite (default: %(default)s)")
    lb.add_argument("--extra", action="append", default=[], metavar="SOUND",
                    help="also include this sound (built-in voice or BANK:N[,edits]); repeatable")
    lb.add_argument("--dry-run", action="store_true", help="show the plan, send nothing")

    im = sub.add_parser("import-score", help="convert a MusicXML score (.mxl/.musicxml) to a MIDI file")
    im.add_argument("score", type=_midi_file, help="the MusicXML file")
    im.add_argument("output", type=Path, help="MIDI file to write, e.g. songs/aquarium/aquarium.mid")
    im.add_argument("--bpm", type=_positive_float, required=True,
                    help="quarter-note tempo (scores often only say e.g. Andantino)")

    tr = sub.add_parser("tracks", help="list the tracks in a MIDI file")
    tr.add_argument("file", type=_midi_file)
    return p


def cmd_ports(_args) -> None:
    print("Outputs:", *mido.get_output_names(), sep="\n  ")
    print("Inputs:", *mido.get_input_names(), sep="\n  ")


def cmd_identity(args) -> None:
    with open_output(args.port) as out, open_input(args.port) as inp:
        out.send(mido.Message("sysex", data=IDENTITY_REQUEST))
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            for msg in inp.iter_pending():
                if msg.type == "sysex":
                    reply = bytes(msg.bytes())
                    print(parse_identity(reply) or "unrecognised reply")
                    print(reply.hex(" "))
                    return
            time.sleep(0.01)
    sys.exit("No reply from the FM-1.")


def cmd_voices(_args) -> None:
    for key, make in sorted(VOICES.items()):
        print(f"{key:10} {make().name!r:14} {(make.__doc__ or '').strip()}")


def send_voice(out, key: str, channel: int) -> dx7.Voice:
    voice = VOICES[key]()
    out.send(mido.Message("sysex", data=dx7.single_voice_sysex(voice, channel - 1)))
    time.sleep(0.3)                     # let the FM-1 digest it before CCs/notes arrive
    return voice


def cmd_send_voice(args) -> None:
    with open_output(args.port) as out:
        voice = send_voice(out, args.voice, args.channel)
    print(f"Sent {voice.name!r} to the edit buffer. Press SAVE on the FM-1 to keep it.")
    if args.save_syx:
        msg = mido.Message("sysex", data=dx7.single_voice_sysex(voice, 0))
        args.save_syx.write_bytes(bytes(msg.bytes()))
        print(f"Wrote {args.save_syx}")


def set_reverb(port_hint: str, out, space: str, decay: int = 92, mix: int = 50,
               channel: int = 1) -> int:
    firmware = firmware_version(port_hint, out)
    if firmware is None:
        sys.exit("The FM-1 didn't report its firmware version; can't pick the CC map.")
    if space == "off":
        msgs = effect_messages(firmware, "reverb", on=False, channel=channel - 1)
    else:
        msgs = effect_messages(firmware, "reverb", channel=channel - 1,
                               space=REVERB_SPACES[space], decay=decay, mix=mix)
    for msg in msgs:
        out.send(msg)
    return firmware


def cmd_reverb(args) -> None:
    with open_output(args.port) as out:
        fw = set_reverb(args.port, out, args.space, args.decay, args.mix,
                        args.channel or args.fx_channel)
    detail = "" if args.space == "off" else f" (decay {args.decay}, mix {args.mix})"
    print(f"Reverb {args.space}{detail} on firmware V{fw}.")


def _library(folder: Path) -> list[syx.Patch]:
    if not folder.is_dir():
        sys.exit(f"No patch library at {folder}")
    patches, warnings = syx.load_library(folder)
    for w in warnings:
        print("warning:", w, file=sys.stderr)
    return patches


def _find_patch(library: list[syx.Patch], spec: str) -> syx.Patch:
    """'BANK:N' or 'BANK:N,op1.r1=80,...' -> the (edited) patch."""
    ref, *edits = [s.strip() for s in spec.split(",")]
    return syx.edit(syx.find(library, ref), edits)


def _patch(folder: Path, spec: str) -> syx.Patch:
    try:
        return _find_patch(_library(folder), spec)
    except ValueError as exc:
        sys.exit(str(exc))


def send_patch(out, patch: syx.Patch, channel: int) -> None:
    out.send(mido.Message("sysex", data=dx7.vced_sysex(patch.vced, channel - 1)))
    time.sleep(0.3)


def cmd_patches(args) -> None:
    patches = _library(args.library)
    if args.bank:
        patches = [p for p in patches if p.source.stem.lower() == args.bank.lower()]
    if args.search:
        patches = [p for p in patches if args.search.lower() in p.name.lower()]
    for p in patches:
        print(f"{p.ref:16} {p.name}")
    print(f"{len(patches)} patch(es)", file=sys.stderr)


def cmd_send_patch(args) -> None:
    patch = _patch(args.library, args.patch)
    with open_output(args.port) as out:
        send_patch(out, patch, args.channel)
    print(f"Sent {patch.ref} {patch.name!r}. Press SAVE on the FM-1 to keep it.")


def cmd_note(args) -> None:
    ch = args.channel - 1
    with open_output(args.port) as out:
        for note in (50, 57, 62, 65):               # D minor
            out.send(mido.Message("note_on", channel=ch, note=note, velocity=100))
        time.sleep(1.5)
        for note in (50, 57, 62, 65):
            out.send(mido.Message("note_off", channel=ch, note=note))


def _song_from_parts(args) -> song_mod.Song:
    """Build a Song from --part / --velocity / --reverb* on the command line."""
    if args.voice or args.patch or args.track or args.channel != 1:
        sys.exit("--part can't be combined with --voice, --patch, --track or --channel")
    parts: dict[int, song_mod.Part] = {}
    for item in args.part:
        if len(item) < 3:
            sys.exit(f"--part needs CHANNEL SOUND TRACK..., got {' '.join(item)!r}")
        try:
            channel = _channel(item[0])
        except (ValueError, argparse.ArgumentTypeError):
            sys.exit(f"--part channel must be 1-16, got {item[0]!r}")
        if channel in parts:
            sys.exit(f"channel {channel} is given to two --part options")
        sound, *edits = [s.strip() for s in item[1].split(",")]
        parts[channel] = song_mod.Part(
            channel=channel, tracks=item[2:], sound=None if sound == "-" else sound,
            edits=dict(e.split("=", 1) if "=" in e else (e, "") for e in edits))
    for ch_text, scale_text in args.velocity or []:
        try:
            ch, scale = _channel(ch_text), _positive_float(scale_text)
        except (ValueError, argparse.ArgumentTypeError):
            sys.exit(f"--velocity needs CHANNEL (1-16) and SCALE (> 0), got {ch_text} {scale_text}")
        if ch not in parts:
            sys.exit(f"--velocity channel {ch} isn't one of the --part channels")
        parts[ch].velocity = scale
    return song_mod.Song(midi=str(args.file.resolve()), parts=list(parts.values()),
                         title=args.file.stem)


def _apply_overrides(args, song: song_mod.Song) -> None:
    """Command-line options that override a song's own settings."""
    if args.reverb:
        song.reverb = song_mod.Reverb(args.reverb, args.reverb_decay, args.reverb_mix)
    if args.no_pedal:
        song.pedal = False


def _session(args, song: song_mod.Song, module=None) -> song_mod.Session:
    """Check everything about the song before any MIDI goes out."""
    cache: list[list[syx.Patch]] = []

    def library() -> list[syx.Patch]:
        if not cache:
            cache.append(_library(args.library))
        return cache[0]
    try:
        bank = bank_mod.Manifest.load(BANK_MANIFEST)
        return song_mod.Session(song, library, args.fx_channel, args.port, module, bank)
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))


def _recording(args):
    """A Recorder if --record was given, else a no-op context."""
    if not args.record:
        return contextlib.nullcontext()
    return Recorder(args.record.expanduser(), normalize=not args.no_normalize,
                    device=args.record_device)


def _check_record(args) -> None:
    if args.no_normalize and not args.record:
        sys.exit("--no-normalize only works with --record")
    if args.record:
        try:
            device = None if getattr(args, "remix", False) else args.record_device
            check_ready(args.record.expanduser(), device)
        except RecordError as exc:
            sys.exit(str(exc))


def _run(args, session: song_mod.Session, source: str) -> None:
    events = session.events(args.start, args.end, args.speed)
    if not any(m.type == "note_on" for _, m in events):
        sys.exit("Nothing to play in that selection.")
    total = events[-1][0]
    print(f"{session.song.title} ({source})")
    for line in session.describe():
        print("  " + line)
    if session.song.reverb:
        r = session.song.reverb
        print(f"  Reverb: {r.space}" + ("" if r.space == "off" else f" (decay {r.decay}, mix {r.mix})"))

    def progress(at: float) -> None:
        print(f"\r  {int(at) // 60}:{int(at) % 60:02d} / "
              f"{int(total) // 60}:{int(total) % 60:02d}", end="", flush=True)
    with open_output(args.port) as out:
        session.out = out
        print(f"Playing ({total / 60:.1f} min). Ctrl-C to stop.")
        try:
            with _recording(args):
                session.perform(args.start, args.end, args.speed, args.transpose, progress)
                print()
        except KeyboardInterrupt:
            print("\nStopped.")
        except RuntimeError as exc:             # includes RecordError
            sys.exit(str(exc))


STEM_SETTLE = 0.5   # seconds; takes then line up within ~10 ms (measured 2026-11-21)


def _run_stems(args, session: song_mod.Session, source: str) -> None:
    """Record each part alone (aligned on playback start), then mix with pan."""
    if getattr(session.module, "perform", None):
        sys.exit(f"{source} has its own perform(); --stems can't split it into parts")
    output = args.record.expanduser()
    folder = output.parent / f"{output.stem}-stems"
    folder.mkdir(exist_ok=True)
    session.window = dict(start=args.start, end=args.end, speed=args.speed)
    session.transpose = args.transpose
    session.on_progress = None
    events = session.events()
    parts = session.song.parts
    passes = [(p, [e for e in events if e[1].channel == p.channel - 1]) for p in parts]
    passes = [(p, ev) for p, ev in passes if any(m.type == "note_on" for _, m in ev)]
    if not passes:
        sys.exit("Nothing to play in that selection.")
    total = events[-1][0]
    print(f"{session.song.title} ({source}): {len(passes)} stems of "
          f"{total / 60:.1f} min each, about {len(passes) * (total + 4) / 60:.0f} min in all")
    for line in session.describe():
        print("  " + line)
    takes = []
    with open_output(args.port) as out:
        session.out = out
        try:
            for i, (part, ev) in enumerate(passes, 1):
                name = "-".join(t.replace(" ", "_") for t in part.tracks)
                path = folder / f"{part.channel:02}-{name}.wav"
                print(f"  Stem {i} of {len(passes)}: Ch {part.channel} ({', '.join(part.tracks)}), "
                      f"pan {part.pan:+g}", flush=True)
                rec = Recorder(path, device=args.record_device, raw=True)
                with rec:
                    session.setup()
                    time.sleep(STEM_SETTLE)    # let program and effect changes land first
                    rec.mark()
                    session.play(ev)
                takes.append(stems_mod.Stem(path, rec.mark_frame, part.pan, part.channel))
        except KeyboardInterrupt:
            sys.exit("\nStopped; no mix written.")
        except RuntimeError as exc:
            sys.exit(str(exc))
    stems_mod.save(takes, folder)
    try:
        stems_mod.mix(takes, output, normalize=not args.no_normalize)
    except RecordError as exc:
        sys.exit(str(exc))
    print(f"  Stems in {folder}")


def _remix(args, song: song_mod.Song) -> None:
    """Mix the saved stems again with the song's current pans (no playing)."""
    output = args.record.expanduser()
    folder = output.parent / f"{output.stem}-stems"
    try:
        takes = stems_mod.repan(stems_mod.load(folder),
                                {p.channel: p.pan for p in song.parts})
        for t in takes:
            print(f"  {t.path.name:34} pan {t.pan:+g}")
        stems_mod.mix(takes, output, normalize=not args.no_normalize)
        stems_mod.save(takes, folder)
    except (RecordError, OSError, ValueError) as exc:
        sys.exit(str(exc))


def _song_folders(args) -> list[Path]:
    """Where song folders live: --songs, plus songs-wip/ when --songs is the default."""
    folders = [args.songs]
    if args.songs == DEFAULT_SONGS and WIP_SONGS.is_dir():
        folders.append(WIP_SONGS)
    return folders


def _song_files(args) -> list[Path]:
    return [path for folder in _song_folders(args) for path in song_mod.song_files(folder)]


def _song_folder(args, name: str) -> Path:
    """The folder holding song NAME (the first that has it, else --songs)."""
    return next((f for f in _song_folders(args) if song_mod.song_path(f, name).is_file()),
                args.songs)


def cmd_song(args) -> None:
    _check_record(args)
    if args.stems and not args.record:
        sys.exit("--stems needs --record FILE (the mix)")
    if args.remix and (not args.record or args.stems):
        sys.exit("--remix needs --record FILE (the mix to rewrite) and no --stems")
    path = song_mod.song_path(_song_folder(args, args.name), args.name)
    if not path.is_file():
        names = ", ".join(p.stem for p in _song_files(args)) or "none"
        sys.exit(f"no song module {path}; songs: {names}")
    if args.end is not None and args.end <= args.start:
        sys.exit("--end must be after --start")
    try:
        song, module = song_mod.load_module(path)
    except Exception as exc:                    # a song file is user code
        sys.exit(f"{path.name}: {exc}")
    _apply_overrides(args, song)
    if args.remix:
        _remix(args, song)
        return
    runner = _run_stems if args.stems else _run
    runner(args, _session(args, song, module), path.name)


def cmd_load_bank(args) -> None:
    songs = []
    for path in _song_files(args):
        try:
            songs.append(song_mod.load_module(path)[0])
        except Exception as exc:
            sys.exit(f"{path.name}: {exc}")
    sounds = {key: (spec, edits) for key, spec, edits in bank_mod.song_sounds(songs)}
    for spec in args.extra:
        ref, *edits = [s.strip() for s in spec.split(",")]
        edit_map = dict(e.split("=", 1) if "=" in e else (e, "") for e in edits)
        sounds.setdefault(song_mod.sound_key(ref, edit_map), (ref, edit_map))
    cache: list[list[syx.Patch]] = []

    def library() -> list[syx.Patch]:
        if not cache:
            cache.append(_library(args.library))
        return cache[0]
    try:
        previous = bank_mod.Manifest.load(BANK_MANIFEST)
        manifest = bank_mod.plan(list(sounds), args.bank, previous)
        vceds = bank_mod.build(manifest, sounds, library)
    except ValueError as exc:
        sys.exit(str(exc))
    base = bank_mod.LETTERS.index(args.bank) * bank_mod.SLOTS
    for i, (key, vced) in enumerate(zip(manifest.slots, vceds)):
        if key:
            name = "".join(map(chr, vced[145:155])).rstrip()
            print(f"  preset {base + i + 1:03} ({args.bank}{i + 1:02})  {name:10}  {key}")
    used = sum(k is not None for k in manifest.slots)
    print(f"{used} sound(s), {bank_mod.SLOTS - used} free slot(s) in bank {args.bank}.")
    if args.dry_run:
        return
    with open_output(args.port) as out:
        out.send(mido.Message("sysex", data=syx.bank_sysex(vceds)))
    manifest.save(BANK_MANIFEST)
    print(f"Sent. On the FM-1, choose bank {args.bank} when it asks where to store the bank.")


def cmd_video(args) -> None:
    from fm1 import video
    folder = _song_folder(args, args.name) / args.name
    spec = folder / f"{args.name}-slides.py"
    audio = args.audio or folder / "build" / f"{args.name}.wav"
    out = args.out or folder / f"{args.name}.mp4"
    for f, what in ((spec, "slide spec"), (audio, "recording")):
        if not f.is_file():
            sys.exit(f"no {what} {f}" + (f"; record it with: fm1ctl.py song {args.name} "
                                         f"--record {audio}" if f == audio else ""))
    if out.suffix.lower() != ".mp4":
        sys.exit("--out must end in .mp4")
    if shutil.which("ffmpeg") is None:
        sys.exit("needs ffmpeg (brew install ffmpeg)")
    video.build(spec, audio, out, folder / "build" / "slides")


def cmd_songs(args) -> None:
    for path in _song_files(args):
        try:
            song, _ = song_mod.load_module(path)
            present = "" if song.midi_path.is_file() else "  (MIDI file missing)"
            print(f"{path.stem:16} {song.title}{present}")
        except Exception as exc:
            print(f"{path.stem:16} BROKEN: {exc}")


def cmd_play(args) -> None:
    _check_record(args)
    if args.velocity and not args.part:
        sys.exit("--velocity only works with --part")
    if args.end is not None and args.end <= args.start:
        sys.exit("--end must be after --start")
    if args.part:
        song = _song_from_parts(args)
        _apply_overrides(args, song)
        _run(args, _session(args, song), "--part")
        return
    if not (args.voice or args.patch or args.track or args.no_song):
        found = song_mod.find_for_midi(args.file.parent, args.file)
        if found:
            song, module = song_mod.load_module(found)
            _apply_overrides(args, song)
            _run(args, _session(args, song, module), found.name)
            return
    midi = mido.MidiFile(args.file)
    tracks = None
    if args.track:
        try:
            tracks = select_tracks(midi, args.track)
        except ValueError as exc:
            sys.exit(str(exc))
    patch = _patch(args.library, args.patch) if args.patch else None
    events = schedule(midi, args.start, args.end, args.speed or 1.0, tracks,
                      pedal=not args.no_pedal)
    if not any(m.type == "note_on" for _, m in events):
        sys.exit("Nothing to play in that selection.")
    with open_output(args.port) as out:
        if args.voice:
            voice = send_voice(out, args.voice, args.channel)
            print(f"Voice: {voice.name}")
        if patch:
            send_patch(out, patch, args.channel)
            print(f"Patch: {patch.ref} {patch.name}")
        if args.reverb:
            set_reverb(args.port, out, args.reverb, args.reverb_decay,
                       args.reverb_mix, channel=args.fx_channel)
            print(f"Reverb: {args.reverb}")
        if tracks is not None:
            names = [midi.tracks[i].name.strip() or f"#{i}" for i in tracks]
            print("Tracks:", ", ".join(names))
        _perform(args, out, events, args.channel - 1)


def _perform(args, out, events, channel: int) -> None:
    total = events[-1][0]
    print(f"Playing {args.file.name} ({total / 60:.1f} min). Ctrl-C to stop.")

    def progress(at: float) -> None:
        print(f"\r  {int(at) // 60}:{int(at) % 60:02d} / "
              f"{int(total) // 60}:{int(total) % 60:02d}", end="", flush=True)
    try:
        with _recording(args):
            play(out, events, channel, args.transpose or 0, progress)
            print()
    except KeyboardInterrupt:
        print("\nStopped.")
    except RecordError as exc:
        sys.exit(str(exc))


def cmd_panic(args) -> None:
    with open_output(args.port) as out:
        release_all(out)
    print("Released every note on all 16 channels.")


def cmd_import_score(args) -> None:
    from fm1.score import read_score, write_midi
    if args.output.suffix.lower() not in (".mid", ".midi"):
        sys.exit("output must end in .mid")
    if not args.output.parent.is_dir():
        sys.exit(f"no such folder: {args.output.parent}")
    staves = read_score(args.score)
    write_midi(staves, args.output, args.bpm, args.score.stem)
    for s in staves:
        print(f"  {s.name:26} {len(s.notes):5} notes" + (f", {len(s.pedal)} pedal" if s.pedal else ""))
    print(f"Wrote {args.output} at {args.bpm:g} bpm.")


def cmd_tracks(args) -> None:
    for index, name, notes in track_summary(mido.MidiFile(args.file)):
        print(f"{index:3}  {name or '(unnamed)':28} {notes:5} notes")


COMMANDS = {
    "ports": cmd_ports, "identity": cmd_identity, "voices": cmd_voices,
    "send-voice": cmd_send_voice, "reverb": cmd_reverb, "note": cmd_note,
    "play": cmd_play, "tracks": cmd_tracks, "song": cmd_song, "songs": cmd_songs, "video": cmd_video,
    "load-bank": cmd_load_bank, "import-score": cmd_import_score,
    "patches": cmd_patches, "send-patch": cmd_send_patch, "panic": cmd_panic,
}


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    # Turn a polite kill into an exception so the player's cleanup runs and no
    # notes are left sounding (the FM-1 ignores All Notes Off).
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: sys.exit(1))
    try:
        COMMANDS[args.command](args)
    except PortNotFound as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
