"""Finding and opening the FM-1's MIDI ports."""

import mido

DEFAULT_PORT_HINT = "FM-1"


class PortNotFound(RuntimeError):
    pass


def find_port(names: list[str], hint: str = DEFAULT_PORT_HINT) -> str:
    """Return the first port name containing `hint` (case-insensitive)."""
    for name in names:
        if hint.lower() in name.lower():
            return name
    raise PortNotFound(
        f"No MIDI port matching {hint!r}. Available: {names or 'none'}"
    )


def open_output(hint: str = DEFAULT_PORT_HINT) -> mido.ports.BaseOutput:
    return mido.open_output(find_port(mido.get_output_names(), hint))


def open_input(hint: str = DEFAULT_PORT_HINT) -> mido.ports.BaseInput:
    return mido.open_input(find_port(mido.get_input_names(), hint))
