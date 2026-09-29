"""Unit tests for the grading service helpers (no docker, no database)."""

import pytest

from app.models import Verdict
from app.services.grading import (
    LANGUAGES,
    _compute_verdict,
    _normalize_output,
    _outputs_match,
    _run_command,
    _verdict_from_exit_code,
    supported_languages,
)


@pytest.mark.unit
def test_supported_languages_sorted():
    assert supported_languages() == sorted(LANGUAGES.keys())
    assert "python" in LANGUAGES
    assert "javascript" in LANGUAGES


@pytest.mark.unit
def test_language_configs_are_sandbox_safe():
    for config in LANGUAGES.values():
        assert config["image"].startswith("codejudge/sandbox-") or config["image"].startswith("kgmp/sandbox-")
        assert config["run"]


@pytest.mark.unit
def test_normalize_output_strips_trailing_whitespace():
    assert _normalize_output("5\n") == "5"
    assert _normalize_output("a  \nb\t\n") == "ab"
    assert _normalize_output("") == ""


@pytest.mark.unit
@pytest.mark.parametrize(
    "actual,expected",
    [
        ("5\n", "5"),
        ("5", "5"),
        ("5 \n\t", "5"),
        ("a\nb", "a\nb\n"),
        ("a", "b"),
        ("", "x"),
    ],
)
def test_outputs_match(actual, expected):
    assert _outputs_match(actual, expected) == (actual.strip() == expected.strip())


@pytest.mark.unit
@pytest.mark.parametrize(
    "rc,expected",
    [
        (0, Verdict.accepted),
        (1, Verdict.runtime_error),
        (124, Verdict.time_limit_exceeded),
        (137, Verdict.memory_limit_exceeded),
        (139, Verdict.runtime_error),
    ],
)
def test_verdict_from_exit_code(rc, expected):
    assert _verdict_from_exit_code(rc) == expected


@pytest.mark.unit
def test_compute_verdict_all_passed():
    passed = _case(True, Verdict.accepted)
    assert _compute_verdict([passed, passed]) == Verdict.accepted


@pytest.mark.unit
def test_compute_verdict_first_failure_wins():
    from app.services.grading import CaseResult

    tle = CaseResult(1, False, Verdict.time_limit_exceeded, "", 10)
    wrong = _case(False, Verdict.wrong_answer)
    assert _compute_verdict([wrong, tle]) == Verdict.wrong_answer
    assert _compute_verdict([tle, wrong]) == Verdict.time_limit_exceeded


@pytest.mark.unit
def test_compute_verdict_runtime_error():
    assert _compute_verdict([_case(False, Verdict.runtime_error)]) == Verdict.runtime_error


@pytest.mark.unit
def test_run_command_builds_timeout_pipeline():
    config = LANGUAGES["python"]
    cmd = _run_command(config)
    assert cmd[0] == "timeout"
    assert cmd[-1].startswith("python3 /sandbox/main.py")
    assert "| head -c" in cmd[-1]


@pytest.mark.unit
def test_compute_verdict_falls_back_to_wrong_answer():
    """accepted verdict with passed=False maps to wrong_answer."""
    from app.services.grading import CaseResult

    weird = CaseResult(1, False, Verdict.accepted, "x", 1)
    assert _compute_verdict([weird]) == Verdict.wrong_answer


@pytest.mark.unit
def test_truncate_limits_output():
    from app.services.grading import STORE_OUTPUT_CHARS, _truncate

    long = "a" * (STORE_OUTPUT_CHARS + 100)
    assert len(_truncate(long)) == STORE_OUTPUT_CHARS


@pytest.mark.unit
def test_normalize_output_empty_lines():
    assert _normalize_output("\n\n") == ""
    assert _normalize_output("a\n\n\n") == "a"


def _case(passed, verdict):
    from app.services.grading import CaseResult

    return CaseResult(
        test_case_id=1,
        passed=passed,
        verdict=verdict,
        actual_output="out",
        exec_time_ms=1,
    )
