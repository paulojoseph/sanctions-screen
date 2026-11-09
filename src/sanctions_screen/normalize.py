"""Normalização de nomes: tudo que entra no matching passa por aqui.

Pipeline: transliterar -> tirar acentos -> minúsculas -> pontuação vira espaço ->
tirar títulos (Mr, Sheikh...) e formas jurídicas (LLC, S.A....) -> tokens.
"""

from __future__ import annotations

import re
import unicodedata

import jellyfish

from .transliteration import to_latin

# letras que o NFKD não decompõe
_SPECIAL = {
    "ı": "i", "İ": "i", "ł": "l", "Ł": "l", "ø": "o", "Ø": "o", "đ": "d", "Đ": "d",
    "ß": "ss", "æ": "ae", "œ": "oe", "þ": "th", "ð": "d",
}

HONORIFICS = {
    "mr", "mrs", "ms", "miss", "dr", "prof", "professor", "eng", "engineer", "sr", "sra",
    "sheikh", "shaikh", "sheikha", "shaykh", "hajji", "haji", "haj", "hadj", "sayyid",
    "sayed", "seyyed", "syed", "mullah", "maulana", "ayatollah", "imam", "general", "gen",
    "colonel", "col", "major", "captain", "capt", "president", "minister", "don", "dona",
    "senor", "senora", "sir", "lord", "lady",
}

LEGAL_FORMS = {
    "llc", "ltd", "limited", "inc", "incorporated", "corp", "corporation", "co", "company",
    "gmbh", "ag", "sa", "sarl", "srl", "spa", "bv", "nv", "oy", "ab", "as", "jsc", "ojsc",
    "pjsc", "ooo", "zao", "oao", "ao", "ltda", "eireli", "plc", "llp", "fze", "fzco", "fzc",
    "dmcc", "pte", "pty", "bhd", "sdn", "kg", "anonim", "sirketi", "sti", "tic", "sanayi",
}

# partículas ibéricas não carregam informação nenhuma na comparação
_IBERIAN_PARTICLES = {"de", "da", "do", "das", "dos", "del", "y"}

_NON_WORD = re.compile(r"[^a-z0-9 ]+")
_SPACES = re.compile(r"\s+")


def fold(text: str) -> str:
    """Strip diacritics and casefold. Idempotent."""
    for src, dst in _SPECIAL.items():
        text = text.replace(src, dst)
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.casefold()


def normalize_text(name: str) -> str:
    """Lowercase ASCII string, single spaces. No honorific/legal stripping yet."""
    text = to_latin(name)
    text = fold(text)
    # S.A. / L.L.C. -> sa / llc ; apóstrofo some (O'Brien -> obrien, Ta'iz -> taiz)
    text = text.replace(".", "").replace("'", "").replace("’", "").replace("ʿ", "")
    text = text.replace("-", " ").replace("_", " ")
    text = _NON_WORD.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def strip_honorifics(tokens: list[str]) -> list[str]:
    i = 0
    while i < len(tokens) - 1 and tokens[i] in HONORIFICS:
        i += 1
    return tokens[i:]


def strip_legal_forms(tokens: list[str]) -> list[str]:
    end = len(tokens)
    while end > 1 and tokens[end - 1] in LEGAL_FORMS:
        end -= 1
    return tokens[:end]


def drop_iberian_particles(tokens: list[str]) -> list[str]:
    out: list[str] = []
    prev = ""
    for t in tokens:
        if t in _IBERIAN_PARTICLES:
            prev = t
            continue
        if t in {"la", "las", "los"} and prev == "de":
            prev = t
            continue
        out.append(t)
        prev = t
    return out or tokens


def tokens(name: str) -> list[str]:
    """Query-side tokens. 'al'/'el'/'bin'/'ibn' stay as tokens of their own."""
    toks = normalize_text(name).split(" ")
    toks = [t for t in toks if t]
    toks = strip_honorifics(toks)
    toks = strip_legal_forms(toks)
    return drop_iberian_particles(toks)


def sort_key(toks: list[str]) -> str:
    return " ".join(sorted(toks))


def phonetic_key(toks: list[str]) -> str:
    keys = [jellyfish.metaphone(t) for t in toks if t]
    return " ".join(sorted(k for k in keys if k))


def normalize(name: str) -> str:
    """Single normalized string, token order preserved."""
    return " ".join(tokens(name))
