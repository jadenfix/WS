#!/usr/bin/env python3
"""Verify recorded bytes, source provenance, and the offline workflow receipt."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads((DEMO / "source-manifest.json").read_text())
    for name, expected in manifest["files"].items():
        actual = sha256(ROOT / name)
        if actual != expected:
            raise SystemExit(f"source drift: {name}: expected {expected}, got {actual}")

    checksums = {}
    for line in (DEMO / "checksums.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        checksums[name] = digest
    for name, expected in checksums.items():
        actual = sha256(DEMO / name)
        if actual != expected:
            raise SystemExit(f"media drift: {name}: expected {expected}, got {actual}")

    receipt = json.loads((DEMO / "capture.json").read_text())
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "output"
        subprocess.run([
            "python", "Crime-Web-Scraping.py", "--input",
            "examples/crime-tables.html", "--output", str(output)
        ], cwd=ROOT, check=True, capture_output=True, text=True)
        summary = json.loads((output / "summary.json").read_text())
        with (output / "counties.csv").open(newline="", encoding="utf-8") as handle:
            counties = list(csv.DictReader(handle))
        with (output / "cities.csv").open(newline="", encoding="utf-8") as handle:
            cities = list(csv.DictReader(handle))
        observed_hashes = {name: sha256(output / name) for name in ("counties.csv", "cities.csv", "summary.json")}

    assert receipt["source_commit"] == manifest["source_commit"]
    assert summary["rows"] == receipt["rows"] == {"counties": 1, "cities": 1}
    assert observed_hashes == receipt["output_sha256"]
    assert len(counties) == len(cities) == 1
    assert counties[0]["County"] == "Example County"
    assert "[" not in counties[0]["County"]
    assert counties[0]["Population"] == "12345"
    assert counties[0]["Violent crime rate per 1,000 persons"] == "1.38"
    assert cities[0]["City/Agency"] == "Example City"
    for name, expected in checksums.items():
        assert receipt["media"][name]["sha256"] == expected
    print("verified: source manifest, offline CLI evidence, output hashes, and media bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
