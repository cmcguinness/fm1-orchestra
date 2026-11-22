"""Slides for the Brandenburg 3 video (`fm1ctl.py video brandenburg3`; see fm1-orchestra/fm1/video.py)."""

FOOTER = "Bach · Brandenburg Concerto No. 3 · M-VAVE FM-1"

SLIDES = [
    {"kind": "title", "title": "Brandenburg No. 3", "weight": 0.9, "lines": [
        "Concerto in G major, BWV 1048: I. (Allegro)",
        "Johann Sebastian Bach, presented 1721",
        "In the spirit of Wendy Carlos's Switched-On Bach (1968), "
        "played on an M-VAVE FM-1: a compact six-operator FM synthesizer, "
        "Yamaha DX7 compatible, eight parts at once.",
    ]},
    {"kind": "bullets", "heading": "The piece", "weight": 1.2, "bullets": [
        "One of six concertos Bach presented in 1721 to Christian Ludwig, "
        "Margrave of Brandenburg.",
        "No. 3 is for three violins, three violas, three cellos and continuo: "
        "three equal groups that trade the opening motif back and forth.",
        "Between its two fast movements Bach wrote only two chords, a Phrygian "
        "cadence, for the players to elaborate.",
    ]},
    {"kind": "bullets", "heading": "Switched-On Bach", "weight": 1.3, "bullets": [
        "In 1968 Wendy Carlos recorded Bach on a Moog synthesizer, building each "
        "piece up one line at a time, since the Moog played one note at once.",
        "The album closed with this concerto, won three Grammy Awards, and was "
        "added to the US National Recording Registry in 2005.",
        "Here the FM-1 plays all the lines live, each with its own Moog-style "
        "sound, in homage to that recording.",
    ]},
    {"kind": "bullets", "heading": "The score", "weight": 1.2, "bullets": [
        "Edition: Chris Sawer, Mutopia Project (2004), via IMSLP #57477: "
        "CC BY 3.0 (its own footer says public domain).",
        "Its 45 pages were read by optical music recognition (Audiveris), then "
        "proofread bar by bar against the printed score: 94 corrections, "
        "mostly dropped rests and missed accidentals.",
        "Converted to MIDI by fm1-orchestra, keeping the score's dynamics. The "
        "score says only Allegro; we play it at 100 quarter notes a minute.",
    ]},
    {"kind": "table", "heading": "The voices", "weight": 1.3,
     "columns": ["FM-1 part", "Lines", "Patch", "Notes"],
     "widths": [1.1, 1.6, 1.6, 2.4],
     "rows": [
         ["Voices 1–3", "Violins I–III", "MOOG ROGUE", "brightened, an octave up"],
         ["Voice 4", "Viola I", "MOOGER", "level 100"],
         ["Voice 5", "Viola II", "MOOG ROGUE", "brightened, an octave up, 100"],
         ["Voice 6", "Viola III", "MOOGER", "level 100"],
         ["Voice 7", "Cellos I–III", "MOOG ROGUE", "brightened, an octave up, 85"],
         ["Voice 8", "Continuo", "MOOGER", "level 50"],
     ],
     "notes": ["Patches from Dave Benson's public-domain DX7 library. The three "
               "cellos share one part: they play the same notes about 90% of the time."]},
    {"kind": "bullets", "heading": "Choices made by ear", "weight": 1.2, "bullets": [
        "Fifteen Moog-style DX7 patches were auditioned on the violin line; "
        "MOOG ROGUE and MOOGER won. MOOGER also won a bass shoot-out.",
        "MOOG ROGUE turned out to sound an octave low and to fade above C5, "
        "which buried the violins. With the fade removed and the parts moved "
        "up an octave, the lines sound at Bach's pitch.",
        "Reverb is a near-dry small room, so every line stays distinct.",
    ]},
    {"kind": "title", "title": "Brandenburg No. 3", "lines": [
        "Johann Sebastian Bach",
        "Score typeset by Chris Sawer, Mutopia Project",
        "Performed by Charles McGuinness and Claude, on an M-VAVE FM-1",
        "An homage to Wendy Carlos's Switched-On Bach · Recorded 20 November 2026",
    ]},
]
