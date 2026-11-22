"""Slides for the Carol of the Bells video (`fm1ctl.py video carol-of-the-bells`;
see fm1-orchestra/fm1/video.py).

The piece is short (about 76 s), so the text is kept brief, the credits are on
the opening slide, and the donation slide comes last, so its QR code stays on
screen until the end.
"""

# Didot has no Cyrillic, so "Щедрик" appears only in body text (Avenir Next).
FOOTER = "Leontovych · Shchedryk (Carol of the Bells) · M-VAVE FM-1"

SLIDES = [
    {"kind": "title", "title": "Carol of the Bells", "weight": 1.0, "lines": [
        "Shchedryk, Mykola Leontovych, 1916",
        "A new arrangement for FM bells, played on an M-VAVE FM-1, "
        "a Yamaha DX7-compatible synthesizer, eight parts at once.",
        "Arranged and performed by Charles McGuinness and Claude · "
        "Recorded 21 November 2026",
    ]},
    {"kind": "bullets", "heading": "The piece", "weight": 1.1, "bullets": [
        "Shchedryk (Щедрик) is a Ukrainian New Year's song: a swallow promises "
        "the family a bountiful year.",
        "Leontovych set it for choir; it was first sung in Kyiv in 1916.",
        "English words came in 1936, making it \"Carol of the Bells\".",
    ]},
    {"kind": "bullets", "heading": "This arrangement", "weight": 1.0, "bullets": [
        "Leontovych's four voices, as he wrote them, over the four-note "
        "ostinato.",
        "FM synthesis is famous for bells: bells carry the ostinato, mallets "
        "the inner voices, and a low bell tolls each phrase.",
    ]},
    {"kind": "table", "heading": "The voices", "weight": 1.2,
     "columns": ["FM-1 part", "Line", "Patch", "Seat"],
     "widths": [1.0, 1.7, 1.6, 1.0],
     "rows": [
         ["Voice 1", "Ostinato (soprano)", "CELESTE", "left of centre"],
         ["Voice 2", "Soprano, octave up", "BELL 1", "right"],
         ["Voice 3", "Alto", "VIBE 1", "left"],
         ["Voice 4", "Tenor", "MARIMBA", "right"],
         ["Voice 5", "Alto and tenor", "WARM PAD 1", "centre"],
         ["Voice 6", "Bass", "STR.PIZZ.1", "centre"],
         ["Voice 7", "Bass, sustained", "VIOLA SECN", "centre"],
         ["Voice 8", "Tolling bell", "TUB BELLS", "centre"],
     ],
     "notes": ["Public-domain DX7 patches, picked by ear. Each part was recorded "
               "on its own, then mixed in stereo."]},
    {"kind": "qr", "heading": "Support Ukraine",
     "url": "https://u24.gov.ua", "caption": "u24.gov.ua",
     "bullets": [
         "Shchedryk is a Ukrainian song, and Ukraine is still defending itself.",
         "UNITED24 is Ukraine's official fundraising platform: defence, medical "
         "aid, and rebuilding homes and schools.",
         "Scan the code, or visit u24.gov.ua, to give.",
     ]},
]
