from sanctions_screen import transliteration as tr


def test_has_cyrillic():
    assert tr.has_cyrillic("Иван")
    assert not tr.has_cyrillic("Ivan")


def test_has_arabic():
    assert tr.has_arabic("محمد")
    assert not tr.has_arabic("Mohammed")


def test_cyrillic_simple():
    assert tr.cyrillic_to_latin("Иван Петров") == "ivan petrov"


def test_cyrillic_yulia():
    # matches how the bank's legacy system spells it
    assert tr.cyrillic_to_latin("Юлия Щербаков") == "julija scherbakov"


def test_to_latin_passthrough():
    assert tr.to_latin("Plain Latin") == "Plain Latin"


def test_arabic_produces_latin_letters():
    out = tr.to_latin("محمد")
    assert out and out.isascii()
