"""Export California crime tables from saved HTML or Wikipedia to clean CSVs."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://en.wikipedia.org/wiki/California_locations_by_crime_rate"


def clean_text(value: str) -> str:
    return " ".join(re.sub(r"\[[^\]]*\]", "", value).split())


def extract_tables(html: str) -> dict[str, list[dict[str, str]]]:
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for table in soup.find_all("table"):
        headers = []
        records = []
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            if not cells:
                continue
            values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
            if all(cell.name == "th" for cell in cells):
                headers = values
                continue
            if headers and len(values) == len(headers):
                records.append(dict(zip(headers, values)))
        if not records or "Population" not in headers or "County" not in headers:
            continue
        kind = "cities" if any("City" in name or "Agency" in name for name in headers) else "counties"
        if kind in result:
            raise ValueError(f"More than one {kind} table matched; inspect the source schema")
        for record in records:
            for key, value in record.items():
                # Preserve labels and fractional rates; remove numeric grouping commas only.
                if re.fullmatch(r"-?\d[\d,]*(?:\.\d+)?", value):
                    record[key] = value.replace(",", "")
        result[kind] = records
    if set(result) != {"counties", "cities"}:
        raise ValueError("Expected county and city crime tables; source schema may have changed")
    return result


def export_tables(tables: dict[str, list[dict[str, str]]], output: Path) -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=True)
    counts = {}
    for kind, records in tables.items():
        with (output / f"{kind}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
        counts[kind] = len(records)
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Saved HTML for an offline, reproducible run")
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args(argv)
    if args.input:
        html = args.input.read_text(encoding="utf-8")
        source = str(args.input)
    else:
        response = requests.get(URL, timeout=30, headers={"User-Agent": "CaliforniaCrimeTables/1.0"})
        response.raise_for_status()
        html = response.text
        source = URL
    counts = export_tables(extract_tables(html), args.output)
    summary = {"source": source, "rows": counts}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
