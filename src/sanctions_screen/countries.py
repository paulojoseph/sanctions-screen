"""Country name -> ISO 3166 alpha-2. Only what the four lists actually use."""

_COUNTRIES = {
    "AF": ["afghanistan"],
    "BR": ["brazil", "brasil"],
    "BY": ["belarus"],
    "CN": ["china", "people's republic of china"],
    "CU": ["cuba"],
    "ES": ["spain", "espana"],
    "IQ": ["iraq"],
    "IR": ["iran", "iran (islamic republic of)", "islamic republic of iran"],
    "KP": ["north korea", "democratic people's republic of korea", "korea, north"],
    "LB": ["lebanon"],
    "LY": ["libya", "libyan arab jamahiriya"],
    "MM": ["burma", "myanmar"],
    "PK": ["pakistan"],
    "PT": ["portugal"],
    "RU": ["russia", "russian federation"],
    "SD": ["sudan"],
    "SO": ["somalia"],
    "SY": ["syria", "syrian arab republic"],
    "TR": ["turkey", "turkiye", "türkiye"],
    "VE": ["venezuela"],
    "YE": ["yemen"],
}

_BY_NAME = {n: code for code, names in _COUNTRIES.items() for n in names}
ALL_CODES = sorted(_COUNTRIES)


def to_iso2(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    if len(v) == 2 and v.upper() in _COUNTRIES:
        return v.upper()
    return _BY_NAME.get(v)


def primary_name(code: str) -> str:
    return _COUNTRIES[code][0].title()
