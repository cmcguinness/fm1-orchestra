import pytest

from fm1.effects import cc_numbers, effect_messages, parse_identity

V15_REPLY = bytes.fromhex(
    "f0 00 32 45 58 01 00 00 23 4d 5a 44 79 05 26 4c 1a 00 00 00 00 00 00 00"
    " 00 00 00 00 00 00 00 00 00 00 00 00 00 00 20 06 f7")


def test_parse_identity_reads_firmware_name():
    assert parse_identity(V15_REPLY) == "FM-1_015"
    assert parse_identity(b"\xf0\x7e\x00\xf7") is None


def test_reverb_cc_map_per_firmware():
    assert cc_numbers(15, "reverb") == [4, 5, 6, 7]
    assert cc_numbers(16, "reverb") == [74, 75, 76, 77]
    assert cc_numbers(15, "phaser") == [20, 21, 22, 23]


def test_effect_messages():
    msgs = effect_messages(15, "reverb", space=1, decay=80, mix=35)
    assert [(m.control, m.value) for m in msgs] == [(4, 127), (5, 1), (6, 80), (7, 35)]
    assert [(m.control, m.value) for m in effect_messages(15, "reverb", on=False)] == [(4, 0)]
    with pytest.raises(ValueError):
        effect_messages(15, "reverb", size=3)
    with pytest.raises(ValueError):
        effect_messages(15, "reverb", mix=101)
