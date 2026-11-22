"""Stem recording: each part recorded alone, then mixed with panning.

The FM-1 ignores MIDI pan (CC10; tested 2026-11-21), and setting pan per
Voice on the panel is fiddly, so stereo placement is done here instead:
every part is played and captured on its own, then ffmpeg mixes the stems
with each part's `pan`.

Alignment: each stem's capture notes the frame at which playback began
(Recorder.mark), and the mix cuts every stem from that frame, so the parts
line up to within a millisecond or so. Every pass sends the same setup, so
reverb and levels match the normal playback.

Panning: each stem is folded to mono and placed with a constant-power pan law
(centre = -3 dB on each side), so a part keeps its loudness wherever it sits.
"""

import json
import math
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fm1.record import RATE, RecordError, finish


@dataclass
class Stem:
    path: Path          # raw capture (WAV, 44.1 kHz stereo)
    start: int          # capture frame at which playback began
    pan: float          # -1 left .. 1 right


def save(stems: list[Stem], folder: Path) -> None:
    """stems.json beside the takes: start frames and pans, for re-mixing later."""
    data = [{"file": s.path.name, "start": s.start, "pan": s.pan} for s in stems]
    (folder / "stems.json").write_text(json.dumps(data, indent=2) + "\n")


def load(folder: Path) -> list[Stem]:
    data = json.loads((folder / "stems.json").read_text())
    return [Stem(folder / d["file"], d["start"], d["pan"]) for d in data]


def gains(pan: float) -> tuple[float, float]:
    """Constant-power (left, right) gains for pan -1..1."""
    angle = (pan + 1) * math.pi / 4
    return math.cos(angle), math.sin(angle)


def mix_filter(stems: list[Stem]) -> str:
    """The ffmpeg filter graph that aligns, pans and sums the stems."""
    chains, labels = [], []
    for i, stem in enumerate(stems):
        left, right = gains(stem.pan)
        chains.append(
            f"[{i}:a]atrim=start_sample={stem.start},asetpts=PTS-STARTPTS,"
            f"pan=stereo|c0={left / 2:.4f}*c0+{left / 2:.4f}*c1"
            f"|c1={right / 2:.4f}*c0+{right / 2:.4f}*c1[s{i}]")
        labels.append(f"[s{i}]")
    chains.append(f"{''.join(labels)}amix=inputs={len(stems)}:normalize=0:duration=longest[out]")
    return ";".join(chains)


def mix(stems: list[Stem], output: Path, normalize: bool = True, log=print) -> None:
    """Mix stems into `output`: silence trimmed and peak normalised, as --record."""
    if not stems:
        raise RecordError("no stems to mix")
    raw = Path(tempfile.mkstemp(suffix=".wav", prefix="fm1-mix-")[1])
    try:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        for stem in stems:
            cmd += ["-i", str(stem.path)]
        # 32-bit float until the final gain, so summing can't clip.
        cmd += ["-filter_complex", mix_filter(stems), "-map", "[out]",
                "-ar", str(RATE), "-c:a", "pcm_f32le", str(raw)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            raise RecordError(f"ffmpeg couldn't mix the stems: {result.stderr.strip()}")
        finish(raw, output, normalize, log)
    finally:
        raw.unlink(missing_ok=True)
