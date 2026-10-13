#!/usr/bin/env python3
"""Render a truthful demo from a real offline exporter run.

The visual is deliberately a receipt, not a mock application. Every displayed
value is parsed from the CSV/JSON files produced by Crime-Web-Scraping.py.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"
W, H = 1280, 720
FPS = 12
SCENE_SECONDS = 2.4

BG = "#07101f"
PANEL = "#101e35"
PANEL_2 = "#142642"
WHITE = "#f7fbff"
MUTED = "#9db1cb"
CYAN = "#66e3ff"
MINT = "#78f0bd"
AMBER = "#ffc66d"
RED = "#ff7c91"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font(size: int, bold: bool = False, mono: bool = False):
    if mono:
        candidate = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    elif bold:
        candidate = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    else:
        candidate = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(candidate, size)


def rounded(draw, box, radius=24, fill=PANEL, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw, xy, value, size=28, color=WHITE, bold=False, mono=False, anchor=None):
    draw.text(xy, value, fill=color, font=font(size, bold=bold, mono=mono), anchor=anchor)


def header(draw, step: int, title: str, subtitle: str):
    text(draw, (64, 49), "WS  /  CRIME TABLE EXPORTER", 18, CYAN, bold=True)
    text(draw, (64, 92), title, 42, WHITE, bold=True)
    text(draw, (64, 148), subtitle, 21, MUTED)
    text(draw, (1216, 57), f"0{step} / 06", 17, MUTED, mono=True, anchor="ra")
    draw.rounded_rectangle((64, 682, 1216, 688), radius=3, fill="#1f3454")
    draw.rounded_rectangle((64, 682, 64 + 1152 * step / 6, 688), radius=3, fill=CYAN)


def badge(draw, x, y, label, color=MINT):
    width = draw.textlength(label, font=font(17, bold=True)) + 34
    rounded(draw, (x, y, x + width, y + 38), 19, fill=color)
    text(draw, (x + 17, y + 9), label, 17, BG, bold=True)
    return x + width


def base(step, title, subtitle):
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    # Decorative data rays; these are framing, not data.
    for i in range(7):
        x = 930 + i * 55
        draw.line((x, 0, x - 210, H), fill="#0b1a2f", width=2)
    header(draw, step, title, subtitle)
    return image, draw


def scene_one(data):
    im, d = base(1, "One command. Three auditable outputs.", "A real offline run — no network, no hidden API, no invented dashboard")
    rounded(d, (64, 215, 1216, 598), 30, PANEL)
    text(d, (104, 254), "$ python Crime-Web-Scraping.py \\", 24, CYAN, mono=True)
    text(d, (104, 294), "    --input examples/crime-tables.html --output output", 24, WHITE, mono=True)
    badge(d, 104, 364, "FICTIONAL OFFLINE FIXTURE", AMBER)
    badge(d, 405, 364, "NETWORK: OFF", MINT)
    text(d, (104, 438), "Source pinned", 17, MUTED, bold=True)
    text(d, (104, 468), data["source_commit"][:12], 24, WHITE, mono=True)
    text(d, (470, 438), "Result", 17, MUTED, bold=True)
    text(d, (470, 468), "counties.csv  •  cities.csv  •  summary.json", 24, WHITE, mono=True)
    text(d, (104, 545), "LIVE WIKIPEDIA UNVERIFIED", 16, RED, bold=True)
    return im


def scene_two(data):
    im, d = base(2, "Schema detection, not table position", "The parser inspects headers and ignores unrelated markup")
    cards = [
        ("01", "Unrelated navigation", "IGNORED", MUTED),
        ("02", "County + Population", "COUNTIES", CYAN),
        ("03", "City/Agency + County", "CITIES", MINT),
    ]
    for idx, (num, name, status, color) in enumerate(cards):
        y = 224 + idx * 118
        rounded(d, (64, y, 1216, y + 92), 20, PANEL_2 if idx else PANEL)
        text(d, (94, y + 27), num, 24, color, mono=True, bold=True)
        text(d, (164, y + 26), name, 25, WHITE, bold=True)
        text(d, (1178, y + 30), status, 17, color, bold=True, anchor="ra")
    text(d, (64, 610), f"Observed from fixture: {data['table_count']} HTML tables → 2 accepted schemas", 20, MUTED)
    return im


def scene_three(data):
    im, d = base(3, "Cleaning that preserves meaning", "Citations and numeric grouping disappear; decimal precision remains")
    rounded(d, (64, 220, 1216, 586), 28, PANEL)
    rows = [
        ("County label", "Example County [1]", "Example County", "citation removed"),
        ("Population", "12,345", data["county"]["Population"], "grouping removed"),
        ("Rate / 1,000", "1.38", data["county"]["Violent crime rate per 1,000 persons"], "fraction preserved"),
    ]
    for idx, (label, before, after, note) in enumerate(rows):
        y = 257 + idx * 100
        text(d, (98, y), label.upper(), 15, MUTED, bold=True)
        text(d, (98, y + 27), before, 26, "#b9c7da", mono=True)
        text(d, (514, y + 27), "→", 28, CYAN, bold=True)
        text(d, (584, y + 27), after, 28, WHITE, mono=True, bold=True)
        text(d, (1175, y + 32), note, 16, MINT, bold=True, anchor="ra")
    return im


def csv_panel(d, title, filename, headers, values, accent):
    rounded(d, (64, 218, 1216, 586), 26, PANEL)
    text(d, (96, 249), title, 26, WHITE, bold=True)
    text(d, (1184, 253), filename, 17, accent, mono=True, anchor="ra")
    x = 96
    # Leave enough separation for the longest fixture labels at GIF resolution.
    widths = [280, 260, 190, 270]
    for idx, heading in enumerate(headers):
        text(d, (x, 325), heading, 14, MUTED, bold=True)
        text(d, (x, 373), values[idx], 23, WHITE, mono=True)
        x += widths[idx]
    d.line((96, 353, 1184, 353), fill="#2a4062", width=2)
    text(d, (96, 505), "1 data row", 18, accent, bold=True)
    text(d, (1184, 505), "UTF-8 CSV  •  parsed back for this frame", 17, MUTED, anchor="ra")


def scene_four(data):
    im, d = base(4, "County export", "The display below is parsed from the produced CSV — not typed into the animation")
    c = data["county"]
    csv_panel(d, "County table", "output/counties.csv",
              ["COUNTY", "POPULATION", "VIOLENT CRIMES", "RATE PER 1,000"],
              [c["County"], c["Population"], c["Violent crimes"], c["Violent crime rate per 1,000 persons"]], CYAN)
    return im


def scene_five(data):
    im, d = base(5, "City export", "Independent output with the same provenance and cleanup contract")
    c = data["city"]
    csv_panel(d, "City / agency table", "output/cities.csv",
              ["CITY / AGENCY", "COUNTY", "POPULATION", "VIOLENT CRIMES"],
              [c["City/Agency"], c["County"], c["Population"], c["Violent crimes"]], MINT)
    return im


def scene_six(data):
    im, d = base(6, "Receipt complete", "Counts, source and output digests are independently checkable")
    rounded(d, (64, 215, 760, 594), 26, PANEL)
    text(d, (98, 252), "summary.json", 18, CYAN, mono=True, bold=True)
    summary_lines = [
        "{",
        '  "source": "examples/crime-tables.html",',
        '  "rows": { "counties": 1, "cities": 1 }',
        "}",
    ]
    for i, line in enumerate(summary_lines):
        text(d, (98, 306 + i * 45), line, 22, WHITE if i not in (1, 2) else "#c7d7eb", mono=True)
    rounded(d, (792, 215, 1216, 594), 26, PANEL_2)
    text(d, (824, 252), "VERIFIED OUTPUT", 16, MINT, bold=True)
    text(d, (824, 301), "1", 48, WHITE, bold=True)
    text(d, (888, 322), "county row", 19, MUTED)
    text(d, (824, 381), "1", 48, WHITE, bold=True)
    text(d, (888, 402), "city row", 19, MUTED)
    text(d, (824, 474), "1.38", 34, CYAN, mono=True, bold=True)
    text(d, (824, 517), "fractional rate retained", 17, MUTED)
    text(d, (64, 630), "FICTIONAL OFFLINE FIXTURE  •  LIVE WIKIPEDIA UNVERIFIED", 16, AMBER, bold=True)
    return im


def collect() -> dict:
    manifest = json.loads((DEMO / "source-manifest.json").read_text())
    for name, expected in manifest["files"].items():
        actual = sha256(ROOT / name)
        if actual != expected:
            raise SystemExit(f"source drift: {name}: expected {expected}, got {actual}")

    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "output"
        subprocess.run(
            ["python", "Crime-Web-Scraping.py", "--input",
             "examples/crime-tables.html", "--output", str(output)],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        with (output / "counties.csv").open(newline="", encoding="utf-8") as handle:
            counties = list(csv.DictReader(handle))
        with (output / "cities.csv").open(newline="", encoding="utf-8") as handle:
            cities = list(csv.DictReader(handle))
        summary = json.loads((output / "summary.json").read_text())
        output_hashes = {name: sha256(output / name) for name in ("counties.csv", "cities.csv", "summary.json")}

    fixture = (ROOT / "examples/crime-tables.html").read_text()
    if len(counties) != 1 or len(cities) != 1 or summary["rows"] != {"counties": 1, "cities": 1}:
        raise SystemExit("fixture result no longer matches the recording contract")
    county = counties[0]
    if county["County"] != "Example County" or county["Population"] != "12345":
        raise SystemExit("cleaning evidence changed")
    if county["Violent crime rate per 1,000 persons"] != "1.38":
        raise SystemExit("fractional-rate evidence changed")
    return {
        "source_commit": manifest["source_commit"],
        "table_count": fixture.count("<table>"),
        "county": county,
        "city": cities[0],
        "summary": summary,
        "output_sha256": output_hashes,
    }


def render_frames(data: dict, frame_dir: Path):
    scenes = [scene_one(data), scene_two(data), scene_three(data), scene_four(data), scene_five(data), scene_six(data)]
    hold = round(FPS * SCENE_SECONDS)
    fade = round(FPS * 0.4)
    frame_number = 0
    for index, current in enumerate(scenes):
        for position in range(hold):
            if index and position < fade:
                alpha = 0.5 - 0.5 * math.cos(math.pi * position / fade)
                frame = Image.blend(scenes[index - 1], current, alpha)
            else:
                frame = current
            frame.save(frame_dir / f"frame-{frame_number:04d}.png", optimize=True)
            frame_number += 1
    return frame_number


def encode(frame_dir: Path):
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required to encode the demo")
    pattern = str(frame_dir / "frame-%04d.png")
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS),
        "-i", pattern, "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-map_metadata", "-1",
        str(DEMO / "ws-offline-demo.mp4"),
    ], check=True)
    palette = frame_dir / "palette.png"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS),
        "-i", pattern, "-vf", "fps=8,scale=960:-1:flags=lanczos,palettegen=max_colors=128:stats_mode=diff",
        str(palette),
    ], check=True)
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS),
        "-i", pattern, "-i", str(palette), "-lavfi",
        "fps=8,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
        "-loop", "0", str(DEMO / "ws-offline-demo.gif"),
    ], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data = collect()
    with tempfile.TemporaryDirectory() as temp:
        frames = Path(temp) / "frames"
        frames.mkdir()
        frame_count = render_frames(data, frames)
        encode(frames)
    media = {}
    for name in ("ws-offline-demo.gif", "ws-offline-demo.mp4"):
        path = DEMO / name
        media[name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    receipt = {
        "schema_version": 1,
        "claim": "Actual offline CLI run against a fictional checked-in fixture",
        "nonclaims": [
            "The demo does not verify or display live Wikipedia data.",
            "The fictional records are not crime statistics or current estimates."
        ],
        "source_commit": data["source_commit"],
        "input": "examples/crime-tables.html",
        "observed_html_tables": data["table_count"],
        "rows": data["summary"]["rows"],
        "evidence": {
            "citation_removed": "Example County [1] -> Example County",
            "population_grouping_removed": "12,345 -> 12345",
            "fractional_rate_preserved": data["county"]["Violent crime rate per 1,000 persons"],
        },
        "output_sha256": data["output_sha256"],
        "recording": {"width": W, "height": H, "fps": FPS, "frames": frame_count},
        "media": media,
    }
    (DEMO / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    with (DEMO / "checksums.sha256").open("w") as handle:
        for name in ("ws-offline-demo.gif", "ws-offline-demo.mp4"):
            handle.write(f"{media[name]['sha256']}  {name}\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
