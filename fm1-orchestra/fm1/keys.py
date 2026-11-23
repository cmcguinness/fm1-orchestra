"""Play the FM-1 live from a MIDI keyboard: messages in, messages out.

KeyRouter does the translating (no ports), so it can be tested without hardware.
"""

import mido

SUSTAIN = 64
MOD_WHEEL = 1
PASSED_CCS = {MOD_WHEEL, SUSTAIN}     # other CCs could land on the FM-1's effects


class KeyRouter:
    """Moves a keyboard's notes to one FM-1 channel, transposed and scaled.

    Remembers which note each held key produced, so the key's release frees
    that note even if the transposition is out of range or the keyboard's
    octave buttons were pressed in between (they act in the keyboard).
    """

    def __init__(self, channel: int, transpose: int = 0, velocity: float = 1.0):
        if not 1 <= channel <= 16:
            raise ValueError("channel must be 1-16")
        self.channel = channel - 1
        self.transpose = transpose
        self.velocity = velocity
        self.held: dict[tuple[int, int], int] = {}     # (in channel, in note) -> out note
        self.pedal = False

    def translate(self, msg: mido.Message) -> list[mido.Message]:
        ch = self.channel
        if msg.type == "note_on" and msg.velocity > 0:
            note = msg.note + self.transpose
            if not 0 <= note <= 127:
                return []
            out = []
            key = (msg.channel, msg.note)
            if key in self.held:                          # re-strike without release
                out.append(mido.Message("note_off", channel=ch, note=self.held[key]))
            self.held[key] = note
            vel = max(1, min(127, round(msg.velocity * self.velocity)))
            return out + [mido.Message("note_on", channel=ch, note=note, velocity=vel)]
        if msg.type in ("note_on", "note_off"):
            note = self.held.pop((msg.channel, msg.note), None)
            if note is None:
                return []
            return [mido.Message("note_off", channel=ch, note=note)]
        if msg.type == "control_change" and msg.control in PASSED_CCS:
            if msg.control == SUSTAIN:
                self.pedal = msg.value >= 64
            return [msg.copy(channel=ch)]
        if msg.type in ("pitchwheel", "aftertouch", "polytouch", "program_change"):
            if msg.type == "polytouch":
                note = msg.note + self.transpose
                return [msg.copy(channel=ch, note=note)] if 0 <= note <= 127 else []
            return [msg.copy(channel=ch)]
        return []                                         # clock, sysex, other CCs

    def release(self) -> list[mido.Message]:
        """Note-offs for everything still held, and the pedal up."""
        out = [mido.Message("note_off", channel=self.channel, note=n)
               for n in self.held.values()]
        self.held.clear()
        if self.pedal:
            out.append(mido.Message("control_change", channel=self.channel,
                                    control=SUSTAIN, value=0))
            self.pedal = False
        return out


def pick_keyboard(inputs: list[str], hint: str | None, fm1_hint: str) -> str:
    """The keyboard's input port: the one matching `hint`, else the only non-FM-1 input."""
    if hint:
        hits = [n for n in inputs if hint.lower() in n.lower()]
        if not hits:
            raise ValueError(f"no MIDI input matching {hint!r}; inputs: {inputs or 'none'}")
        return hits[0]
    others = [n for n in inputs if fm1_hint.lower() not in n.lower()]
    if len(others) == 1:
        return others[0]
    if not others:
        raise ValueError("no MIDI keyboard found; plug one in (see `fm1ctl.py ports`)")
    raise ValueError("several MIDI inputs; choose one with --keyboard NAME: "
                     + ", ".join(others))
