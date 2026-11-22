import math

from fm1.stems import Stem, gains, mix_filter


def test_constant_power_pan():
    assert gains(-1) == (1.0, gains(-1)[1]) and abs(gains(-1)[1]) < 1e-9
    left, right = gains(0)
    assert math.isclose(left, right) and math.isclose(left ** 2 + right ** 2, 1)
    left, right = gains(1)
    assert abs(left) < 1e-9 and math.isclose(right, 1)


def test_mix_filter_aligns_and_pans_each_stem():
    f = mix_filter([Stem("a.wav", 22050, -1.0), Stem("b.wav", 22100, 0.5)])
    assert "[0:a]atrim=start_sample=22050" in f and "[1:a]atrim=start_sample=22100" in f
    assert "c1=0.0000*c0" in f                      # hard left: nothing on the right
    assert f.endswith("[s0][s1]amix=inputs=2:normalize=0:duration=longest[out]")


def test_load_and_repan(tmp_path):
    import pytest
    from fm1.record import RecordError
    from fm1.stems import load, repan, save
    takes = [Stem(tmp_path / "01-Ostinato.wav", 100, -0.2, 1),
             Stem(tmp_path / "05-Violino_I.wav", 120, 0.0)]          # older take: no channel
    save(takes, tmp_path)
    loaded = load(tmp_path)
    assert [(s.channel, s.start) for s in loaded] == [(1, 100), (5, 120)]
    moved = repan(loaded, {1: 0.5, 5: -0.5})
    assert [s.pan for s in moved] == [0.5, -0.5] and moved[0].start == 100
    with pytest.raises(RecordError, match="05-Violino_I"):
        repan(loaded, {1: 0.0})
    with pytest.raises(RecordError, match="record them first"):
        load(tmp_path / "nowhere")
