"""Hand-built voices.

The organs use algorithm 32 (six parallel carriers, no modulation), which turns
the DX7 into a six-drawbar additive organ: each operator is one pipe rank,
and its frequency ratio is the footage (ratio 0.5 = 16', 1 = 8', 2 = 4',
3 = 2 2/3', 4 = 2', 6 = 1 1/3').
"""

from .dx7 import Operator, Voice

# Pipe-organ amplitude envelope: quick but not instant speech, full sustain,
# a short release so fast passages stay clean.
_PIPE_RATES = (80, 99, 99, 60)
_PIPE_LEVELS = (99, 99, 99, 0)


def _rank(coarse: int, level: int, detune: int = 7, tame_top: int = 0) -> Operator:
    return Operator(
        eg_rates=_PIPE_RATES,
        eg_levels=_PIPE_LEVELS,
        output_level=level,
        freq_coarse=coarse,
        detune=detune,
        # Roll off the upper ranks as you go up the keyboard so the
        # treble doesn't get shrill.
        kbd_break_point=39,
        kbd_right_depth=tame_top,
        kbd_right_curve=0,
    )


def organ_plenum() -> Voice:
    """Full organ: 16' 8' 4' 2 2/3' 2' 1 1/3', for the Toccata."""
    return Voice(
        name="BACH PLENO",
        algorithm=32,
        feedback=2,            # OP6 self-feedback adds a little reedy edge
        operators=[
            _rank(1, 99),                    # OP1  8'  principal
            _rank(2, 88, detune=8),          # OP2  4'  octave
            _rank(0, 84),                    # OP3 16'  bourdon
            _rank(3, 76, detune=6, tame_top=15),   # OP4 2 2/3' quint
            _rank(4, 80, detune=8, tame_top=20),   # OP5 2'  super-octave
            _rank(6, 68, tame_top=30),       # OP6 1 1/3' mixture
        ],
        lfo_pitch_mod_depth=0,
    )


def organ_flute() -> Voice:
    """Soft flutes 8' + 4' with a gentle tremulant."""
    voice = Voice(
        name="FLUTE 8+4 ",
        algorithm=32,
        feedback=0,
        operators=[
            _rank(1, 99),
            _rank(2, 80, detune=8),
            _rank(1, 0),
            _rank(1, 0),
            _rank(1, 0),
            _rank(1, 0),
        ],
        lfo_speed=30,
        lfo_amp_mod_depth=12,
        lfo_wave=0,
    )
    # The LFO tremulant only reaches operators with amp-mod sensitivity.
    for op in voice.operators[:2]:
        op.amp_mod_sens = 1
    return voice


def celesta() -> Voice:
    """Celesta: struck steel bars over wooden resonators, for the Sugar Plum Fairy.

    Algorithm 5, three two-operator stacks:
      OP2->OP1  the body: a bright strike that mellows to a near-sine tone
      OP4->OP3  the 'ping': two octaves up, gone in a fraction of a second
      OP6->OP5  the shimmer: an octave up, slightly detuned so it beats
    Every part decays even while the key is held (L3 = 0), like a struck bar,
    and decays faster up the keyboard (rate scaling), as real bars do. The
    celesta part lives at D5-C8, so the upper partials are rolled off
    hard above A5 to keep them from turning harsh.
    """
    top = dict(kbd_break_point=60, kbd_right_curve=1)       # 60 = A5, -EXP
    return Voice(
        name="CELESTA   ",
        algorithm=5,
        feedback=0,
        operators=[
            # OP1 body carrier
            Operator(eg_rates=(99, 32, 22, 45), eg_levels=(99, 78, 0, 0),
                     output_level=93, freq_coarse=1, key_vel_sens=2,
                     kbd_rate_scaling=2),
            # OP2 body modulator: brightness that fades
            Operator(eg_rates=(99, 58, 30, 50), eg_levels=(99, 45, 0, 0),
                     output_level=52, freq_coarse=1, key_vel_sens=3,
                     kbd_rate_scaling=2, kbd_right_depth=40, **top),
            # OP3 ping carrier
            Operator(eg_rates=(99, 72, 40, 60), eg_levels=(99, 20, 0, 0),
                     output_level=56, freq_coarse=4, key_vel_sens=3,
                     kbd_rate_scaling=3, kbd_right_depth=55, **top),
            # OP4 ping modulator
            Operator(eg_rates=(99, 85, 50, 60), eg_levels=(99, 0, 0, 0),
                     output_level=36, freq_coarse=3, key_vel_sens=3,
                     kbd_rate_scaling=3, kbd_right_depth=60, **top),
            # OP5 shimmer carrier
            Operator(eg_rates=(99, 40, 25, 50), eg_levels=(99, 60, 0, 0),
                     output_level=66, freq_coarse=2, detune=9, key_vel_sens=2,
                     kbd_rate_scaling=2, kbd_right_depth=35, **top),
            # OP6 shimmer modulator
            Operator(eg_rates=(99, 70, 40, 60), eg_levels=(99, 10, 0, 0),
                     output_level=28, freq_coarse=7, key_vel_sens=3,
                     kbd_rate_scaling=3, kbd_right_depth=60, **top),
        ],
    )


