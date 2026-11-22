# Setup

Everything needed before the first note: the Mac side, the FM-1's own
settings, and the firmware.

## Requirements

- **macOS.** Developed on macOS 27; the audio recording path uses CoreAudio.
- **An M-VAVE FM-1 on firmware V16** (multitimbral: 8 parts, 20 voices),
  connected by USB. V15 plays single-part pieces only; see [Firmware](#upgrading-the-fm-1-to-v16).
- **Python 3.12.** `python-rtmidi` has no wheels for 3.13/3.14 on macOS yet, and
  building it from source fails.
- **[uv](https://docs.astral.sh/uv/)** (or plain `pip`) and **[Homebrew](https://brew.sh)**
  for `ffmpeg`, which is used to trim recordings and make videos.
- Something to listen with. The FM-1 has a headphone/line jack. Its USB audio
  can also be monitored through the Mac; [Rogue Amoeba Loopback](https://rogueamoeba.com/loopback/)
  with *FM-1 Audio* as the source and your speakers as the monitor works well.

## Installing

```sh
git clone https://github.com/cmcguinness/fm1-orchestra.git
cd fm1-orchestra
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
brew install ffmpeg

.venv/bin/python fm1-orchestra/fm1ctl.py ports      # should list "FM-1" outputs and inputs
.venv/bin/python fm1-orchestra/fm1ctl.py identity   # should print FM-1_016
.venv/bin/python -m pytest            # optional: the test suite needs no hardware
```

All commands below are `.venv/bin/python fm1-orchestra/fm1ctl.py ...`, run from the
repository root; every command takes `--help`.

## Setting up the FM-1 (once)

Song modules assume this layout on the unit. These settings are global, so they
survive changing songs; save them so they survive power cycles too.

1. **Give each part its own channel.** Turn the **PRESETS** knob to open the
   preset list, then turn **SELECT** to scroll to the entries above the presets:
   *FX, Voice1 … Voice8*. With a Voice highlighted, the four knobs under the
   screen are **K1 MIDI Ch, K2 Level, K3 Pan, K4 On/Off**. Set
   **Voice *n* to MIDI channel *n*** (Voice1 → 1 … Voice8 → 8), all **On**, all
   levels equal. Don't use **ALL**. The list closes after about 3 seconds idle;
   turn PRESETS again to reopen it.
2. **Move the effect channel out of the way.** Press **GLO** and set
   **Effect Ch** to **16**. Effects are controlled by CCs on this channel, and on
   V16 notes 0–26 sent there light the key LEDs instead of playing.
3. **Save.** **SAVE → Globe**.
4. Optional: set each Voice's **Pan** (K3) to taste. The FM-1 ignores MIDI pan
   (CC 10), so pan lives on the unit; for recordings, `--stems` pans in software.

## Upgrading the FM-1 to V16

1. Download **M-UPGRADE** for macOS and the **FM-1 firmware** (`FM-1.fwsc`) from
   [m-vave.com/download](https://www.m-vave.com/download).
2. Open M-UPGRADE with the FM-1 connected, choose **Select firmware**, pick the
   `.fwsc` file and start the upgrade.
3. Afterwards `fm1ctl.py identity` should print `FM-1_016`. Presets survived the
   upgrade on our unit.

In our upgrade M-UPGRADE reported *"Create MIDI enumerator: -304"* during its
verify step, yet the flash had worked. Check with `identity` before retrying.
Upgrading firmware carries some risk; back up anything you care about first.
