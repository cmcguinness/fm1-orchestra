"""Slides for the Aquarium video (`fm1ctl.py video aquarium`; see fm1-orchestra/fm1/video.py)."""

FOOTER = "Saint-Saëns · Aquarium · M-VAVE FM-1"

SLIDES = [
    {"kind": "title", "title": "Aquarium", "weight": 0.8, "lines": [
        "from Le Carnaval des animaux (The Carnival of the Animals)",
        "Camille Saint-Saëns, 1886",
        "Played on an M-VAVE FM-1: a compact six-operator FM synthesizer, "
        "Yamaha DX7 compatible. Firmware V16: eight parts, 20 voices.",
    ]},
    {"kind": "bullets", "heading": "The piece", "weight": 1.3, "bullets": [
        "Saint-Saëns wrote The Carnival of the Animals in 1886 as a private "
        "joke for a Mardi Gras concert: a “grand zoological fantasy” in 14 movements.",
        "Worried it would hurt his serious reputation, he forbade publication in "
        "his lifetime, except for The Swan. It appeared in 1922, after his death.",
        "Aquarium paints light moving through water: rippling piano figures, muted "
        "strings, and a glass harmonica floating above the flute's melody.",
        "You may have heard it at Epcot: it opens Impressions de France, the "
        "France pavilion's film, in Buddy Baker's arrangement.",
    ]},
    {"kind": "bullets", "heading": "The arrangement", "weight": 1.0, "bullets": [
        "Score: Nevin Williams' MuseScore transcription of the Durand edition, "
        "for flute, glass harmonica, two pianos and strings (IMSLP #904564/904565), "
        "dedicated to the public domain.",
        "Converted from MusicXML to MIDI by fm1control (with music21), keeping the "
        "score's dynamics, hairpins, sf accents, pizzicati and pedal.",
        "Tempo: the score says only Andantino; we play it at 66 quarter notes a minute.",
    ]},
    {"kind": "table", "heading": "The voices", "weight": 1.3,
     "columns": ["FM-1 part", "Instrument", "DX7 patch", "Notes"],
     "widths": [1.1, 1.6, 1.6, 2.4],
     "rows": [
         ["Voice 1", "Piano 1", "PIANO 1", "factory ROM 1A; arpeggios voiced"],
         ["Voice 2", "Glass harmonica", "CRYSTALBEL", "at the written octave"],
         ["Voice 3", "Flute", "FLUTE 1", "factory ROM 1A"],
         ["Voice 4", "Piano 2", "PIANO 1", "arpeggios voiced"],
         ["Voices 5–6", "Violins I & II", "VIOLA SECN", "muted (Sourdine), p"],
         ["Voices 7–8", "Violas, cellos", "STRINGS 2", "factory ROM 1A"],
     ],
     "notes": ["Patches from Dave Benson's public-domain DX7 library, chosen by ear "
               "in side-by-side auditions."]},
    {"kind": "bullets", "heading": "How it's played", "weight": 1.2, "bullets": [
        "fm1control (Python) sends each part's notes live over USB MIDI, one MIDI "
        "channel per FM-1 part.",
        "All the sounds sit in one FM-1 preset bank; each part picks its patch by "
        "Program Change, and its level by Expression (strings at 100 of 127).",
        "Piano figures are voiced by pitch: each ripple swells to its top note. "
        "sf accents lift the pp texture rather than jump to forte.",
        "Light room reverb from the FM-1's own effects. Recorded straight from "
        "its USB audio, no microphones.",
    ]},
    {"kind": "bullets", "heading": "Choices made by ear", "weight": 1.1, "bullets": [
        "The first glass harmonica patch whined: it sounds an octave above the "
        "note, and the source we started from was already an octave high. The "
        "score's octave fixed it, and CRYSTALBEL won a seven-way shoot-out.",
        "The strings combine two patches: VIOLA SECN for the violins, STRINGS 2 "
        "below, picked from eight string sections.",
        "Software rubato was tried and rejected; the score's own dynamics carry "
        "the phrasing.",
    ]},
    {"kind": "title", "title": "Aquarium", "lines": [
        "Camille Saint-Saëns",
        "Score transcribed by Nevin Williams",
        "Performed by Charles McGuinness and Claude, on an M-VAVE FM-1",
        "Recorded 20 November 2026",
    ]},
]
