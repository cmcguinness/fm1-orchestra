from pathlib import Path

import pytest

from fm1 import dx7
from fm1.syx import bank_sysex, find, pack_voice, read_bank, unpack_voice

ROM1A = Path(__file__).parent.parent / "sysex" / "rom1a.syx"


def test_unpack_inverts_pack_for_built_in_voices():
    from fm1.voices import VOICES
    for make in VOICES.values():
        vced = make().to_vced()
        assert unpack_voice(pack_voice(vced)) == vced


def test_unpack_clamps_garbage():
    vced = unpack_voice(bytes([0x7F] * 128))
    assert vced[134] == 31 and vced[144] == 48         # algorithm, transpose clamped
    assert all(0 <= b <= 99 for b in vced[:145])


@pytest.mark.skipif(not ROM1A.exists(), reason="patch library not present")
def test_factory_e_piano_unpacks_to_known_values():
    bank, warnings = read_bank(ROM1A)
    assert not warnings
    ep = find(bank, "rom1a:11")
    assert ep.name == "E.PIANO 1"
    assert ep.vced[134] + 1 == 5 and ep.vced[135] == 6   # algorithm 5, feedback 6
    assert ep.vced[4 * 21 + 18] == 14                     # OP2 ratio 14 (stored 5th)
    assert len(dx7.vced_sysex(ep.vced)) == 161


def test_edit_sets_operator_and_global_fields():
    import pytest
    from fm1.syx import Patch, edit
    from pathlib import Path
    p = Patch(Path("x.syx"), 0, "X", [0] * 155)
    e = edit(p, ["op1.r1=80", "op6.coarse=3", "alg=5", "fb=7"])
    assert e.vced[5 * 21 + 0] == 80          # OP1 is stored last
    assert e.vced[0 * 21 + 18] == 3          # OP6 first
    assert e.vced[134] == 4 and e.vced[135] == 7
    assert p.vced[5 * 21] == 0               # original untouched
    for bad in (["op1.r1=100"], ["op7.r1=1"], ["op1.zz=1"], ["fb=8"], ["op1.r1"]):
        with pytest.raises(ValueError):
            edit(p, bad)


def test_bank_sysex_round_trips_through_read_bank(tmp_path):
    patches, _ = read_bank(ROM1A)
    payload = bank_sysex([p.vced for p in patches])
    path = tmp_path / "out.syx"
    path.write_bytes(bytes([0xF0, *payload, 0xF7]))
    again, warnings = read_bank(path)
    assert not warnings
    assert [p.vced for p in again] == [p.vced for p in patches]


def test_drone_detection_and_fix():
    from fm1.dx7 import drones
    lib = [p for p in read_bank(Path(__file__).parent.parent / "sysex" / "dxmik2.syx")[0]]
    glass1 = find(lib, "dxmik2:24")
    assert drones(glass1.vced) == [3]
    from fm1.syx import edit
    assert drones(edit(glass1, ["op3.l4=0"]).vced) == []
    from fm1.voices import VOICES
    assert all(drones(make().to_vced()) == [] for make in VOICES.values())


def test_edit_sets_lfo_fields():
    from fm1.syx import Patch, edit
    p = Patch(Path("x.syx"), 0, "X", [0] * 155)
    e = edit(p, ["lfo.speed=34", "lfo.delay=30", "lfo.pmd=10", "lfo.amd=0", "lfo.wave=4", "pms=3"])
    assert e.vced[137:144] == [34, 30, 10, 0, 0, 4, 3]
    with pytest.raises(ValueError):
        edit(p, ["lfo.wave=6"])
