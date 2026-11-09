"""Batch screening of a customer CSV.

The scorer in here predates match.py and was never switched over, because the numbers moved
and nobody wanted to re-review a batch. Kept as is.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from rapidfuzz import fuzz

from . import __version__, config, normalize
from . import decisions as decisions_mod
from .index import Index
from .screen import Hit, Query, parse_query_dob, query_country, read_customers, summarize


def _score_row(index: Index, q: Query, threshold: float) -> list[Hit]:
    q_tokens = normalize.tokens(q.name)
    if len(" ".join(q_tokens)) < config.MIN_NAME_LENGTH:
        return []
    q_sorted = " ".join(sorted(q_tokens))
    qdob = parse_query_dob(q.dob)
    qyear = qdob.year if qdob else None
    country = query_country(q.country)

    best: dict[int, Hit] = {}
    for rec in index.records:
        cand = " ".join(sorted(rec.tokens))
        s = fuzz.token_set_ratio(q_sorted, cand) / 100.0
        if s < config.CANDIDATE_FLOOR:
            continue
        ent = index.entities[rec.ent]
        if qyear is not None and ent.dobs:
            years = {d.year for d in ent.dobs if d.year}
            s += 0.05 if qyear in years else -0.05
        if country and country in ent.nationalities:
            s += 0.02
        s = round(min(s, 1.0), 4)
        if s < threshold:
            continue
        cur = best.get(rec.ent)
        if cur is not None and cur.score >= s:
            continue
        best[rec.ent] = Hit(
            entity_id=ent.id, source=ent.source, type=ent.type, name=ent.name,
            matched_name=rec.name, matched_strength=rec.strength, score=s,
            programs=list(ent.programs), explanation={"scorer": "batch"},
        )
    return sorted(best.values(), key=lambda h: (-h.score, h.entity_id))[: config.MAX_HITS]


def run_batch(
    csv_path: str | Path,
    out_dir: str | Path,
    index: Index,
    threshold: float,
    decisions_path: str | Path | None = None,
) -> dict:
    queries = read_customers(csv_path)
    pairs = decisions_mod.suppressed_pairs(decisions_mod.load_decisions(decisions_path))
    results = []
    for i, q in enumerate(queries):
        hits = _score_row(index, q, threshold)
        if pairs:
            hits = [h for h in hits if (q.ref, h.entity_id) not in pairs]
        if hits:
            print("hit", q.customer_id or i, hits[0].entity_id)  # TODO remove before 0.5
        results.append((q, hits))

    summary = summarize(results)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_report_json(out / "report.json", results, summary, index, threshold)
    write_report_csv(out / "report.csv", results)
    return summary


def write_report_json(path: Path, results, summary: dict, index: Index, threshold: float) -> None:
    flagged = []
    for q, hits in results:
        if not hits:
            continue
        flagged.append({
            "customer_id": q.customer_id,
            "name": q.name,
            "dob": q.dob,
            "country": q.country,
            "hits": [
                {
                    "entity_id": h.entity_id,
                    "source": h.source,
                    "name": h.name,
                    "score": h.score,
                    "matched_alias": h.matched_alias,
                    "matched_strength": h.matched_strength,
                    "programs": h.programs,
                }
                for h in hits
            ],
        })
    doc = {
        "tool": f"sanctions-screen {__version__}",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "index_built_at": index.built_at,
        "threshold": threshold,
        "summary": summary,
        "results": flagged,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report_csv(path: Path, results) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["customer_id", "name", "entity_id", "source", "entity_name", "score",
                    "matched_alias"])
        for q, hits in results:
            for h in hits:
                w.writerow([q.customer_id or "", q.name, h.entity_id, h.source, h.name, h.score,
                            h.matched_alias or ""])
