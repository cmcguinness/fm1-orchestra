"""Reading DX7 SysEx patch files.

A 32-voice bank (VMEM) is F0 43 0n 09 20 00, 4096 data bytes (32 voices x
128 packed bytes), a checksum and F7: 4104 bytes in all. Packed voices are
unpacked here into the 155-byte single-voice (VCED) layout that
dx7.single_voice_sysex sends.

Patch files from the internet vary in quality: values with stray high bits,
bad checksums. Every field is masked to its bit width and clamped to its legal
range, as DX7 editors such as Dexed do, so a sloppy patch can't send
out-of-range data to the FM-1.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from .dx7 import checksum

BANK_HEADER = bytes([0xF0, 0x43])
BANK_SIZE = 4104
VOICE_BYTES = 128

# Maximum legal value for each VCED byte, in VCED order.
_OP_MAX = [99, 99, 99, 99, 99, 99, 99, 99,      # EG rates, levels
           99, 99, 99, 3, 3, 7,                 # break point, depths, curves, rate scaling
           3, 7, 99, 1, 31, 99, 14]             # AMS, KVS, level, mode, coarse, fine, detune
_GLOBAL_MAX = [99, 99, 99, 99, 99, 99, 99, 99,  # pitch EG
               31, 7, 1, 99, 99, 99, 99, 1, 5, 7, 48]


@dataclass
class Patch:
    source: Path
    index: int          # 0-31 within the bank
    name: str
    vced: list[int]     # 155 bytes, ready for dx7.single_voice_sysex

    @property
    def ref(self) -> str:
        return f"{self.source.stem}:{self.index + 1}"


def _clean_name(raw: bytes) -> str:
    return "".join(chr(c) if 32 <= c < 127 else " " for c in raw).rstrip()


def unpack_voice(v: bytes) -> list[int]:
    """128-byte packed bank voice -> 155-byte VCED list."""
    if len(v) != VOICE_BYTES:
        raise ValueError("packed voice must be 128 bytes")
    out: list[int] = []
    for op in range(6):                         # stored OP6 first, as in VCED
        o = v[op * 17:(op + 1) * 17]
        out += [
            *o[0:8],                            # rates, levels
            o[8], o[9], o[10],                  # break point, left/right depth
            o[11] & 0x03, (o[11] >> 2) & 0x03,  # left curve, right curve
            o[12] & 0x07,                       # rate scaling
            o[13] & 0x03, (o[13] >> 2) & 0x07,  # amp mod sens, key velocity sens
            o[14],                              # output level
            o[15] & 0x01, (o[15] >> 1) & 0x1F,  # osc mode, coarse
            o[16],                              # fine
            (o[12] >> 3) & 0x0F,                # detune
        ]
    g = v[102:]
    out += [
        *g[0:8],                                # pitch EG
        g[8] & 0x1F,                            # algorithm
        g[9] & 0x07, (g[9] >> 3) & 0x01,        # feedback, osc key sync
        g[10], g[11], g[12], g[13],             # LFO speed, delay, PMD, AMD
        g[14] & 0x01, (g[14] >> 1) & 0x07,      # LFO key sync, wave
        (g[14] >> 4) & 0x07,                    # pitch mod sens
        g[15],                                  # transpose
    ]
    limits = _OP_MAX * 6 + _GLOBAL_MAX
    out = [min(b & 0x7F, hi) for b, hi in zip(out, limits)]
    name = [c if 32 <= c < 127 else 32 for c in v[118:128]]
    return out + name


def pack_voice(vced: list[int]) -> bytes:
    """155-byte VCED -> 128-byte packed bank voice (inverse of unpack_voice)."""
    if len(vced) != 155:
        raise ValueError("VCED must be 155 bytes")
    out: list[int] = []
    for op in range(6):
        o = vced[op * 21:(op + 1) * 21]
        out += [*o[0:11], o[11] | o[12] << 2, o[13] | o[20] << 3, o[14] | o[15] << 2,
                o[16], o[17] | o[18] << 1, o[19]]
    g = vced[126:145]
    out += [*g[0:8], g[8], g[9] | g[10] << 3, *g[11:15],
            g[15] | g[16] << 1 | g[17] << 4, g[18]]
    return bytes(out + list(vced[145:155]))


def bank_sysex(vceds: list[list[int]], channel: int = 0) -> list[int]:
    """32-voice bank dump payload (without F0/F7, as mido wants)."""
    if len(vceds) != 32:
        raise ValueError(f"a bank holds exactly 32 voices, got {len(vceds)}")
    data = b"".join(pack_voice(v) for v in vceds)
    return [0x43, channel & 0x0F, 0x09, 0x20, 0x00, *data, checksum(list(data))]


def read_bank(path: Path) -> tuple[list[Patch], list[str]]:
    """Return the bank's 32 patches and any warnings about the file."""
    raw = path.read_bytes()
    warnings: list[str] = []
    if len(raw) != BANK_SIZE or raw[:2] != BANK_HEADER or raw[3] != 0x09:
        raise ValueError(f"{path.name}: not a DX7 32-voice bank "
                         f"({len(raw)} bytes, header {raw[:4].hex(' ')})")
    data = raw[6:6 + 4096]
    if checksum(list(data)) != raw[6 + 4096]:
        warnings.append(f"{path.name}: checksum mismatch (loaded anyway)")
    patches = []
    for i in range(32):
        packed = data[i * VOICE_BYTES:(i + 1) * VOICE_BYTES]
        vced = unpack_voice(packed)
        patches.append(Patch(path, i, _clean_name(packed[118:128]), vced))
    return patches, warnings


