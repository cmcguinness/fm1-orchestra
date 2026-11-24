#!/usr/bin/env python3
"""Headless keyboard -> FM-1 bridge for a Raspberry Pi (or any Linux box).

Plug a USB MIDI keyboard and the FM-1 into the Pi (through a hub on a Zero).
Whenever both are present, the keyboard's notes go to one FM-1 channel through
the same KeyRouter as `fm1ctl.py play-keys`: notes, sustain, mod wheel, pitch
bend, aftertouch and program changes pass; other CCs are dropped so they can't
reach the FM-1's effects. Unplugging either side releases held notes and the
bridge waits for it to come back. Runs until stopped (systemd: fm1-bridge).
"""

import argparse
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import mido  # noqa: E402

from fm1.keys import KeyRouter, pick_keyboard  # noqa: E402
from fm1.port import DEFAULT_PORT_HINT, PortNotFound, find_port  # noqa: E402

IGNORED_INPUTS = ("midi through", "rtmidi")    # ALSA's loopback, other apps' ports


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--channel", type=int, default=1,
                   help="FM-1 MIDI channel to play (1-16, default 1; not the Effect Ch)")
    p.add_argument("--transpose", type=int, default=0, help="semitones (default 0)")
    p.add_argument("--velocity", type=float, default=1.0,
                   help="velocity scale (default 1.0)")
    p.add_argument("--keyboard", help="part of the keyboard's port name "
                   "(default: the only MIDI input that isn't the FM-1)")
    p.add_argument("--port", default=DEFAULT_PORT_HINT,
                   help=f"part of the FM-1's port name (default {DEFAULT_PORT_HINT})")
    p.add_argument("--poll", type=float, default=2.0,
                   help="seconds between checks for plugged/unplugged devices")
    p.add_argument("--show", action="store_true", help="print each message sent")
    args = p.parse_args(argv)
    if not 1 <= args.channel <= 16:
        p.error("--channel must be 1-16")
    if not -48 <= args.transpose <= 48:
        p.error("--transpose must be -48..48")
    if not 0 < args.velocity <= 4:
        p.error("--velocity must be in (0, 4]")
    if args.poll <= 0:
        p.error("--poll must be positive")
    return args


def log(msg: str) -> None:
    print(msg, flush=True)


def find_pair(args) -> tuple[str, str] | None:
    """(keyboard input, FM-1 output) port names, or None if either is missing."""
    try:
        out = find_port(mido.get_output_names(), args.port)
    except PortNotFound:
        return None
    inputs = [n for n in dict.fromkeys(mido.get_input_names())
              if not n.lower().startswith(IGNORED_INPUTS)]
    try:
        kb = pick_keyboard(inputs, args.keyboard, args.port)
    except ValueError:
        return None
    return kb, out


def bridge(args, kb_name: str, out_name: str) -> None:
    """Route kb_name -> out_name until either port disappears."""
    router = KeyRouter(args.channel, args.transpose, args.velocity)
    lock = threading.Lock()
    with mido.open_output(out_name) as out:
        def on_message(msg):
            with lock:
                for sent in router.translate(msg):
                    out.send(sent)
                    if args.show:
                        log(f"  {sent}")

        with mido.open_input(kb_name, callback=on_message):
            log(f"{kb_name} -> {out_name} channel {args.channel}")
            try:
                while True:
                    time.sleep(args.poll)
                    names = set(mido.get_input_names()) | set(mido.get_output_names())
                    if kb_name not in names or out_name not in names:
                        log("device unplugged")
                        return
            finally:
                with lock:
                    for msg in router.release():
                        try:
                            out.send(msg)
                        except Exception:       # the FM-1 itself may be gone
                            break


def main(argv=None) -> int:
    args = parse_args(argv)
    mido.set_backend("mido.backends.rtmidi")
    if args.channel == 16:
        log("warning: channel 16 is the FM-1's default Effect Ch; notes there "
            "light LEDs instead of playing")
    waiting = False
    try:
        while True:
            pair = find_pair(args)
            if pair is None:
                if not waiting:
                    log("waiting for the keyboard and the FM-1")
                    waiting = True
                time.sleep(args.poll)
                continue
            waiting = False
            try:
                bridge(args, *pair)
            except (OSError, RuntimeError) as exc:     # port vanished mid-open
                log(f"error: {exc}")
                time.sleep(args.poll)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
