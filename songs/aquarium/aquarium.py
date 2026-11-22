"""Saint-Saens, The Carnival of the Animals, 7. Aquarium -- from the score.

aquarium.mid is generated from Nevin Williams' MuseScore transcription of
the Durand edition (IMSLP #904565, public domain dedication), kept in
songs/aquarium/sources/ (gitignored), with:

    fm1ctl.py import-score "songs/aquarium/sources/IMSLP904565-PMLP6099-Aquarium_(No._7).mxl" \\
        songs/aquarium/aquarium.mid --bpm 66

It has the full ensemble, the glass harmonica at the written octave, and
the score's dynamics, hairpins and pizzicati. (It replaced a version built on
a downloaded MIDI arrangement, which had the glass an octave too high and
left out the flute and strings.) The score
says only "Andantino"; 66 bpm is my choice.

On the FM-1: Voice1-8 on MIDI Ch 1-8, Effect Ch 16, song bank loaded.
"""

from fm1.song import Part, Reverb, Song

# Strings picked by ear (2026-11-20) from 8 sections, then mixed: VIOLA SECN
# on the violins, factory STRINGS 2 (the softer one) on violas and cellos.
UPPER_STRINGS = "bank0043:15"   # VIOLA SECN
LOWER_STRINGS = "rom1a:5"       # STRINGS 2

SONG = Song(
    title="Aquarium (Saint-Saens)",
    parts=[
        Part(channel=1, sound="rom1a:8", tracks=["Piano 1"], shape=0.25),    # PIANO 1
        Part(channel=2, sound="atsu_4:28", tracks=["Glass Harmonica"]),       # CRYSTALBEL
        Part(channel=3, sound="rom1a:24", tracks=["Flute"]),                  # FLUTE 1
        Part(channel=4, sound="rom1a:8", tracks=["Piano 2"], shape=0.25),
        Part(channel=5, sound=UPPER_STRINGS, tracks=["Violins 1"], expression=100),
        Part(channel=6, sound=UPPER_STRINGS, tracks=["Violins 2"], expression=100),
        Part(channel=7, sound=LOWER_STRINGS, tracks=["Violas"], expression=100),
        Part(channel=8, sound=LOWER_STRINGS, tracks=["Violoncellos"], expression=100),
    ],
    reverb=Reverb("room", decay=30, mix=7),
)
