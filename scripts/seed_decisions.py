"""Writes data/decisions/decisions.jsonl with the reviewer decisions we ship as examples.

The decisions are deterministic picks from real hits on the example customer files, so
the entity ids exist in the fixture lists. Run once; it refuses to overwrite.
"""
import json
import random
import sys
from pathlib import Path

from sanctions_screen import screen

OUT = Path("data/decisions/decisions.jsonl")
REVIEWERS = ["m.ferreira", "j.okafor", "a.lindqvist"]
REASONS = [
    "DOB differs by more than a year, different person",
    "country of residence and nationality do not match the listed party",
    "common name, no secondary identifiers in common",
    "ID document number does not match",
    "customer onboarded with passport, listed party has different document",
    "name matches only on given names",
]


def main() -> int:
    if OUT.exists():
        print(f"{OUT} already exists, not overwriting", file=sys.stderr)
        return 1
    rng = random.Random(7)
    index = screen.get_index("tests/fixtures/lists")
    rows = []
    for path, limit, want in (("examples/customers_10k.csv", 2500, 37),
                              ("examples/customers_small.csv", 50, 3)):
        found = []
        for q in screen.read_customers(path)[:limit]:
            hits = screen.screen_name(index, q.name, dob=q.dob, country=q.country,
                                      customer_id=q.customer_id, decisions_path=None)
            for h in hits[:1]:
                found.append((q.customer_id, h.entity_id))
        rows.extend(rng.sample(found, min(want, len(found))))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    day = 3
    with open(OUT, "w", encoding="utf-8") as fh:
        for i, (cust, ent) in enumerate(rows):
            rec = {"customer_ref": cust, "entity_id": ent, "decision": "not_a_match",
                   "reviewer": REVIEWERS[i % 3], "reason": rng.choice(REASONS),
                   "decided_at": f"2025-0{3 + i // 14}-{day + (i * 2) % 25:02d}T1{i % 8}:2{i % 6}:00+00:00"}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} decisions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
