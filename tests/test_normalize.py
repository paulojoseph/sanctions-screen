from sanctions_screen import normalize


def test_fold_removes_diacritics():
    assert normalize.fold("José Ñandú Çelik") == "jose nandu celik"


def test_normalize_text_strips_punctuation():
    assert normalize.normalize_text("O'Brien-Smith, Jr.") == "obrien smith jr"


def test_tokens_basic():
    assert normalize.tokens("José María Ñandú") == ["jose", "maria", "nandu"]


def test_honorifics_removed():
    assert normalize.tokens("Dr. Ahmed Hassan") == ["ahmed", "hassan"]


def test_legal_forms_removed():
    assert normalize.normalize("ACME Trading Ltd.") == "acme trading"


def test_legal_forms_removed_portuguese():
    assert "ltda" not in normalize.tokens("Atlas Comércio Ltda")


def test_sort_key_is_order_insensitive():
    a = normalize.sort_key(normalize.tokens("Haddad Abd Rahman"))
    b = normalize.sort_key(normalize.tokens("Rahman Abd Haddad"))
    assert a == b


def test_phonetic_key_equal_for_spelling_variants():
    a = normalize.phonetic_key(normalize.tokens("Mohammed"))
    b = normalize.phonetic_key(normalize.tokens("Muhammad"))
    assert a == b


def test_empty_string():
    assert normalize.tokens("") == []
    assert normalize.normalize("   ") == ""
