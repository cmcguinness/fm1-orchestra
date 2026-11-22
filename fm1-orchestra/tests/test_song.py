import mido
import pytest

from fm1 import bank as bank_mod
from fm1 import song as song_mod

BANK = bank_mod.Manifest("D", ["celesta"] + [None] * 31)


def _write(tmp_path, body):
    midi = mido.MidiFile(type=1, ticks_per_beat=480)
    midi.tracks = [
        mido.MidiTrack([mido.MetaMessage("track_name", name="Piano"),
                        mido.Message("note_on", note=60, velocity=40, time=0),
                        mido.Message("note_off", note=60, time=480)]),
        mido.MidiTrack([mido.MetaMessage("track_name", name="Glass"),
                        mido.Message("note_on", note=84, velocity=40, time=0),
                        mido.Message("note_off", note=84, time=480)]),
    ]
    midi.save(tmp_path / "tune.mid")
    path = tmp_path / "tune.py"
    path.write_text("from fm1.song import Part, Reverb, Song\n" + body)
    return path


GOOD = """
SONG = Song(parts=[
    Part(channel=1, sound="celesta", tracks=["Piano"], velocity=0.5),
    Part(channel=3, tracks=["Glass"], velocity=2.0),
], reverb=Reverb("hall", mix=25))
"""


def test_module_loads_and_routes_parts(tmp_path):
    path = _write(tmp_path, GOOD)
    song, module = song_mod.load_module(path)
    assert song.title == "tune" and song.midi_path == (tmp_path / "tune.mid").resolve()
    session = song_mod.Session(song, library=lambda: [], module=module, bank=BANK)
    ons = [(m.channel, m.note, m.velocity) for _, m in session.events()
           if m.type == "note_on"]
    assert ons == [(0, 60, 20), (2, 84, 80)]
    assert session.sounds[0].label == "CELESTA" and session.sounds[1] is None


def test_song_folders_are_found_by_name(tmp_path):
    folder = tmp_path / "tune"
    folder.mkdir()
    path = _write(folder, GOOD)                 # songs/tune/tune.py + tune.mid
    (tmp_path / "empty").mkdir()                # a song folder with no module yet
    (folder / "tune-slides.py").write_text("SLIDES = []\n")
    assert song_mod.song_files(tmp_path) == [path]
    assert song_mod.song_path(tmp_path, "tune") == path
    assert song_mod.find_for_midi(folder, folder / "tune.mid") == path
    assert song_mod.find_for_midi(tmp_path / "empty", tmp_path / "empty" / "x.mid") is None


@pytest.mark.parametrize("parts, message", [
    ('Part(channel=16, tracks=["Piano"])', "effect channel"),
    ('Part(channel=1, tracks=["Piano"]), Part(channel=1, tracks=["Glass"])', "two parts"),
    ('Part(channel=1, tracks=["Piano"]), Part(channel=2, tracks=["Pia"])', "track 0"),
    ('Part(channel=1, tracks=["Nope"])', "no track"),
    ('Part(channel=1, sound="banjo", tracks=["Piano"])', "unknown sound"),
])
def test_bad_songs_fail_before_any_midi(tmp_path, parts, message):
    path = _write(tmp_path, f'SONG = Song(parts=[{parts}])\n')
    song, module = song_mod.load_module(path)
    with pytest.raises(ValueError, match=message):
        song_mod.Session(song, library=lambda: [], module=module, bank=BANK)


def test_custom_perform_takes_over(tmp_path):
    path = _write(tmp_path, GOOD + """
calls = []
def perform(session):
    calls.append(len(session.events()))
""")
    song, module = song_mod.load_module(path)
    session = song_mod.Session(song, library=lambda: [], module=module, bank=BANK)
    session.perform(start=0.0)
    assert module.calls == [4]


