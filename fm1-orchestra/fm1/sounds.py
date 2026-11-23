"""Named library sounds: a short name for a patch from the library plus edits.

Use the name anywhere a sound is accepted (`--sound`, a Part's `sound`,
`load-bank --extra`, `send-patch`). Extra edits can follow it, e.g.
`berlin-bass,lfo.pmd=20`; they apply after the name's own.
"""

NAMED = {
    # The DX7's factory BASS 2, the fretless line of Berlin's "Take My Breath
    # Away", with a delayed vibrato built in (the record's came from the mod
    # wheel) and its octave-down transpose removed so a keyboard's middle range
    # sounds where the line sits.
    "berlin-bass": ("rom1a:16", ["lfo.pmd=14", "lfo.speed=34", "lfo.delay=45",
                                 "lfo.wave=4", "pms=3", "transpose=24"],
                    "BASS 2 with delayed vibrato (Berlin, Take My Breath Away)"),
}


def expand(spec: str, edits: list[str]) -> tuple[str, list[str]]:
    """A named sound -> (BANK:N, its edits + `edits`); anything else unchanged."""
    if spec.lower() in NAMED:
        ref, own, _ = NAMED[spec.lower()]
        return ref, [*own, *edits]
    return spec, edits
