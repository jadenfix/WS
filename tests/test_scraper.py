import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("crime_scraper", ROOT / "Crime-Web-Scraping.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ScraperTests(unittest.TestCase):
    def test_named_tables_clean_citations_and_preserve_rates(self):
        tables = module.extract_tables((ROOT / "examples/crime-tables.html").read_text())
        self.assertEqual(tables["counties"][0]["County"], "Example County")
        self.assertEqual(tables["counties"][0]["Population"], "12345")
        self.assertEqual(tables["counties"][0]["Violent crime rate per 1,000 persons"], "1.38")
        self.assertEqual(tables["cities"][0]["City/Agency"], "Example City")

    def test_missing_schema_fails(self):
        with self.assertRaisesRegex(ValueError, "source schema"):
            module.extract_tables("<table><tr><th>Other</th></tr></table>")

    def test_offline_cli_exports_csv(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, str(ROOT / "Crime-Web-Scraping.py"),
                            "--input", str(ROOT / "examples/crime-tables.html"),
                            "--output", directory], check=True, capture_output=True)
            self.assertEqual(json.loads((Path(directory) / "summary.json").read_text())["rows"],
                             {"counties": 1, "cities": 1})
            with (Path(directory) / "counties.csv").open() as handle:
                self.assertEqual(list(csv.DictReader(handle))[0]["Population"], "12345")