def test_setup_picks_sounds_by_program_change(tmp_path):
    song, module = song_mod.load_module(_write(tmp_path, GOOD.replace(', reverb=Reverb("hall", mix=25)', "")))
    session = song_mod.Session(song, library=lambda: [], module=module, bank=BANK)

    class Port:
        sent = []
        def send(self, m): self.sent.append(m)
    session.out = Port()
    session.setup()
    sent = [(m.type, m.channel, getattr(m, "program", None) or getattr(m, "value", None))
            for m in Port.sent]
    assert sent == [("control_change", 0, 127), ("program_change", 0, 96),
                    ("control_change", 2, 127)]


def test_sound_missing_from_bank_is_refused(tmp_path):
    song, module = song_mod.load_module(_write(tmp_path, GOOD))
    with pytest.raises(ValueError, match="load-bank"):
        song_mod.Session(song, library=lambda: [], module=module,
                         bank=bank_mod.Manifest("D", [None] * 32))


def test_bank_plan_keeps_existing_slots(tmp_path):
    first = bank_mod.plan(["a", "b", "c"], "D", None)
    assert first.slots[:3] == ["a", "b", "c"]
    second = bank_mod.plan(["c", "d"], "D", first)      # a and b dropped, d added
    assert second.slots[:3] == ["d", None, "c"]
    assert second.program("c") == 96 + 2
    path = tmp_path / "m.json"
    second.save(path)
    assert bank_mod.Manifest.load(path).slots == second.slots
    with pytest.raises(ValueError):
        bank_mod.plan([str(i) for i in range(33)], "D", None)


def test_sound_key_is_canonical():
    assert song_mod.sound_key("DXOC12:21", {"op1.r1": "80"}) == "dxoc12:21,op1.r1=80"


def test_part_transpose_shifts_only_that_part(tmp_path):
    body = GOOD.replace('Part(channel=3, tracks=["Glass"], velocity=2.0)',
                        'Part(channel=3, tracks=["Glass"], transpose=-12)')
    song, module = song_mod.load_module(_write(tmp_path, body))
    session = song_mod.Session(song, library=lambda: [], module=module, bank=BANK)
    notes = sorted((m.channel, m.note) for _, m in session.events())
    assert notes == [(0, 60), (0, 60), (2, 72), (2, 72)]


def test_humanize_keeps_phrase_lengths_and_note_order():
    from fm1.humanize import Humanize, apply, phrase_bounds, warp_time
    bounds = phrase_bounds([0.0, 0.5, 1.0, 4.0, 4.5], gap=1.5, end=8.0)
    assert bounds == [0.0, 4.0, 8.0]
    ts = [i / 100 for i in range(801)]
    warped = [warp_time(t, bounds, 0.3, 0.0) for t in ts]
    assert all(b >= a for a, b in zip(warped, warped[1:]))          # monotonic
    assert warp_time(4.0, bounds, 0.3, 0.0) == pytest.approx(4.0)    # phrase length kept
    assert warp_time(2.0, bounds, 0.3, 0.0) == pytest.approx(2.0)    # arch is symmetric
    assert warp_time(1.0, bounds, 0.3, 0.0) > 1.0                    # broad start
    assert warp_time(5.0, bounds, 0.0, 0.25) == pytest.approx(5.25)  # one breath
    ev = [(0.0, mido.Message("note_on", note=60, velocity=60)),
          (0.01, mido.Message("note_off", note=60))]
    out = apply(ev, Humanize(rubato=0.2, jitter_ms=30, velocity=0.2, seed=3), [])
    assert [m.type for _, m in out] == ["note_on", "note_off"]
    assert out[1][0] >= out[0][0]


