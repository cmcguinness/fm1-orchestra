import mido
import pytest

from fm1.keys import KeyRouter, pick_keyboard


def on(note, vel=100, ch=0):
    return mido.Message("note_on", channel=ch, note=note, velocity=vel)


def off(note, ch=0):
    return mido.Message("note_off", channel=ch, note=note)


def test_moves_notes_to_the_chosen_channel_transposed():
    r = KeyRouter(channel=3, transpose=12)
    [m] = r.translate(on(60))
    assert (m.type, m.channel, m.note, m.velocity) == ("note_on", 2, 72, 100)
    [m] = r.translate(off(60))
    assert (m.type, m.channel, m.note) == ("note_off", 2, 72)


def test_release_frees_the_note_it_started_even_if_transpose_changed():
    r = KeyRouter(channel=1)
    r.translate(on(60))
    r.transpose = 5
    [m] = r.translate(off(60))
    assert m.note == 60


def test_velocity_zero_note_on_is_a_release():
    r = KeyRouter(channel=1)
    r.translate(on(60))
    [m] = r.translate(on(60, vel=0))
    assert m.type == "note_off"


def test_velocity_scaled_and_clamped():
    r = KeyRouter(channel=1, velocity=2.0)
    assert r.translate(on(60, vel=100))[0].velocity == 127
    r = KeyRouter(channel=1, velocity=0.01)
    assert r.translate(on(61, vel=10))[0].velocity == 1


def test_out_of_range_notes_dropped_and_their_release_ignored():
    r = KeyRouter(channel=1, transpose=24)
    assert r.translate(on(120)) == []
    assert r.translate(off(120)) == []


def test_only_safe_ccs_pass():
    r = KeyRouter(channel=2)
    pedal = r.translate(mido.Message("control_change", control=64, value=127))
    assert pedal[0].channel == 1
    assert r.translate(mido.Message("control_change", control=74, value=10)) == []
    assert r.translate(mido.Message("clock")) == []


def test_release_lets_go_of_held_notes_and_pedal():
    r = KeyRouter(channel=1)
    r.translate(on(60))
    r.translate(on(64))
    r.translate(mido.Message("control_change", control=64, value=127))
    out = r.release()
    assert sorted(m.note for m in out if m.type == "note_off") == [60, 64]
    assert any(m.type == "control_change" and m.value == 0 for m in out)
    assert r.release() == []


def test_pick_keyboard():
    inputs = ["LPK25", "FM-1", "Logic Pro Virtual Out"]
    assert pick_keyboard(inputs, "lpk", "FM-1") == "LPK25"
    assert pick_keyboard(["LPK25", "FM-1"], None, "FM-1") == "LPK25"
    with pytest.raises(ValueError, match="--keyboard"):
        pick_keyboard(inputs, None, "FM-1")
    with pytest.raises(ValueError, match="no MIDI input"):
        pick_keyboard(inputs, "oxygen", "FM-1")
