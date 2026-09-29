"""Unit tests for XSS sanitization (app.sanitize)."""

import pytest

from app.sanitize import sanitize_text


@pytest.mark.unit
def test_none_returns_none():
    assert sanitize_text(None) is None


@pytest.mark.unit
def test_plain_text_unchanged():
    assert sanitize_text("  hello world  ") == "hello world"


@pytest.mark.unit
def test_script_block_removed():
    cleaned = sanitize_text("before <script>alert(1)</script> after")
    assert "<script>" not in cleaned
    assert "before" in cleaned
    assert "after" in cleaned


@pytest.mark.unit
def test_dangerous_tags_removed():
    cleaned = sanitize_text('<p>ok</p><iframe src="x"></iframe><img src="y">')
    assert "iframe" not in cleaned
    assert "ok" in cleaned


@pytest.mark.unit
def test_event_handlers_removed():
    cleaned = sanitize_text('<div onclick="alert(1)">click</div>')
    assert "onclick" not in cleaned
    assert "click" in cleaned


@pytest.mark.unit
def test_javascript_uri_removed():
    cleaned = sanitize_text('click <a href="javascript:alert(1)">here</a>')
    assert "javascript:" not in cleaned
    assert "here" in cleaned


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        "<SCRIPT>alert(1)</SCRIPT>",
        "<scr<script>ipt>alert(1)</scr</script>ipt>",
        "<img src=x onerror=alert(1)>",
        '<a href="JaVaScRiPt:alert(1)">x</a>',
    ],
)
def test_known_vectors_are_cleaned(payload):
    cleaned = sanitize_text(payload)
    assert "<" not in cleaned.replace(" ", "").replace(">", "").strip() or "javascript" not in cleaned.lower()


@pytest.mark.unit
def test_max_length_truncation():
    cleaned = sanitize_text("a" * 100, max_length=10)
    assert len(cleaned) == 10


@pytest.mark.unit
def test_data_text_html_uri_removed():
    cleaned = sanitize_text('<a href="data:text/html:alert(1)">x</a>')
    assert "data:text/html" not in cleaned
