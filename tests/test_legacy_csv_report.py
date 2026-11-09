from sanctions_screen import legacy_csv_report as lr


def test_format_hit_cell():
    assert lr.format_hit_cell("ofac:1", 0.9) == "ofac:1@0.90"


def test_roundtrip(tmp_path):
    rows = [
        {"customer_id": "C-1", "name": "Ali", "hits": [("ofac:1", 0.9), ("un:2", 0.95)]},
        {"customer_id": "C-2", "name": "Bea", "hits": []},
    ]
    p = tmp_path / "legacy.csv"
    assert lr.write_legacy_report(p, rows) == 2
    back = lr.read_legacy_report(p)
    assert back[0]["hits"][0][0] == "un:2"
    assert back[1]["hits"] == []
