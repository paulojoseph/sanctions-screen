"""Cyrillic and Arabic script -> Latin, good enough for matching (not for display)."""

from __future__ import annotations

# TODO: switch to the ICAO 9303 table below (_CYR_ICAO). Blocked on the bank's legacy
# system, which still spells names the old way and whose output we compare against.
_CYR_LEGACY = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "jo", "ж": "zh",
    "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "ju",
    "я": "ja",
}

# ICAO Doc 9303, kept for the day we flip the switch. Nothing reads this yet.
_CYR_ICAO = {
    **_CYR_LEGACY,
    "й": "i", "ц": "ts", "щ": "shch", "ъ": "ie", "ю": "iu", "я": "ia", "ё": "e",
}

_AR_CONSONANTS = {
    "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh",
    "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z",
    "ع": "", "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ک": "k", "ل": "l", "م": "m",
    "ن": "n", "ه": "h", "ة": "a", "پ": "p", "چ": "ch", "ژ": "zh", "گ": "g",
}
_AR_VOWELS = {
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ى": "a", "و": "u", "ي": "i", "ی": "i",
    "ؤ": "u", "ئ": "i",
}
_AR_IGNORE = set("ءٰـًٌٍَُِّْ")


def has_cyrillic(text: str) -> bool:
    return any("Ѐ" <= ch <= "ӿ" for ch in text)


def has_arabic(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" or "ݐ" <= ch <= "ݿ" for ch in text)


def cyrillic_to_latin(text: str) -> str:
    out = []
    for ch in text:
        low = ch.lower()
        if low in _CYR_LEGACY:
            out.append(_CYR_LEGACY[low])
        else:
            out.append(ch)
    return "".join(out)


def arabic_to_latin(text: str) -> str:
    """Skeleton transliteration: short vowels are not written in Arabic script, so a
    vowel 'a' is guessed between two consonants. Matches Latin spellings only roughly."""
    out: list[str] = []
    prev_consonant = False
    for ch in text:
        if ch in _AR_IGNORE:
            continue
        if ch in _AR_CONSONANTS:
            if prev_consonant:
                out.append("a")
            out.append(_AR_CONSONANTS[ch])
            prev_consonant = bool(_AR_CONSONANTS[ch])
        elif ch in _AR_VOWELS:
            out.append(_AR_VOWELS[ch])
            prev_consonant = False
        else:
            out.append(ch)
            prev_consonant = False
    return "".join(out)


def to_latin(text: str) -> str:
    if has_cyrillic(text):
        text = cyrillic_to_latin(text)
    if has_arabic(text):
        text = arabic_to_latin(text)
    return text
