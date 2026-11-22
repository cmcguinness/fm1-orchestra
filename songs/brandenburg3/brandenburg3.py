"""Bach, Brandenburg Concerto No. 3 in G, BWV 1048, first movement,
after Wendy Carlos's Switched-On Bach (1968).

brandenburg3.mid is generated from a corrected optical reading of Chris
Sawer's Mutopia edition (CC BY 3.0, IMSLP #57477; the PDF footer says public
domain); see CREDITS.md and score/bwv1048-1-corrections.md:

    fm1ctl.py import-score songs/brandenburg3/score/bwv1048-1.musicxml \\
        songs/brandenburg3/brandenburg3.mid --bpm 100

The score says only Allegro; 100 quarters a minute is our choice. (The first
version of this arrangement used a Kunst der Fuge sequence, which is licensed
for personal use only; keep it as local/brandenburg3/brandenburg3-kunstderfuge.mid if
you have it, for fm1-orchestra/tools/compare_omr.py.)

Carlos played each line separately on a Moog, each with its own timbre, and
kept it fairly dry. Here two Moog-style patches (picked by ear from a
15-patch audition) alternate across neighbouring lines so they stay
distinct. The three cellos play the same notes ~90% of the time, so they
share a part; that makes eight parts, the FM-1's maximum. Tracks: 1-3
violins, 4-6 violas, 7-9 cellos, 10 continuo.

On the FM-1: Voice1-8 on MIDI Ch 1-8, Effect Ch 16, and the song bank
loaded (fm1ctl.py load-bank). For Carlos's stereo spread, set each Voice's
Pan on the unit (PRESETS list, SELECT to the Voice, K3): violins left,
violas centre, cellos and bass right.
"""

from fm1.song import Part, Reverb, Song

ROGUE = "dxoc14:8"      # MOOG ROGUE: bright, cutting
# ROGUE's main tone runs at half pitch (sounds an octave low) and rolls off
# above C5, which muted the violin lines on real speakers. For the violins:
# roll-off removed and the parts played an octave up, at Bach's pitch.
# ("Option 4 by a mile", 2026-11-20.)
BRIGHT_ROGUE = "dxoc14:8"
BRIGHT_EDITS = {"op4.rd": 0, "op5.rd": 0}
MOOGER = "mike2:4"      # MOOGER: rounder; also the pick for the bass. In a
                        # bass shoot-out (MOOG BASS, SynBass1, PrSynBass1,
                        # SYNBASS 3B, MINI MOOGY, MINI-MOOG) the others were as
                        # twangy but some drove the very low end far too hard.

SONG = Song(
    title="Brandenburg Concerto No. 3, I (Switched-On)",
    parts=[
        Part(channel=1, sound=BRIGHT_ROGUE, edits=BRIGHT_EDITS, tracks=["1"],
             transpose=12),  # Violino I
        Part(channel=2, sound=BRIGHT_ROGUE, edits=BRIGHT_EDITS, tracks=["2"],
             transpose=12),  # Violino II (all violins bright)
        Part(channel=3, sound=BRIGHT_ROGUE, edits=BRIGHT_EDITS, tracks=["3"],
             transpose=12),  # Violino III
        Part(channel=4, sound=MOOGER, tracks=["4"], expression=100),    # Viola I
        Part(channel=5, sound=BRIGHT_ROGUE, edits=BRIGHT_EDITS, tracks=["5"],
             expression=100, transpose=12),                         # Viola II
        Part(channel=6, sound=MOOGER, tracks=["6"], expression=100),    # Viola III
        # Cellos: ROGUE was sounding an octave low, which is why the low parts
        # swamped the violins and had to sit at 50. At Bach's pitch they can
        # come up to 85 ("option 3 is the winner"). Earlier balance notes:
        # then "boost the highs": violins full, violas 100, low parts 50.
        Part(channel=7, sound=BRIGHT_ROGUE, edits=BRIGHT_EDITS, tracks=["7", "8", "9"],
             expression=85, transpose=12),                          # Violoncello I-III
        Part(channel=8, sound=MOOGER, tracks=["10"], expression=50),          # Continuo
    ],
    reverb=Reverb("room", decay=15, mix=3),   # by ear on headphones: hall too much, fully dry too bare
)