def grand_piano() -> Voice:
    """Acoustic grand, as far as FM allows; tuned for quiet, pedalled music.

    Algorithm 5, three two-operator stacks:
      OP2->OP1  the string: brightness decays faster than loudness, as on a
                real piano, and depends strongly on how hard the key is hit
      OP4->OP3  a second string, slightly detuned, for the slow beating of a
                piano's unison strings
      OP6->OP5  the hammer: a short noisy knock (OP6 feedback) at the attack
    Decay is long while the key is held and shortens up the keyboard;
    releasing the key damps the note fairly quickly, like the dampers do.
    """
    bright_bass = dict(kbd_break_point=48, kbd_right_curve=1, kbd_right_depth=30)  # 48 = A3
    return Voice(
        name="GRAND PNO ",
        algorithm=5,
        feedback=5,
        operators=[
            # OP1 string carrier
            Operator(eg_rates=(99, 45, 18, 52), eg_levels=(99, 82, 0, 0),
                     output_level=97, freq_coarse=1, key_vel_sens=3,
                     kbd_rate_scaling=3),
            # OP2 string modulator: the tone colour
            Operator(eg_rates=(99, 40, 22, 55), eg_levels=(99, 60, 0, 0),
                     output_level=70, freq_coarse=1, key_vel_sens=6,
                     kbd_rate_scaling=3, **bright_bass),
            # OP3 second-string carrier, detuned against OP1
            Operator(eg_rates=(99, 45, 18, 52), eg_levels=(99, 80, 0, 0),
                     output_level=88, freq_coarse=1, detune=9, key_vel_sens=3,
                     kbd_rate_scaling=3),
            # OP4 second-string modulator, an octave up for extra overtones
            Operator(eg_rates=(99, 55, 25, 55), eg_levels=(99, 40, 0, 0),
                     output_level=55, freq_coarse=2, key_vel_sens=6,
                     kbd_rate_scaling=3, **bright_bass),
            # OP5 hammer carrier
            Operator(eg_rates=(99, 85, 60, 70), eg_levels=(99, 0, 0, 0),
                     output_level=60, freq_coarse=1, key_vel_sens=5,
                     kbd_rate_scaling=4),
            # OP6 hammer modulator with feedback: the knock
            Operator(eg_rates=(99, 90, 70, 70), eg_levels=(99, 0, 0, 0),
                     output_level=66, freq_coarse=5, key_vel_sens=5,
                     kbd_rate_scaling=4),
        ],
    )


def electric_piano() -> Voice:
    """Tine electric piano in the Rhodes manner, the sound DX7 FM does best.

    Algorithm 5, three two-operator stacks:
      OP2->OP1  the body: round, with more growl the harder you play
      OP4->OP3  the tine: a 14x modulator gives the glassy 'ding' at the
                attack and dies within a fraction of a second
      OP6->OP5  warmth: a detuned, lightly fed-back layer that fills out the tone
    """
    tame = dict(kbd_break_point=55, kbd_right_curve=1)       # 55 = E5
    return Voice(
        name="TINE EP   ",
        algorithm=5,
        feedback=3,
        operators=[
            # OP1 body carrier
            Operator(eg_rates=(96, 28, 22, 60), eg_levels=(99, 80, 0, 0),
                     output_level=99, freq_coarse=1, key_vel_sens=2,
                     kbd_rate_scaling=3),
            # OP2 body modulator: growl on hard hits
            Operator(eg_rates=(95, 45, 30, 65), eg_levels=(99, 65, 0, 0),
                     output_level=58, freq_coarse=1, key_vel_sens=6,
                     kbd_rate_scaling=3, kbd_right_depth=25, **tame),
            # OP3 tine carrier
            Operator(eg_rates=(96, 30, 22, 60), eg_levels=(99, 78, 0, 0),
                     output_level=86, freq_coarse=1, detune=8, key_vel_sens=2,
                     kbd_rate_scaling=3),
            # OP4 tine modulator: the 'ding'
            Operator(eg_rates=(99, 70, 40, 70), eg_levels=(99, 0, 0, 0),
                     output_level=60, freq_coarse=14, key_vel_sens=5,
                     kbd_rate_scaling=4, kbd_right_depth=50, **tame),
            # OP5 warmth carrier
            Operator(eg_rates=(96, 30, 22, 60), eg_levels=(99, 75, 0, 0),
                     output_level=72, freq_coarse=1, detune=6, key_vel_sens=2,
                     kbd_rate_scaling=3),
            # OP6 warmth modulator with feedback
            Operator(eg_rates=(95, 50, 30, 65), eg_levels=(99, 55, 0, 0),
                     output_level=40, freq_coarse=1, key_vel_sens=4,
                     kbd_rate_scaling=3, kbd_right_depth=30, **tame),
        ],
    )


VOICES = {
    "plenum": organ_plenum,
    "flute": organ_flute,
    "celesta": celesta,
    "piano": grand_piano,
    "epiano": electric_piano,
}
