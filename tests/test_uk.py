import pytest

from sanctions_screen import uk


def test_parse_uk_groups_rows(lists_dir):
    ents = uk.parse_uk(lists_dir / "uk_consolidated.csv")
    assert len(ents) > 300
    assert len({e.id for e in ents}) == len(ents)


def test_parse_uk_rejects_other_csv(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(uk.ParseError):
        uk.parse_uk(p)
