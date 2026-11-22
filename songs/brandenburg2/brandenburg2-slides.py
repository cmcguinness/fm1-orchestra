"""Slides for the Brandenburg 2 video (`fm1ctl.py video brandenburg2`; see fm1-orchestra/fm1/video.py)."""

FOOTER = "Bach · Brandenburg Concerto No. 2 · M-VAVE FM-1"

SLIDES = [
    {"kind": "title", "title": "Brandenburg No. 2", "weight": 0.9, "lines": [
        "Concerto in F major, BWV 1047: III. Allegro assai",
        "Johann Sebastian Bach, presented 1721",
        "The theme of William F. Buckley Jr.'s Firing Line, played on an "
        "M-VAVE FM-1: a compact six-operator FM synthesizer, Yamaha DX7 "
        "compatible, eight parts at once.",
    ]},
    {"kind": "bullets", "heading": "The piece", "weight": 1.2, "bullets": [
        "One of six concertos Bach presented in 1721 to Christian Ludwig, "
        "Margrave of Brandenburg.",
        "Its soloists are an unlikely four: trumpet, recorder, oboe and violin, "
        "over strings and continuo.",
        "The finale is a fugue led by the trumpet, whose part climbs to a high "
        "F, among the hardest writing for the instrument in the repertoire.",
    ]},
    {"kind": "bullets", "heading": "Firing Line", "weight": 1.1, "bullets": [
        "From 1966 to 1999, this movement opened Firing Line, William F. "
        "Buckley Jr.'s public-affairs interview programme.",
        "The aim here: that bright trumpet out front, brisk and crisp, with "
        "strings in the Switched-On Bach manner of our Brandenburg No. 3.",
    ]},
    {"kind": "bullets", "heading": "The score", "weight": 1.0, "bullets": [
        "Edition: Mutopia Project (2009), typeset by Andy Vaught from the "
        "Bach-Gesellschaft edition: public domain.",
        "Its MIDI has no dynamics, so fm1-orchestra adds the phrasing: strong beats "
        "lean in, faster notes are lighter, and notes are slightly detached, "
        "the bass most of all.",
        "Played at 100 quarter notes a minute.",
    ]},
    {"kind": "table", "heading": "The voices", "weight": 1.3,
     "columns": ["FM-1 part", "Line", "Patch", "Seat"],
     "widths": [1.0, 1.6, 1.8, 1.0],
     "rows": [
         ["Voice 1", "Trumpet", "TRUMPET 7, reworked", "right of centre"],
         ["Voice 2", "Recorder", "SOFT FLUTE", "left of centre"],
         ["Voice 3", "Oboe", "OBOE", "centre"],
         ["Voice 4", "Solo violin", "MOOG ROGUE", "left"],
         ["Voices 5–6", "Violins I–II", "MOOG ROGUE", "far left, left"],
         ["Voice 7", "Viola", "MOOGER", "right"],
         ["Voice 8", "Cello, violone", "MOOGER", "far right"],
     ],
     "notes": ["Patches from Dave Benson's public-domain DX7 library. The FM-1 "
               "ignores MIDI pan, so each part was recorded on its own and the "
               "eight recordings mixed in stereo, seated as a chamber orchestra."]},
    {"kind": "bullets", "heading": "Choices made by ear", "weight": 1.4, "bullets": [
        "The trumpet took six rounds: it buzzed, went shrill at the high F, and "
        "struck each note like metal. One oscillator sat at a mistuned "
        "3.18× the pitch; tuning it to 3× and softening the start fixed it.",
        "It also gained a trumpet's vibrato, and a start that hits then eases off.",
        "Nine string patches were tried; none sounded like strings, so the "
        "strings went Switched-On instead.",
        "The recorder patch was shrill up high; SOFT FLUTE won from five.",
    ]},
    {"kind": "title", "title": "Brandenburg No. 2", "lines": [
        "Johann Sebastian Bach",
        "Score typeset by Andy Vaught, Mutopia Project",
        "Performed by Charles McGuinness and Claude, on an M-VAVE FM-1",
        "For Firing Line, 1966–1999 · Recorded 21 November 2026",
    ]},
]
