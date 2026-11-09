"""Name-to-name scoring."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from . import config, normalize

MODES = ("strict", "balanced", "broad")


@dataclass(frozen=True)
class MatchScore:
    score: float
    sort_jw: float
    coverage: float
    phonetic: float
    mode: str


def _coverage(a: list[str], b: list[str]) -> float:
    """Share of the characters of `a` that sit in tokens with a close partner in `b`."""
    total = sum(len(t) for t in a)
    if not total:
        return 0.0
    hit = 0
    for t in a:
        best = 0.0
        for u in b:
            s = JaroWinkler.similarity(t, u)
            if s > best:
                best = s
        if best >= config.TOKEN_MATCH_MIN:
            hit += len(t)
    return hit / total


def score_tokens(
    q: list[str], c: list[str], q_phon: str, c_phon: str, mode: str = "balanced"
) -> MatchScore:
    if not q or not c:
        return MatchScore(0.0, 0.0, 0.0, 0.0, mode)
    sort_jw = JaroWinkler.similarity(normalize.sort_key(q), normalize.sort_key(c))
    cov_q = _coverage(q, c)
    cov_c = _coverage(c, q)
    coverage = 0.5 * (cov_q + cov_c)
    if q_phon == c_phon:
        phon = 1.0
    else:
        phon = fuzz.ratio(q_phon, c_phon) / 100.0
    score = config.W_SORT * sort_jw + config.W_COVERAGE * coverage + config.W_PHONETIC * phon
    if mode == "strict" and cov_q < config.STRICT_MIN_COVERAGE:
        score *= 0.5
    return MatchScore(round(score, 4), round(sort_jw, 4), round(coverage, 4), round(phon, 4), mode)


def match_name(query: str, candidate: str, mode: str = "balanced") -> MatchScore:
    """Score how well `query` matches `candidate`, from 0.0 to 1.0.

    Modes:
      strict    every token of the query has to find a partner in the candidate,
                otherwise the score is halved
      balanced  blend of order-insensitive similarity, token coverage and phonetic key
      broad     like balanced, but also keeps single-token overlaps (surname only) and
                phonetic-only matches
    """
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}, expected one of {MODES}")
    q = normalize.tokens(query)
    c = normalize.tokens(candidate)
    return score_tokens(q, c, normalize.phonetic_key(q), normalize.phonetic_key(c), mode)
