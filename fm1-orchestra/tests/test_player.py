import mido

from fm1.player import play, release_all, schedule, select_tracks


def _file():
    f = mido.MidiFile(type=1, ticks_per_beat=100)
    conductor = mido.MidiTrack([mido.MetaMessage("set_tempo", tempo=500000, time=0),
                                mido.MetaMessage("set_tempo", tempo=1000000, time=200)])
    a = mido.MidiTrack([mido.MetaMessage("track_name", name="Celesta"),
                        mido.Message("note_on", note=80, velocity=90, time=300),
                        mido.Message("control_change", control=7, value=100, time=0),
                        mido.Message("note_off", note=80, time=100)])
    b = mido.MidiTrack([mido.MetaMessage("track_name", name="Cello"),
                        mido.Message("note_on", note=40, velocity=90, time=50),
                        mido.Message("program_change", program=3, time=0)])
    f.tracks = [conductor, a, b]
    return f


def _notes(events):
    return [(round(t, 6), "on" if m.type == "note_on" and m.velocity else "off", m.note)
            for t, m in events]


def test_select_by_name_or_number():
    f = _file()
    assert select_tracks(f, ["celesta"]) == [1]
    assert select_tracks(f, ["2", "Celesta", "1"]) == [2, 1]


def test_track_selection_keeps_tempo_and_drops_non_notes():
    f = _file()
    # 200 ticks at 0.5 s/beat + 100 ticks at 1 s/beat = 2.0 s
    assert _notes(schedule(f, tracks=[1])) == [(2.0, "on", 80), (3.0, "off", 80)]
    assert (0.25, "on", 40) in _notes(schedule(f))


def _pedal_file():
    f = mido.MidiFile(type=1, ticks_per_beat=480)      # default 120 bpm: 480 ticks = 0.5 s
    piano = mido.MidiTrack([
        mido.Message("control_change", control=64, value=127, time=0),
        mido.Message("note_on", note=60, velocity=80, time=0),
        mido.Message("note_off", note=60, time=480),       # 0.5 s, pedal down: held
        mido.Message("note_on", note=60, velocity=80, time=480),   # 1.0 s re-strike
        mido.Message("note_off", note=60, time=480),       # 1.5 s, held
        mido.Message("control_change", control=64, value=0, time=480),  # 2.0 s lift
    ])
    melody = mido.MidiTrack([
        mido.Message("note_on", note=90, velocity=60, time=0),
        mido.Message("note_off", note=90, time=480),       # 0.5 s: not pedalled
    ])
    f.tracks = [piano, melody]
    return f


def test_pedal_applies_only_to_its_own_track():
    ev = _notes(schedule(_pedal_file()))
    assert (0.5, "off", 90) in ev                          # melody releases on time
    assert (0.5, "off", 60) not in ev                      # piano held by its pedal
    assert ev.count((1.0, "off", 60)) == 1                 # re-strike: release then strike
    assert ev.index((1.0, "off", 60)) < ev.index((1.0, "on", 60))
    assert ev[-1] == (2.0, "off", 60)                      # released when pedal lifts
    assert all(m.type in ("note_on", "note_off") for _, m in schedule(_pedal_file()))


def test_no_pedal_releases_on_time():
    ev = _notes(schedule(_pedal_file(), pedal=False))
    assert (0.5, "off", 60) in ev and (1.5, "off", 60) in ev


def test_release_all_sends_every_note_off():
    class Port:
        def __init__(self): self.sent = []
        def send(self, m): self.sent.append(m)
    port = Port()
    release_all(port, [0])
    assert sum(m.type == "note_off" for m in port.sent) == 128


class _Port:
    def __init__(self): self.sent = []
    def send(self, m): self.sent.append(m)


def test_parts_route_tracks_to_their_channels():
    f = _pedal_file()                                     # track 0 piano, track 1 melody
    events = schedule(f, channels={0: 0, 1: 2})
    assert {m.channel for _, m in events if m.note == 60} == {0}
    assert {m.channel for _, m in events if m.note == 90} == {2}
    port = _Port()
    play(port, events, channel=None)
    ons = [(m.channel, m.note) for m in port.sent if m.type == "note_on"]
    assert ons == [(0, 60), (2, 90), (0, 60)]
    # cleanup releases exactly the channels that were used
    assert {m.channel for m in port.sent[-2 * 129:] if m.type == "note_off"} == {0, 2}


def test_same_pitch_on_two_parts_sounds_on_both():
    f = mido.MidiFile(type=1, ticks_per_beat=480)
    f.tracks = [mido.MidiTrack([mido.Message("note_on", note=70, velocity=80, time=0),
                                mido.Message("note_off", note=70, time=480)])
                for _ in range(2)]
    port = _Port()
    play(port, schedule(f, channels={0: 0, 1: 2}), channel=None)
    assert [(m.channel, m.note) for m in port.sent if m.type == "note_on"] == [(0, 70), (2, 70)]
