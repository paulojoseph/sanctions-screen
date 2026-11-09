from sanctions_screen import eu


def test_parse_eu_counts(lists_dir):
    ents = eu.parse_eu(lists_dir / "eu_fsf.xml")
    assert len(ents) > 300
    assert all(e.id.startswith("eu:") for e in ents)


def test_parse_eu_missing_file_raises(tmp_path):
    import pytest
    with pytest.raises(eu.ParseError):
        eu.parse_eu(tmp_path / "nope.xml")
