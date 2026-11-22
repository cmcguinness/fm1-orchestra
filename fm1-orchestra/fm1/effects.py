"""FM-1 effects, driven by MIDI CC.

Each effect is a group of four controllers: [switch, p1, p2, p3]. Firmware
V15 puts the groups at CC 0-23; V16 moved them up by 70 (CC 70-93). The
switch turns the effect on at any non-zero value.

The CCs are read only on the FM-1's Effect Channel (GLO page; factory
default 2). Sent on any other channel they do nothing, or worse: on a note
channel CC 1 is the mod wheel and, on V16, CC 7 is master volume.

Sources: the community FM-1 editor (src/lib/fm1-parameters.ts) for the V15
order; M-VAVE's V16 release notes for the V16 map ("Filter 70-73, Reverb
74-77, Delay 78-81, Distortion 82-85, Chorus 86-89, Phaser 90-93").
"""

import time

import mido

from .port import open_input

IDENTITY_REQUEST = [0x00, 0x32, 0x45, 0x00, 0x00, 0x00, 0x40, 0x7F]

# Group order and parameter names within each group.
GROUPS = {
    "filter":     ("type", "cutoff", "resonance"),   # type 0 LP, 1 BP, 2 HP
    "reverb":     ("space", "decay", "mix"),         # space 0 room, 1 hall, 2 plate
    "delay":      ("decay", "rate", "mix"),
    "distortion": ("gain", "tone", "level"),
    "chorus":     ("frequency", "depth", "mix"),
    "phaser":     ("frequency", "depth", "mix"),
}
REVERB_SPACES = {"room": 0, "hall": 1, "plate": 2}
_CC_BASE = {15: 0, 16: 70}


def _unpack_7bit(data: bytes) -> bytes:
    """Unpack a 7-bit SysEx stream, least-significant bit first."""
    acc = bits = 0
    out = bytearray()
    for byte in data:
        acc |= (byte & 0x7F) << bits
        bits += 7
        while bits >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            bits -= 8
    return bytes(out)


def parse_identity(reply: bytes) -> str | None:
    """Return the firmware name (e.g. 'FM-1_015') from an identity reply."""
    if len(reply) < 10 or reply[0] != 0xF0 or reply[1:4] != bytes([0x00, 0x32, 0x45]):
        return None
    decoded = _unpack_7bit(reply[1:-1])
    start = decoded.find(b"FM-1_")
    if start < 0:
        return None
    return decoded[start:start + 8].decode("ascii", "replace")


def firmware_version(port_hint: str, out: mido.ports.BaseOutput,
                     timeout: float = 2.0) -> int | None:
    """Ask the FM-1 which firmware it runs; return e.g. 15, or None."""
    with open_input(port_hint) as inp:
        out.send(mido.Message("sysex", data=IDENTITY_REQUEST))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for msg in inp.iter_pending():
                if msg.type == "sysex":
                    name = parse_identity(bytes(msg.bytes()))
                    if name and name[5:].isdigit():
                        return int(name[5:])
            time.sleep(0.01)
    return None


def cc_numbers(firmware: int, group: str) -> list[int]:
    """CC numbers [switch, p1, p2, p3] for an effect group."""
    if firmware not in _CC_BASE:
        raise ValueError(f"unknown CC map for firmware V{firmware}")
    base = _CC_BASE[firmware] + 4 * list(GROUPS).index(group)
    return [base, base + 1, base + 2, base + 3]


def effect_messages(firmware: int, group: str, on: bool = True,
                    channel: int = 0, **params: int) -> list[mido.Message]:
    """Messages that switch an effect on or off and set named parameters."""
    names = GROUPS[group]
    unknown = set(params) - set(names)
    if unknown:
        raise ValueError(f"{group} has no parameter(s) {sorted(unknown)}; use {names}")
    ccs = cc_numbers(firmware, group)
    msgs = [mido.Message("control_change", channel=channel,
                         control=ccs[0], value=127 if on else 0)]
    for name, value in params.items():
        if not 0 <= value <= 100:
            raise ValueError(f"{group} {name} must be 0-100")
        msgs.append(mido.Message("control_change", channel=channel,
                                 control=ccs[1 + names.index(name)], value=value))
    return msgs
