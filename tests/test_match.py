import pytest

from sanctions_screen import match


def test_identical_names_score_one():
    assert match.match_name("Ali Hassan", "Ali Hassan").score == 1.0


def test_token_order_does_not_matter():
    assert match.match_name("Hassan Ali", "Ali Hassan").score >= 0.99


def test_unrelated_names_score_low():
    assert match.match_name("Ali Hassan", "Maria Silva").score < 0.5


def test_small_typo_still_high():
    assert match.match_name("Mohamed Hassan", "Mohammed Hassan").score > 0.9


def test_strict_penalises_missing_tokens():
    balanced = match.match_name("Ali Hassan Omar", "Ali Hassan").score
    strict = match.match_name("Ali Hassan Omar", "Ali Hassan", mode="strict").score
    assert strict < balanced


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        match.match_name("a b", "a b", mode="loose")


def test_empty_query_scores_zero():
    assert match.match_name("", "Ali Hassan").score == 0.0


def test_score_in_range():
    s = match.match_name("Abd al Rahman Haddad", "Haddad, Abd al-Rahman")
    assert 0.0 <= s.score <= 1.0
