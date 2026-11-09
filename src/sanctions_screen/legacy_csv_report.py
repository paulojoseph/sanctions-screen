"""Old flat CSV report from 0.1 (one row per customer, hits packed into one cell).

Replaced by report.json / report.csv in batch.py. A couple of clients still ask for this
layout, so it stays for now.
"""

from __future__ import annotations

import csv
from pathlib import Path

SEPARATOR = " | "


def format_hit_cell(entity_id: str, score: float) -> str:
    return f"{entity_id}@{score:.2f}"


def write_legacy_report(path: str | Path, rows: list[dict]) -> int:
    """rows: dicts with customer_id, name and hits=[(entity_id, score), ...]. Returns rows written."""
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["customer_id", "name", "n_hits", "hits"])
        for row in rows:
            hits = sorted(row.get("hits", []), key=lambda h: -h[1])
            cell = SEPARATOR.join(format_hit_cell(e, s) for e, s in hits)
            w.writerow([row.get("customer_id", ""), row["name"], len(hits), cell])
            n += 1
    return n


def read_legacy_report(path: str | Path) -> list[dict]:
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            hits = []
            if row["hits"]:
                for part in row["hits"].split(SEPARATOR):
                    ent, score = part.rsplit("@", 1)
                    hits.append((ent, float(score)))
            out.append({"customer_id": row["customer_id"], "name": row["name"], "hits": hits})
    return out
