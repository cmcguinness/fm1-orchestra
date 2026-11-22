"""Build a 1080p slide-show video over a recorded performance.

Usually run as `fm1ctl.py video NAME`, which uses the song folder's files:
songs/NAME/NAME-slides.py over songs/NAME/build/NAME.wav, writing
songs/NAME/NAME.mp4. Directly, from fm1-orchestra/:

    python -m fm1.video ../songs/aquarium/aquarium-slides.py \\
        --audio ../songs/aquarium/build/aquarium.wav --out ../songs/aquarium/aquarium.mp4

The spec is a Python file defining SLIDES (and optionally FOOTER, the text at
the bottom of each slide), SLIDES being a list of dicts:
    {"kind": "title",   "title": ..., "lines": [...], "weight": 1}
    {"kind": "bullets", "heading": ..., "bullets": [...], "weight": 1}
    {"kind": "table",   "heading": ..., "columns": [...], "rows": [[...]], "notes": [...]}
    {"kind": "qr",      "heading": ..., "bullets": [...], "url": ..., "caption": ...}
(a "qr" slide shows the bullets beside a scannable QR code for `url`).
The last slide holds until the music ends. Each slide's screen time is shared
out by `weight` (default 1), crossfading between slides. Needs ffmpeg.
"""

import argparse
import io
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
MARGIN = 140
FADE = 1.0                  # seconds of crossfade between slides
LAST_MIN = 14.0             # the closing slide holds at least this long
SERIF = "/System/Library/Fonts/Supplemental/Didot.ttc"
SANS = "/System/Library/Fonts/Avenir Next.ttc"
INK = (236, 241, 244)
SOFT = (170, 196, 206)
ACCENT = (120, 200, 210)


def font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=index)


TITLE = lambda s: font(SERIF, s, 0)
TITLE_I = lambda s: font(SERIF, s, 1)
BODY = lambda s: font(SANS, s, 7)          # Regular
BODY_M = lambda s: font(SANS, s, 5)        # Medium
BODY_D = lambda s: font(SANS, s, 2)        # Demi Bold


def background() -> Image.Image:
    """Deep water: a vertical navy-to-teal gradient with soft light from above."""
    img = Image.new("RGB", (W, H))
    top, bottom = (8, 22, 40), (10, 58, 72)
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        row = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        for x in range(W):
            glow = max(0.0, 1 - ((x - W * 0.62) ** 2 / (W * 0.55) ** 2 + (y + 200) ** 2 / (H * 0.9) ** 2))
            px[x, y] = tuple(min(255, round(c + 26 * glow)) for c in row)
    return img


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = f"{line} {w}".strip()
        if draw.textlength(trial, font=f) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


FOOTER = "M-VAVE FM-1"       # replaced by the spec's FOOTER, if it defines one


def footer(draw, page: int, total: int) -> None:
    draw.line([(MARGIN, H - 92), (W - MARGIN, H - 92)], fill=(60, 100, 112), width=1)
    draw.text((MARGIN, H - 78), FOOTER, font=BODY(24), fill=SOFT)
    label = f"{page} / {total}"
    draw.text((W - MARGIN - draw.textlength(label, font=BODY(24)), H - 78), label,
              font=BODY(24), fill=SOFT)


def heading(draw, text: str) -> int:
    draw.text((MARGIN, 110), text, font=TITLE(76), fill=INK)
    draw.line([(MARGIN, 215), (MARGIN + 160, 215)], fill=ACCENT, width=4)
    return 270


def render(slide: dict, base: Image.Image, page: int, total: int) -> Image.Image:
    img = base.copy()
    d = ImageDraw.Draw(img)
    kind = slide["kind"]
    if kind == "title":
        title_f = TITLE(150)
        tw = d.textlength(slide["title"], font=title_f)
        y = 250 if slide.get("lines") else 420
        d.text(((W - tw) / 2, y), slide["title"], font=title_f, fill=INK)
        y += 200
        d.line([((W - 220) / 2, y), ((W + 220) / 2, y)], fill=ACCENT, width=3)
        y += 50
        for i, line in enumerate(slide.get("lines", [])):
            f = TITLE_I(46) if i == 0 else BODY(36)
            color = INK if i == 0 else SOFT
            for part in wrap(d, line, f, W - 2 * MARGIN):
                lw = d.textlength(part, font=f)
                d.text(((W - lw) / 2, y), part, font=f, fill=color)
                y += 62 if i == 0 else 54
            y += 18
    elif kind == "bullets":
        y = heading(d, slide["heading"])
        f = BODY(38)
        for b in slide["bullets"]:
            lines = wrap(d, b, f, W - 2 * MARGIN - 50)
            d.ellipse([MARGIN + 4, y + 20, MARGIN + 16, y + 32], fill=ACCENT)
            for line in lines:
                d.text((MARGIN + 50, y), line, font=f, fill=INK)
                y += 54
            y += 22
    elif kind == "table":
        y = heading(d, slide["heading"])
        cols = slide["columns"]
        widths = slide.get("widths") or [1] * len(cols)
        span = W - 2 * MARGIN
        xs = [MARGIN]
        for w in widths[:-1]:
            xs.append(xs[-1] + span * w / sum(widths))
        for x, c in zip(xs, cols):
            d.text((x, y), c, font=BODY_D(30), fill=ACCENT)
        y += 52
        d.line([(MARGIN, y), (W - MARGIN, y)], fill=(70, 120, 132), width=1)
        y += 18
        for row in slide["rows"]:
            for i, (x, cell) in enumerate(zip(xs, row)):
                d.text((x, y), cell, font=BODY_M(32) if i == 0 else BODY(32),
                       fill=INK if i < 2 else SOFT)
            y += 56
        y += 20
        for note in slide.get("notes", []):
            for line in wrap(d, note, BODY(28), span):
                d.text((MARGIN, y), line, font=BODY(28), fill=SOFT)
                y += 42
    elif kind == "qr":
        y = heading(d, slide["heading"])
        size = 520
        code = qr_image(slide["url"], size)
        qx, qy = W - MARGIN - size, y + 10
        pad = 24
        d.rounded_rectangle([qx - pad, qy - pad, qx + size + pad, qy + size + pad],
                            radius=18, fill=(255, 255, 255))
        img.paste(code, (qx, qy))
        caption = slide.get("caption", slide["url"])
        cw = d.textlength(caption, font=BODY_M(34))
        d.text((qx + (size - cw) / 2, qy + size + pad + 22), caption, font=BODY_M(34), fill=ACCENT)
        f = BODY(38)
        width = qx - pad - MARGIN - 110
        for b in slide.get("bullets", []):
            d.ellipse([MARGIN + 4, y + 20, MARGIN + 16, y + 32], fill=ACCENT)
            for line in wrap(d, b, f, width):
                d.text((MARGIN + 50, y), line, font=f, fill=INK)
                y += 54
            y += 22
    else:
        raise ValueError(f"unknown slide kind {kind!r}")
    if kind != "title":
        footer(d, page, total)
    return img


