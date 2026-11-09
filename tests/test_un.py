from sanctions_screen import un


def test_load_un_counts(lists_dir):
    ents = un.load_un(lists_dir / "un_consolidated.xml")
    assert len(ents) > 300
    assert all(e.source == "un" for e in ents)


def test_load_un_ids_are_reference_numbers(lists_dir):
    ents = un.load_un(lists_dir / "un_consolidated.xml")
    assert ents[0].id == "un:" + ents[0].uid


def test_load_un_both_kinds(lists_dir):
    ents = un.load_un(lists_dir / "un_consolidated.xml")
    assert {"person", "organization"} <= {e.type for e in ents}


def test_load_un_original_script_alias_is_strong(lists_dir):
    ents = un.load_un(lists_dir / "un_consolidated.xml")
    with_alias = [e for e in ents if e.aliases]
    assert with_alias
    assert any(a.strength == "strong" for e in with_alias for a in e.aliases)