def test_shape_voices_figures_by_pitch(tmp_path):
    midi = mido.MidiFile(type=1, ticks_per_beat=480)       # 0.5 s per beat
    notes = [60, 64, 67, 72]
    track = mido.MidiTrack([mido.MetaMessage("track_name", name="Piano")])
    for n in notes:
        track += [mido.Message("note_on", note=n, velocity=60, time=0),
                  mido.Message("note_off", note=n, time=96)]           # 0.1 s apart
    midi.tracks = [track]
    midi.save(tmp_path / "arp.mid")
    path = tmp_path / "arp.py"
    path.write_text("from fm1.song import Part, Song\n"
                    'SONG = Song(parts=[Part(channel=1, tracks=["Piano"], shape=0.25)])\n')
    song, module = song_mod.load_module(path)
    session = song_mod.Session(song, library=lambda: [], module=module, bank=BANK)
    vel = [m.velocity for _, m in session.events() if m.type == "note_on"]
    assert vel == [45, 55, 63, 75]                       # bottom -25%, top +25%
    later = [m.velocity for _, m in session.events(start=0.15) if m.type == "note_on"]
    assert later == [63, 75]                             # same shaping mid-piece


def _metric_file(tmp_path):
    midi = mido.MidiFile(type=1, ticks_per_beat=480)       # 120 bpm: a beat is 0.5 s
    track = mido.MidiTrack([mido.MetaMessage("track_name", name="Line"),
                            mido.MetaMessage("time_signature", numerator=2, denominator=4)])
    for _ in range(4):                                     # four eighths in a 2/4 bar
        track += [mido.Message("note_on", note=72, velocity=100, time=0),
                  mido.Message("note_off", note=72, time=240)]
    midi.tracks = [track]
    midi.save(tmp_path / "metric.mid")
    return tmp_path / "metric.mid"


def test_accents_follow_the_metre_and_articulation_detaches(tmp_path):
    _metric_file(tmp_path)
    (tmp_path / "metric.py").write_text(
        "from fm1.song import Part, Song\n"
        'SONG = Song(parts=[Part(channel=1, tracks=["Line"], accent=0.2, articulation=0.5)])\n')
    song, module = song_mod.load_module(tmp_path / "metric.py")
    session = song_mod.Session(song, library=lambda: [], module=module, bank=BANK)
    ev = session.events()
    vel = [m.velocity for _, m in ev if m.type == "note_on"]
    assert vel == [120, 100, 110, 100]          # downbeat, offbeat, beat 2, offbeat
    ons = [t for t, m in ev if m.type == "note_on"]
    offs = [t for t, m in ev if m.type == "note_off"]
    assert offs[0] == pytest.approx(ons[0] + 0.125)   # an eighth (0.25 s) played at half length
    assert all(off > on for on, off in zip(ons, offs))
    later = [m.velocity for _, m in session.events(start=0.5) if m.type == "note_on"]
    assert later == [110, 100]                  # metric position kept mid-piece


def test_articulation_keeps_releases_after_starts():
    from fm1.articulate import articulate, MIN_NOTE
    ev = [(0.0, mido.Message("note_on", note=60, velocity=90)),
          (0.01, mido.Message("note_off", note=60)),
          (0.01, mido.Message("note_on", note=60, velocity=90)),
          (0.5, mido.Message("note_off", note=60))]
    out = articulate(ev, {0: 0.3})
    kinds = [m.type for _, m in out]
    assert kinds == ["note_on", "note_off", "note_on", "note_off"]   # the re-strike survives
    assert out[1][0] == pytest.approx(0.01)          # a short note is never lengthened
    assert out[3][0] == pytest.approx(0.01 + 0.49 * 0.3)
    assert sorted(t for t, _ in out) == [t for t, _ in out]


def test_pan_is_validated_and_described(tmp_path):
    _metric_file(tmp_path)
    (tmp_path / "bad.py").write_text(
        "from fm1.song import Part, Song\n"
        'SONG = Song(parts=[Part(channel=1, tracks=["Line"], pan=1.5)])\n')
    song, module = song_mod.load_module(tmp_path / "bad.py")
    song.midi = "metric.mid"
    with pytest.raises(ValueError, match="pan"):
        song_mod.Session(song, library=lambda: [], module=module, bank=BANK)
    song.parts[0].pan = -0.5
    session = song_mod.Session(song, library=lambda: [], module=module, bank=BANK)
    assert "pan -0.5" in session.describe()[0]
