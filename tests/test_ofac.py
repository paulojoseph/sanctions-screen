from sanctions_screen import ofac


def test_parse_dob_variants():
    assert ofac.parse_dob_text("12 Mar 1971").kind == "full"
    assert ofac.parse_dob_text("1971").kind == "year"
    assert ofac.parse_dob_text("circa 1971").kind == "circa"


def test_load_sdn_counts(lists_dir):
    ents = ofac.load_sdn(lists_dir / "ofac_sdn.xml")
    assert len(ents) > 300
    assert all(e.id.startswith("ofac:") for e in ents)


def test_load_sdn_types(lists_dir):
    ents = ofac.load_sdn(lists_dir / "ofac_sdn.xml")
    assert {"person", "organization"} <= {e.type for e in ents}


def test_load_sdn_has_list_date(lists_dir):
    ents = ofac.load_sdn(lists_dir / "ofac_sdn.xml")
    assert ents[0].list_date == "2025-03-14"