def qr_image(url: str, size: int) -> Image.Image:
    """A black-on-white QR code for `url`, `size` pixels square (no quiet zone;
    the slide draws a white card around it)."""
    import segno
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=10, border=0)
    buf.seek(0)
    return Image.open(buf).convert("RGB").resize((size, size), Image.NEAREST)


def audio_seconds(path: Path) -> float:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    if not m:
        raise SystemExit(f"can't read the length of {path}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def durations(slides: list[dict], total: float) -> list[float]:
    """Screen time per slide (including its fade-in overlap)."""
    body = slides[:-1]
    last = max(LAST_MIN, total * 0.12)
    budget = total - last + FADE * len(body)
    weights = [s.get("weight", 1.0) for s in body]
    times = [budget * w / sum(weights) for w in weights]
    return times + [total - sum(times) + FADE * len(body)]


def load_spec(path: Path) -> list[dict]:
    """The spec's SLIDES; also applies its optional FOOTER text."""
    global FOOTER
    spec = importlib.util.spec_from_file_location("video_spec", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    FOOTER = getattr(module, "FOOTER", FOOTER)
    return module.SLIDES


def build(spec: Path, audio: Path, out: Path, keep: Path | None) -> None:
    slides = load_spec(spec)
    total = audio_seconds(audio)
    times = durations(slides, total)
    work = keep or Path(tempfile.mkdtemp(prefix="fm1-video-"))
    work.mkdir(parents=True, exist_ok=True)
    base = background()
    pngs = []
    for i, slide in enumerate(slides, 1):
        p = work / f"slide-{i:02}.png"
        render(slide, base, i, len(slides)).save(p)
        pngs.append(p)
    inputs = []
    for p, t in zip(pngs, times):
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{t:.3f}", "-i", str(p)]
    inputs += ["-i", str(audio)]
    chain, prev, offset = [], "[0:v]", 0.0
    for i in range(1, len(pngs)):
        offset += times[i - 1] - FADE
        label = f"[v{i}]"
        chain.append(f"{prev}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}{label}")
        prev = label
    fade_out = max(0.0, total - 3)
    chain.append(f"{prev}format=yuv420p,fade=t=in:st=0:d=1.5,fade=t=out:st={fade_out:.3f}:d=3[v]")
    audio_n = len(pngs)
    chain.append(f"[{audio_n}:a]afade=t=in:st=0:d=0.3,afade=t=out:st={fade_out:.3f}:d=3[a]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
           "-filter_complex", ";".join(chain), "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "stillimage",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
           "-t", f"{total:.3f}", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"ffmpeg failed: {result.stderr.strip()}")
    for i, (s, t) in enumerate(zip(slides, times), 1):
        print(f"  slide {i}: {t:5.1f} s  {s.get('title') or s.get('heading')}")
    print(f"Wrote {out} ({total:.1f} s, 1920x1080). Slides in {work}")
    if keep is None:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("spec", type=Path, help="slide spec (a .py file defining SLIDES)")
    p.add_argument("--audio", type=Path, required=True, help="the recorded performance")
    p.add_argument("--out", type=Path, required=True, help="the .mp4 to write")
    p.add_argument("--slides-dir", type=Path, help="keep the slide PNGs here")
    a = p.parse_args(argv)
    for f in (a.spec, a.audio):
        if not f.is_file():
            p.error(f"no such file: {f}")
    if a.out.suffix.lower() != ".mp4":
        p.error("--out must end in .mp4")
    if shutil.which("ffmpeg") is None:
        p.error("needs ffmpeg (brew install ffmpeg)")
    build(a.spec, a.audio, a.out, a.slides_dir)


if __name__ == "__main__":
    main()
