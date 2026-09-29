"""Unit tests for AI feedback response parsing (no DB, no network)."""

import json

import pytest

from app.services.ai_feedback import (
    FALLBACK,
    _call_mock,
    _parse_and_validate,
    _parse_lenient,
    _strip_code_fences,
)


@pytest.mark.unit
def test_strip_code_fences():
    assert _strip_code_fences("```json\n{\"a\": 1}\n```") == "{\"a\": 1}"
    assert _strip_code_fences("```\nplain\n```") == "plain"
    assert _strip_code_fences("plain") == "plain"


@pytest.mark.unit
def test_parse_and_validate_happy_path():
    raw = json.dumps(
        {
            "readability": "Good",
            "complexity": "O(1)",
            "best_practices": "Nice",
            "optimization": "None",
        }
    )
    parsed = _parse_and_validate(raw)
    assert parsed == {
        "readability": "Good",
        "complexity": "O(1)",
        "best_practices": "Nice",
        "optimization": "None",
    }


@pytest.mark.unit
def test_parse_and_validate_missing_fields_fall_back():
    parsed = _parse_and_validate(json.dumps({"readability": "ok"}))
    assert parsed["readability"] == "ok"
    assert parsed["complexity"] == FALLBACK["complexity"]
    assert parsed["optimization"] == FALLBACK["optimization"]


@pytest.mark.unit
def test_parse_and_validate_non_dict_raises():
    with pytest.raises(ValueError):
        _parse_and_validate("[1, 2, 3]")


@pytest.mark.unit
def test_parse_and_validate_malformed_json_raises():
    with pytest.raises(ValueError):
        _parse_and_validate("{not json")


@pytest.mark.unit
def test_parse_lenient_truncated():
    truncated = '{"readability": "Good code but truncated'
    parsed = _parse_lenient(truncated)
    assert parsed["readability"] == "Good code but truncated"
    assert parsed["complexity"] == FALLBACK["complexity"]


@pytest.mark.unit
def test_parse_lenient_handles_escapes():
    parsed = _parse_lenient('{"best_practices": "use \\"quotes\\" and \\n newline"')
    assert "quotes" in parsed["best_practices"]


@pytest.mark.unit
def test_call_mock_returns_valid_feedback_json():
    raw = _call_mock()
    parsed = json.loads(raw)
    assert set(parsed) == {"readability", "complexity", "best_practices", "optimization"}


@pytest.mark.unit
def test_call_provider_uses_gateway_when_available(mock_gateway):
    from tests.fixtures.app import make_completion_result

    mock_gateway["available"] = 1
    mock_gateway["results"].append(
        make_completion_result(json.dumps({"readability": "ok"}))
    )
    from app.services.ai_feedback import _call_provider

    content, model = _call_provider("sys", "user")
    assert model == "mock/gemini#0"
    assert mock_gateway["calls"][0][1]["json_mode"] is True


@pytest.mark.unit
def test_call_provider_falls_back_to_mock_when_unavailable(mock_gateway):
    mock_gateway["available"] = 0
    from app.services.ai_feedback import _call_provider

    content, model = _call_provider("sys", "user")
    assert model == "mock-gemini-2.5-flash"
    assert "readability" in content
    assert mock_gateway["calls"] == []


@pytest.mark.unit
def test_parse_lenient_corrupted_escape_uses_raw():
    from app.services.ai_feedback import _parse_lenient

    parsed = _parse_lenient('{"complexity": "O(n) \\')
    assert parsed["complexity"] in ("O(n) ", "O(n) \\")
    assert parsed["readability"] == FALLBACK["readability"]
