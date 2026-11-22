"""DX7 voice data model and SysEx encoding (the FM-1 speaks DX7 SysEx).

Reference: the DX7 single-voice (VCED) format, 155 data bytes:
  6 operators x 21 bytes, stored OP6 first, then 29 global bytes,
  then a 10-character name.
"""

from dataclasses import dataclass, field

YAMAHA_ID = 0x43


@dataclass
class Operator:
    eg_rates: tuple[int, int, int, int] = (99, 99, 99, 99)
    eg_levels: tuple[int, int, int, int] = (99, 99, 99, 0)
    kbd_break_point: int = 39          # 39 = C3 (MIDI 60)
    kbd_left_depth: int = 0
    kbd_right_depth: int = 0
    kbd_left_curve: int = 0            # 0=-LIN 1=-EXP 2=+EXP 3=+LIN
    kbd_right_curve: int = 0
    kbd_rate_scaling: int = 0          # 0-7
    amp_mod_sens: int = 0              # 0-3
    key_vel_sens: int = 0              # 0-7
    output_level: int = 0              # 0-99
    osc_mode: int = 0                  # 0 = ratio, 1 = fixed
    freq_coarse: int = 1               # 0 = 0.5x, 1..31 = 1x..31x
    freq_fine: int = 0                 # 0-99
    detune: int = 7                    # 0-14, 7 = centre

    def to_bytes(self) -> list[int]:
        return [
            *self.eg_rates, *self.eg_levels,
            self.kbd_break_point, self.kbd_left_depth, self.kbd_right_depth,
            self.kbd_left_curve, self.kbd_right_curve, self.kbd_rate_scaling,
            self.amp_mod_sens, self.key_vel_sens, self.output_level,
            self.osc_mode, self.freq_coarse, self.freq_fine, self.detune,
        ]


@dataclass
class Voice:
    name: str
    # operators[0] is OP1 ... operators[5] is OP6
    operators: list[Operator] = field(default_factory=lambda: [Operator() for _ in range(6)])
    pitch_eg_rates: tuple[int, int, int, int] = (99, 99, 99, 99)
    pitch_eg_levels: tuple[int, int, int, int] = (50, 50, 50, 50)
    algorithm: int = 1                 # 1-32, as printed on the panel
    feedback: int = 0                  # 0-7
    osc_key_sync: int = 1
    lfo_speed: int = 35
    lfo_delay: int = 0
    lfo_pitch_mod_depth: int = 0
    lfo_amp_mod_depth: int = 0
    lfo_key_sync: int = 0
    lfo_wave: int = 4                  # 0=TRI 1=SAW- 2=SAW+ 3=SQR 4=SIN 5=S/H
    pitch_mod_sens: int = 3            # 0-7
    transpose: int = 24                # 24 = no transpose (C3)

    def to_vced(self) -> list[int]:
        if len(self.operators) != 6:
            raise ValueError("a DX7 voice has exactly 6 operators")
        if not 1 <= self.algorithm <= 32:
            raise ValueError("algorithm must be 1-32")
        data: list[int] = []
        for op in reversed(self.operators):          # stored OP6 first
            data += op.to_bytes()
        data += [
            *self.pitch_eg_rates, *self.pitch_eg_levels,
            self.algorithm - 1, self.feedback, self.osc_key_sync,
            self.lfo_speed, self.lfo_delay, self.lfo_pitch_mod_depth,
            self.lfo_amp_mod_depth, self.lfo_key_sync, self.lfo_wave,
            self.pitch_mod_sens, self.transpose,
        ]
        data += [ord(c) for c in self.name[:10].ljust(10)]
        if len(data) != 155:
            raise AssertionError(f"VCED length {len(data)} != 155")
        bad = [i for i, b in enumerate(data) if not 0 <= b <= 127]
        if bad:
            raise ValueError(f"VCED bytes out of 7-bit range at offsets {bad}")
        return data


def checksum(data: list[int]) -> int:
    return (-sum(data)) & 0x7F


def single_voice_sysex(voice: Voice, channel: int = 0) -> list[int]:
    """SysEx payload (without F0/F7, as mido wants) for a single-voice dump.

    On the FM-1 this lands in the selected voice's edit buffer; it is not
    stored until SAVE is pressed on the unit.
    """
    return vced_sysex(voice.to_vced(), channel)


def vced_sysex(data: list[int], channel: int = 0) -> list[int]:
    """Single-voice dump payload from 155 raw VCED bytes."""
    if len(data) != 155:
        raise ValueError(f"VCED must be 155 bytes, got {len(data)}")
    return [YAMAHA_ID, 0x00 | (channel & 0x0F), 0x00, 0x01, 0x1B, *data, checksum(data)]


# Carrier (audible) operators for each algorithm 1-32, per the DX7 chart.
CARRIERS = {
    1: (1, 3), 2: (1, 3), 3: (1, 4), 4: (1, 4), 5: (1, 3, 5), 6: (1, 3, 5),
    7: (1, 3), 8: (1, 3), 9: (1, 3), 10: (1, 4), 11: (1, 4), 12: (1, 3),
    13: (1, 3), 14: (1, 3), 15: (1, 3), 16: (1,), 17: (1,), 18: (1,),
    19: (1, 4, 5), 20: (1, 2, 4), 21: (1, 2, 4, 5), 22: (1, 3, 4, 5),
    23: (1, 2, 4, 5), 24: (1, 2, 3, 4, 5), 25: (1, 2, 3, 4, 5), 26: (1, 2, 4),
    27: (1, 2, 4), 28: (1, 3, 6), 29: (1, 2, 3, 5), 30: (1, 2, 3, 6),
    31: (1, 2, 3, 4, 5), 32: (1, 2, 3, 4, 5, 6),
}


def drones(vced: list[int]) -> list[int]:
    """Audible operators that never fall silent after the key is released.

    A carrier whose envelope's final level (L4) is above 0 keeps sounding
    after note-off; note-offs and program changes can't stop it, only a panic
    on the unit (hold PLAY/STOP) or voice stealing. Returns their numbers.
    """
    alg = vced[134] + 1
    out = []
    for n in CARRIERS[alg]:
        op = vced[(6 - n) * 21:(7 - n) * 21]
        if op[16] > 0 and op[7] > 0:            # output level, L4
            out.append(n)
    return out
