# California crime table exporter

Turn county and city tables from Wikipedia HTML into clean CSV files. The exporter selects tables by their headers, removes citation markers, and preserves fractional crime rates. It fails explicitly when the source schema no longer matches.

```sh
python -m pip install -r requirements.txt
# Offline example using fictional test records:
python Crime-Web-Scraping.py --input examples/crime-tables.html --output output
# Fetch the current Wikipedia page:
python Crime-Web-Scraping.py --output output
python -m unittest discover -s tests -v
```

Outputs: `output/counties.csv`, `output/cities.csv`, and `output/summary.json` with source and row counts. The example HTML contains fictional values for software testing. Live values retain the source page's reporting period; they are not current crime estimates. Network requests have a 30-second timeout and propagate HTTP failures.
