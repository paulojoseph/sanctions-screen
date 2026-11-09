"""Compares the library screening path against the hand-reviewed expected hits."""
import json

import pytest

from sanctions_screen import screen
from tests.conftest import EXAMPLES, LISTS, ROOT

GOLDEN = ROOT / "tests" / "golden" / "expected_hits.json"


def test_golden_hits():
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))["customers"]
    index = screen.get_index(LISTS)
    for q in screen.read_customers(EXAMPLES / "customers_small.csv"):
        hits = screen.screen_name(
            index, q.name, dob=q.dob, country=q.country, customer_id=q.customer_id,
            decisions_path=None,
        )
        want = expected[q.customer_id]
        assert [h.entity_id for h in hits] == [w["entity_id"] for w in want], q.customer_id
        for h, w in zip(hits, want, strict=True):
            assert h.score == pytest.approx(w["score"], abs=0.0005), (q.customer_id, h.entity_id)
