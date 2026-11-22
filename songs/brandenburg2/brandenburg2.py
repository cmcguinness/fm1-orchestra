"""Bach, Brandenburg Concerto No. 2 in F, BWV 1047, III. Allegro assai,
in the manner of the theme of William F. Buckley's "Firing Line".

brandenburg2.mid is Mutopia's public-domain edition (Andy Vaught, from the
Bach-Gesellschaft, Mutopia-2009/06/13-1680): its LilyPond MIDI for movement
III, with tracks named and the tempo set to 100 quarters a minute (the MIDI
had a placeholder 60 and no dynamics; every note is velocity 127).

Mutopia's trumpet part is coded `\\transposition f` (a fifth down) where
Bach's clarino in F sounds a fourth up, so its MIDI trumpet is an octave
low; transpose=12 puts it back up to the famous high F.

Which recording Firing Line used isn't documented, so "in the manner of" means
its well-known character: bright trumpet out front, brisk and crisp, and
real orchestral colours, not the Moog colours of brandenburg3.py.

On the FM-1: Voice1-8 on MIDI Ch 1-8, Effect Ch 16, song bank loaded.
"""

from fm1.song import Part, Reverb, Song

# The trumpet: TRUMPET 7 (brass3:19), reworked by ear over four rounds. The
# original buzzed (feedback 7), went shrill up at Bach's high F (no keyboard
# scaling), and swelled into each note instead of tonguing it. Fixes: less
# feedback, modulators easing off above A5, a softer attack blip, and
# envelopes that hit then soften ("A1 is pretty good"). Velocity 65%, since
# the MIDI has no dynamics (every note 127) and velocity drives brightness.
# A1 made it quiet ("why is the volume so low"): carrier up to 99 and sustain
# levels up 3; the other parts sit lower so the trumpet leads, as on the show.
TRUMPET = "brass3:19"
TRUMPET_EDITS = {
    "fb": 4, "op6.out": 60, "op1.out": 99,
    "op2.bp": 60, "op2.rc": 1, "op2.rd": 50,
    "op3.bp": 60, "op3.rc": 1, "op3.rd": 50,
    "op4.bp": 60, "op4.rc": 1, "op4.rd": 50,
    "op1.l1": 99, "op1.l2": 93, "op1.l3": 91, "op1.r2": 60,
    "op2.l1": 99, "op2.l2": 88, "op2.l3": 84, "op2.r2": 55,
    "op3.l1": 99, "op3.l2": 86, "op3.l3": 82, "op3.r2": 55,
    # Vibrato, as a real trumpet's (picked V3 of three): quick, early, sine,
    # with the patch's tremolo removed.
    "lfo.wave": 4, "lfo.amd": 0, "pms": 3,
    "lfo.speed": 40, "lfo.delay": 10, "lfo.pmd": 10,
    # "Sounds like hitting metal at the start": op5, which modulates the
    # carrier, ran at an inharmonic 3.18 and peaked at note-on. Tuned to 3,
    # its burst cut to 75, and the op6 blip on it removed (M3). With the
    # unit's Attack raised from 0% to 10% on the panel: "tapping gone!"
    "op5.fine": 0, "op6.fine": 0, "op5.l1": 75, "op6.out": 0,
    # Slower attacks in place of the panel's ENV Attack 10% (which MIDI can't
    # set and bank loads don't keep): every operator's R1 down 26, the carrier
    # (op1) down further, to 40. Picked as "option 3 is it" (S5).
    "op1.r1": 40, "op2.r1": 61, "op3.r1": 51, "op4.r1": 40, "op5.r1": 22, "op6.r1": 51,
}

# Feel ("super synthy, not very real"): the MIDI has every note at 127 and
# full length. Players lean into strong beats and detach notes, basses most.
# Velocities start at 75% so accents have room; timing is never touched.
FEEL = {"accent": 0.2, "vary": 0.04}

# Solo violin kept as SOLOVIOLIN (it beat three alternatives).
# Violins: VIOLINS A (DX5 factory), picked from nine string patches on
# Violin I alone; reworks with more vibrato or a quicker bow lost to the original.
# Strings, Switched-On style. Real-string patches were tried at length (the
# best: SOLOVIOLIN, VIOLINS A, VIOLA SECN, CELLOS 1A) but never sounded like
# strings, so, as in brandenburg3.py, the strings are Moog sounds instead:
# MOOG ROGUE with its roll-off removed, an octave up (it sounds an octave
# low), for the violins; rounder MOOGER for viola and bass.
ROGUE, ROGUE_EDITS = "dxoc14:8", {"op4.rd": 0, "op5.rd": 0}
MOOGER = "mike2:4"

# Seating ("pan the voices for an 'in the chamber' feel"), as heard from the
# audience: concertino in front, solo violin left, trumpet right of centre;
# ripieno violins left, viola and bass right. Pan is applied only by
# `song brandenburg2 --record FILE --stems` (the FM-1 ignores MIDI pan).
SONG = Song(
    title="Brandenburg Concerto No. 2, III (Firing Line)",
    parts=[
        Part(channel=1, sound=TRUMPET, edits=TRUMPET_EDITS, tracks=["Tromba"],
             transpose=12, velocity=0.65, articulation=0.8, **FEEL, pan=0.3),
        # Recorder: SOFT FLUTE. RECORDERS (full-depth tremolo, no high-note
        # roll-off) was "very shrill" up at E6-G6; picked from five.
        Part(channel=2, sound="church:15", tracks=["Flauto"], expression=127,  # 100 "too soft"
             velocity=0.75, articulation=0.8, **FEEL, pan=-0.2),                  # SOFT FLUTE
        Part(channel=3, sound="rom2a:3", tracks=["Oboe"], expression=100,
             velocity=0.75, articulation=0.8, **FEEL, pan=0.1),                  # OBOE
        Part(channel=4, sound=ROGUE, edits=ROGUE_EDITS, tracks=["Violino (solo)"],
             expression=100, transpose=12, velocity=0.75, articulation=0.75, **FEEL, pan=-0.45),
        Part(channel=5, sound=ROGUE, edits=ROGUE_EDITS, tracks=["5"], expression=75,
             transpose=12, velocity=0.75, articulation=0.7, **FEEL, pan=-0.75),   # Violino I
        Part(channel=6, sound=ROGUE, edits=ROGUE_EDITS, tracks=["6"], expression=75,
             transpose=12, velocity=0.75, articulation=0.7, **FEEL, pan=-0.35),   # Violino II
        Part(channel=7, sound=MOOGER, tracks=["Viola"], expression=75,
             velocity=0.75, articulation=0.7, **FEEL, pan=0.45),
        Part(channel=8, sound=MOOGER, tracks=["Violone", "Violoncello"], expression=35,
             velocity=0.75, articulation=0.6, **FEEL, pan=0.7),                 # continuo; 50 "too loud"
    ],
    reverb=Reverb("room", decay=30, mix=5),
)
