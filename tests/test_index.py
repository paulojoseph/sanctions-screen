from sanctions_screen import ofac
from sanctions_screen.index import build_index, load_index, save_index


def test_build_index_has_records(lists_dir):
    ents = ofac.load_sdn(lists_dir / "ofac_sdn.xml")
    idx = build_index(ents)
    assert len(idx.entities) == len(ents)
    assert len(idx.records) >= len(ents)


def test_index_roundtrip(tmp_path, lists_dir):
    idx = build_index(ofac.load_sdn(lists_dir / "ofac_sdn.xml"))
    path = tmp_path / "idx.json.gz"
    save_index(idx, path)
    back = load_index(path)
    assert len(back.entities) == len(idx.entities)
    assert back.sources == idx.sources

