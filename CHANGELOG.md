# Changelog

## 0.4.0
- `diff` command to compare two list snapshots.
- `serve` command and `POST /screen`, `GET /health`.
- Reviewer decisions (`decisions.jsonl`) suppress known false positives per customer.
- Stale-list warning when a source is older than 14 days.
- Confidence bands and review priority in reports.

## 0.3.0
- `batch` command with `report.json` and `report.csv`.
- Local watchlist (`data/lists/local_watchlist.csv`).
- Weak aliases are scored but never boost a hit.

## 0.2.0
- EU and UK parsers.
- Phonetic key (metaphone) in the score.
- Arabic and Cyrillic transliteration.

## 0.1.2
- Golden file for the example customers, reviewed by two analysts.

## 0.1.0
- OFAC and UN parsers, first fuzzy matching, flat CSV report (see `legacy_csv_report.py`).
