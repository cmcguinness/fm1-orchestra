"""Recording the FM-1's own USB audio while it plays.

The FM-1 is a USB audio interface ("FM-1 Audio", 2 channels, 44.1 kHz), so
recording needs no cables. Capture is done here in Python with sounddevice
(PortAudio), choosing the FM-1's *input* by device number. Traps found
2026-11-20 with off-the-shelf tools:
  - ffmpeg's AVFoundation capture silently drops ~5% of the audio (10 s
    requested -> 9.45 s of samples), whatever its queue size.
  - sox can't open "FM-1 Audio" by name, because macOS lists an input and an
    output with that same name.
sounddevice captured 10.008 s in 10 s with no overflows. ffmpeg is still used
to trim silence, normalise and encode. The level follows the FM-1's volume
knob. macOS asks once for microphone permission for the terminal app.
"""

import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

DEFAULT_DEVICE = "FM-1 Audio"
RATE = 44100
START_GRACE = 0.5       # seconds of capture before playing
TAIL = 2.5              # seconds kept rolling after the last note (releases, reverb)
PEAK_TARGET = -1.0      # dBFS peak after normalising
SILENCE = "-85dB"       # only true silence: quiet endings (ppp) sit near -60 dB


class RecordError(RuntimeError):
    pass


def input_device(name: str) -> int:
    """PortAudio device number of the audio input called `name`."""
    import sounddevice as sd
    for i, d in enumerate(sd.query_devices()):
        if d["name"] == name and d["max_input_channels"] >= 2:
            return i
    raise RecordError(f"no audio input named {name!r}; is the FM-1 connected?")


def check_ready(output: Path, device: str = DEFAULT_DEVICE) -> None:
    """Fail before any MIDI is sent if recording can't work."""
    if shutil.which("ffmpeg") is None:
        raise RecordError("--record needs ffmpeg (brew install ffmpeg)")
    if not output.parent.is_dir():
        raise RecordError(f"no such folder: {output.parent}")
    if output.suffix.lower() not in (".wav", ".flac", ".mp3", ".m4a", ".aiff"):
        raise RecordError("--record file must end in .wav, .flac, .mp3, .m4a or .aiff")
    input_device(device)


class Recorder:
    """Context manager: capture while the block runs, then trim and save.

    Ctrl-C inside the block still produces a file of what was played.
    """

    def __init__(self, output: Path, normalize: bool = True, log=print,
                 device: str = DEFAULT_DEVICE, raw: bool = False):
        """raw=True keeps the capture exactly as recorded (no trim, no gain, WAV
        only), for stems that must line up; see mark()."""
        self.output = output
        self.device = device
        self.normalize = normalize
        self.keep_raw = raw
        self.mark_frame: int | None = None
        self.log = log
        self.raw = Path(tempfile.mkstemp(suffix=".wav", prefix="fm1-raw-")[1])

    def __enter__(self) -> "Recorder":
        import sounddevice as sd
        self.chunks: queue.Queue = queue.Queue()
        self.problems = 0
        self.frames = 0
        self.last: tuple[float, int] | None = None   # (ADC time, frame) of the latest chunk
        self.wav = wave.open(str(self.raw), "wb")
        self.wav.setnchannels(2)
        self.wav.setsampwidth(2)
        self.wav.setframerate(RATE)

        def callback(data, frames, when, status):
            if status:
                self.problems += 1
            self.last = (when.inputBufferAdcTime, self.frames)
            self.frames += frames
            self.chunks.put(bytes(data))

        def writer():
            while True:
                chunk = self.chunks.get()
                if chunk is None:
                    return
                self.wav.writeframes(chunk)
        self.thread = threading.Thread(target=writer, daemon=True)
        self.thread.start()
        self.stream = sd.InputStream(device=input_device(self.device), channels=2,
                                     samplerate=RATE, dtype="int16", callback=callback)
        self.stream.start()
        time.sleep(START_GRACE)
        return self

    def mark(self) -> int:
        """Note the capture frame that corresponds to now (call just before
        playing). Uses PortAudio's clock, so it's accurate to well under a
        millisecond rather than to the size of an audio block."""
        now = self.stream.time
        if self.last is None:
            raise RecordError("no audio has arrived from the FM-1 yet")
        adc, frame = self.last
        self.mark_frame = frame + round((now - adc) * RATE)
        return self.mark_frame

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                time.sleep(TAIL)
        finally:
            self._stop()
        if self.keep_raw:
            shutil.move(self.raw, self.output)
            return
        if self.raw.stat().st_size > 1024:
            finish(self.raw, self.output, self.normalize, self.log)
        self.raw.unlink(missing_ok=True)

    def _stop(self) -> None:
        self.stream.stop()
        self.stream.close()
        self.chunks.put(None)
        self.thread.join(timeout=10)
        self.wav.close()
        if self.problems:
            self.log(f"warning: {self.problems} audio overflow(s) while recording")

def finish(raw: Path, output: Path, normalize: bool = True, log=print) -> None:
    """Trim leading/trailing silence, normalise the peak, encode to `output`."""
    trim = (f"silenceremove=start_periods=1:start_threshold={SILENCE}:start_silence=0.05,"
            f"areverse,silenceremove=start_periods=1:start_threshold={SILENCE}:"
            f"start_silence=0.5,areverse")
    gain = 0.0
    if normalize:
        peak = _peak_db(raw, trim)
        if peak is None:
            log("Recording is silent: is the FM-1's volume turned down?")
            return
        gain = PEAK_TARGET - peak
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
         "-af", f"{trim},volume={gain:.2f}dB", str(output)],
        capture_output=True, text=True)
    if result.returncode:
        raise RecordError(f"ffmpeg couldn't write {output}: {result.stderr.strip()}")
    note = f", normalised {gain:+.1f} dB" if normalize else ""
    log(f"Recorded {output} ({_duration(output):.1f} s{note})")


def _peak_db(path: Path, filters: str) -> float | None:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
                          f"{filters},volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"max_volume: (-?[\d.]+|-inf) dB", out)
    if not m or m.group(1) == "-inf" or float(m.group(1)) < -80:
        return None
    return float(m.group(1))


def _duration(path: Path) -> float:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
