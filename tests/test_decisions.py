from sanctions_screen import decisions


def test_customer_ref_prefers_id():
    assert decisions.customer_ref("C-1", "Ali Hassan") == "C-1"


def test_customer_ref_falls_back_to_name():
    assert decisions.customer_ref(None, "Ali  HASSAN") == "name:ali hassan"


def test_append_and_load(tmp_path):
    p = tmp_path / "d.jsonl"
    decisions.append_decision(p, "C-1", "ofac:1", "tester", "different person")
    decisions.append_decision(p, "C-2", "un:X.1", "tester", "different dob")
    loaded = decisions.load_decisions(p)
    assert len(loaded) == 2
    assert ("C-1", "ofac:1") in decisions.suppressed_pairs(loaded)


def test_load_missing_file_is_empty(tmp_path):
    assert decisions.load_decisions(tmp_path / "none.jsonl") == []


def test_bad_line_reports_line_number(tmp_path):
    import pytest
    p = tmp_path / "d.jsonl"
    p.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=":1:"):
        decisions.load_decisions(p)


def test_shipped_decisions_parse():
    from tests.conftest import ROOT
    loaded = decisions.load_decisions(ROOT / "data" / "decisions" / "decisions.jsonl")
    assert len(loaded) == 40