def load_library(folder: Path) -> tuple[list[Patch], list[str]]:
    patches: list[Patch] = []
    warnings: list[str] = []
    for path in sorted(folder.glob("*.syx")):
        try:
            bank, warn = read_bank(path)
        except ValueError as exc:
            warnings.append(str(exc))
            continue
        patches += bank
        warnings += warn
    return patches, warnings


def find(patches: list[Patch], ref: str) -> Patch:
    """Look up 'bankname:N' (N = 1-32)."""
    bank, _, num = ref.rpartition(":")
    if not bank or not num.isdigit() or not 1 <= int(num) <= 32:
        raise ValueError(f"patch reference must look like BANK:N with N 1-32, got {ref!r}")
    for p in patches:
        if p.source.stem.lower() == bank.lower() and p.index == int(num) - 1:
            return p
    raise ValueError(f"no bank named {bank!r}")


# Editable fields: name -> offset within an operator's 21 VCED bytes.
OP_FIELDS = {name: i for i, name in enumerate(
    "r1 r2 r3 r4 l1 l2 l3 l4 bp ld rd lc rc rs ams kvs out mode coarse fine detune".split())}
GLOBAL_FIELDS = {
    "alg": 134, "fb": 135, "sync": 136,             # algorithm, feedback, osc key sync
    "lfo.speed": 137, "lfo.delay": 138,             # vibrato/tremolo source
    "lfo.pmd": 139, "lfo.amd": 140,                 # pitch (vibrato) and amplitude depth
    "lfo.sync": 141, "lfo.wave": 142,               # wave: 0 tri 1 saw- 2 saw+ 3 sqr 4 sine 5 S/H
    "pms": 143,                                     # pitch-mod sensitivity, 0-7
    "transpose": 144,                               # 0-48 semitones, 24 = none
}


def edit(patch: Patch, edits: list[str]) -> Patch:
    """A copy of the patch with edits like 'op1.r1=80' or 'fb=3' applied.

    Operator fields: r1-r4 / l1-l4 (envelope rates/levels), bp ld rd lc rc
    (keyboard scaling), rs (rate scaling), ams, kvs (velocity sensitivity),
    out (output level), mode, coarse, fine, detune. Globals: alg (1-32), fb,
    sync, lfo.speed, lfo.delay, lfo.pmd, lfo.amd, lfo.sync, lfo.wave, pms,
    transpose (0-48, 24 = none).
    """
    vced = list(patch.vced)
    limits = _OP_MAX * 6 + _GLOBAL_MAX
    for item in edits:
        target, eq, value_text = item.partition("=")
        if not eq or not value_text.lstrip("-").isdigit():
            raise ValueError(f"edit must look like op1.r1=80 or fb=3, got {item!r}")
        value = int(value_text)
        target = target.strip().lower()
        if target in GLOBAL_FIELDS:
            offset = GLOBAL_FIELDS[target]
            if target == "alg":
                if not 1 <= value <= 32:
                    raise ValueError("alg must be 1-32")
                value -= 1
        else:
            op, dot, field = target.partition(".")
            if (not dot or len(op) != 3 or not op.startswith("op") or op[2] not in "123456"
                    or field not in OP_FIELDS):
                raise ValueError(f"unknown field {target!r}: use opN.FIELD with N 1-6 and "
                                 f"FIELD one of {', '.join(OP_FIELDS)}, or alg/fb")
            offset = (6 - int(op[2])) * 21 + OP_FIELDS[field]   # stored OP6 first
        if not 0 <= value <= limits[offset]:
            raise ValueError(f"{target} must be 0-{limits[offset]}")
        vced[offset] = value
    return replace(patch, vced=vced)
