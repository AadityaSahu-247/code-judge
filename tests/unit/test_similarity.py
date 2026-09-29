"""Unit tests for text/code similarity helpers (app.services.similarity)."""

import pytest

from app.services.similarity import code_similarity, jaccard, text_similarity


@pytest.mark.unit
def test_jaccard_basic():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a"}, {"a", "b"}) == 0.5
    assert jaccard({"a"}, {"b"}) == 0.0


@pytest.mark.unit
def test_jaccard_empty_sets():
    assert jaccard(set(), set()) == 0.0
    assert jaccard(set(), {"a"}) == 0.0


@pytest.mark.unit
def test_identical_text_is_1():
    assert text_similarity("the quick brown fox jumps", "the quick brown fox jumps") == 1.0


@pytest.mark.unit
def test_disjoint_text_is_0():
    assert text_similarity("banana apple pie", "zzzz qqqq xxxx") == 0.0


@pytest.mark.unit
def test_text_case_and_stopwords_insensitive():
    # Stop words are stripped, so this should be > 0.
    sim = text_similarity("Why does my loop never end", "my loop never ends")
    assert sim > 0


@pytest.mark.unit
def test_identical_code_is_1():
    src = "a, b = map(int, input().split())\nprint(a + b)"
    assert code_similarity(src, src) == 1.0


@pytest.mark.unit
def test_copied_code_with_comment_changes_is_high():
    a = "x = int(input())\nprint(x * 2)"
    b = "# my answer\nx = int(input())\nprint(x * 2)  # output"
    assert code_similarity(a, b) > 0.5


@pytest.mark.unit
def test_distinct_code_is_low():
    a = "for i in range(10): print(i)"
    b = "return sum(1 for x in items if x > 0)"
    assert code_similarity(a, b) < 0.5


@pytest.mark.unit
def test_short_code_handled_gracefully():
    assert code_similarity("a", "b") == 0.0
    assert code_similarity("a", "a") == 1.0
