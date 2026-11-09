import json

from sanctions_screen import batch, screen
from tests.conftest import EXAMPLES, LISTS


def test_batch_small_writes_reports(tmp_path):
    idx = screen.get_index(LISTS)
    summary = batch.run_batch(EXAMPLES / "customers_small.csv", tmp_path, idx, 0.8)
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.csv").exists()
    assert summary["rows"] == 50


def test_batch_report_json_shape(tmp_path):
    idx = screen.get_index(LISTS)
    batch.run_batch(EXAMPLES / "customers_small.csv", tmp_path, idx, 0.8)
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert "summary" in data and "results" in data


def test_batch_decisions_suppress(tmp_path):
    from sanctions_screen import decisions
    idx = screen.get_index(LISTS)
    d = tmp_path / "d.jsonl"
    batch.run_batch(EXAMPLES / "customers_small.csv", tmp_path / "a", idx, 0.8)
    first = json.loads((tmp_path / "a" / "report.json").read_text(encoding="utf-8"))
    row = next(r for r in first["results"] if r["hits"])
    decisions.append_decision(d, row["customer_id"], row["hits"][0]["entity_id"], "t", "x")
    batch.run_batch(EXAMPLES / "customers_small.csv", tmp_path / "b", idx, 0.8, d)
    second = json.loads((tmp_path / "b" / "report.json").read_text(encoding="utf-8"))
    again = next(r for r in second["results"] if r["customer_id"] == row["customer_id"])
    assert row["hits"][0]["entity_id"] not in [h["entity_id"] for h in again["hits"]]


def test_batch_10k_runs_and_finds_planted(tmp_path):
    idx = screen.get_index(LISTS)
    summary = batch.run_batch(EXAMPLES / "customers_10k.csv", tmp_path, idx, 0.8)
    assert summary["rows"] == 10000
    assert 100 < summary["rows_with_hits"] < 1500
