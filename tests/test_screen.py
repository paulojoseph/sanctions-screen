import pytest

from sanctions_screen import screen
from tests.conftest import EXAMPLES, LISTS


def test_parse_query_dob_formats():
    assert screen.parse_query_dob("1971").kind == "year"
    assert screen.parse_query_dob("1971-03-12").kind == "full"
    assert screen.parse_query_dob("12/03/1971").month == 3
    assert screen.parse_query_dob("circa 1971").kind == "circa"
    assert screen.parse_query_dob("") is None


def test_parse_query_dob_garbage():
    assert screen.parse_query_dob("not a date") is None


def test_get_index_builds_from_directory():
    idx = screen.get_index(LISTS)
    assert set(idx.sources) >= {"ofac", "un", "eu", "uk"}


def test_get_index_is_cached():
    # relies on the index loaded by an earlier test in the session
    cached = screen._INDEX_CACHE[str(LISTS)]
    assert screen.get_index(LISTS) is cached


def test_get_index_missing_path():
    with pytest.raises(FileNotFoundError):
        screen.get_index("/nonexistent/path")


def test_exact_name_hits_with_high_score():
    idx = screen.get_index(LISTS)
    name = idx.entities[0].name
    hits = screen.screen_name(idx, name, decisions_path=None)
    assert hits and hits[0].score >= 0.95


def test_threshold_filters_hits():
    idx = screen.get_index(LISTS)
    name = idx.entities[0].name
    loose = screen.screen_name(idx, name, threshold=0.5, decisions_path=None)
    tight = screen.screen_name(idx, name, threshold=0.99, decisions_path=None)
    assert len(tight) <= len(loose)


def test_unrelated_name_no_hits():
    idx = screen.get_index(LISTS)
    assert screen.screen_name(idx, "Zzyzx Qwerty", decisions_path=None) == []


def test_decisions_suppress_hit(tmp_path):
    from sanctions_screen import decisions
    idx = screen.get_index(LISTS)
    ent = idx.entities[0]
    p = tmp_path / "d.jsonl"
    decisions.append_decision(p, "C-9", ent.id, "t", "different person")
    hits = screen.screen_name(idx, ent.name, customer_id="C-9", decisions_path=p)
    assert ent.id not in [h.entity_id for h in hits]


def test_decisions_are_per_customer(tmp_path):
    from sanctions_screen import decisions
    idx = screen.get_index(LISTS)
    ent = idx.entities[0]
    p = tmp_path / "d.jsonl"
    decisions.append_decision(p, "C-9", ent.id, "t", "different person")
    hits = screen.screen_name(idx, ent.name, customer_id="C-10", decisions_path=p)
    assert ent.id in [h.entity_id for h in hits]


def test_dob_exact_mismatch_lowers_score():
    idx = screen.get_index(LISTS)
    ent = next(e for e in idx.entities if any(d.kind == "full" for d in e.dobs))
    d = next(d for d in ent.dobs if d.kind == "full")
    good = screen.screen_name(idx, ent.name, dob=d.as_date().isoformat(), decisions_path=None)
    bad = screen.screen_name(idx, ent.name, dob=f"{d.year - 15}-06-30", decisions_path=None)
    g = next(h for h in good if h.entity_id == ent.id)
    b = [h for h in bad if h.entity_id == ent.id]
    assert not b or b[0].score < g.score


def test_hits_to_json_is_valid(tmp_path):
    import json
    idx = screen.get_index(LISTS)
    hits = screen.screen_name(idx, idx.entities[0].name, decisions_path=None)
    json.loads(screen.hits_to_json(hits))


def test_library_path_on_customer_sample():
    idx = screen.get_index(LISTS)
    queries = screen.read_customers(EXAMPLES / "customers_10k.csv")[:1000]
    flagged = 0
    for q in queries:
        hits = screen.screen_name(idx, q.name, dob=q.dob, country=q.country,
                                  customer_id=q.customer_id, decisions_path=None)
        flagged += bool(hits)
    assert 5 < flagged < 200
