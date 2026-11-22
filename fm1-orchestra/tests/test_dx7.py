from fm1 import dx7
from fm1.voices import VOICES


def test_every_voice_encodes_to_a_valid_single_voice_dump():
    for make in VOICES.values():
        payload = dx7.single_voice_sysex(make())
        assert payload[:5] == [0x43, 0x00, 0x00, 0x01, 0x1B]
        data, check = payload[5:-1], payload[-1]
        assert len(data) == 155
        assert (sum(data) + check) & 0x7F == 0
        assert all(0 <= b <= 127 for b in payload)


def test_layout_matches_dx7_vced_offsets():
    v = VOICES["plenum"]()
    data = v.to_vced()
    assert data[134] == 31                      # algorithm 32, stored 0-based
    assert data[135] == v.feedback
    assert data[144] == 24                      # transpose centre
    assert bytes(data[145:155]).decode() == "BACH PLENO"
    # OP6 is stored first: its coarse freq is at offset 18, OP1's at 5*21+18.
    assert data[18] == v.operators[5].freq_coarse
    assert data[5 * 21 + 18] == v.operators[0].freq_coarse
