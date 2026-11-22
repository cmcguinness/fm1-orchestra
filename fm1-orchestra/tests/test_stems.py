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
