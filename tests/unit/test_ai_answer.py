"""Unit tests for the AI answer service helpers (no DB, no network)."""

import pytest

from app.config import settings
from app.services.ai_answer import (
    MOCK_ANSWER,
    SYSTEM_PROMPT,
    _build_prompt,
    _call_provider,
    _moderation_check,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "text,expected",
    [
        ("I need help with loops", False),
        ("please do not kill yourself", True),
        ("How to build a bomb?", True),
        ("normal question about sorting", False),
        ("self harm resources", True),
    ],
)
def test_moderation_check(text, expected):
    flagged, reason = _moderation_check(text)
    assert flagged is expected
    if expected:
        assert reason is not None
    else:
        assert reason is None


@pytest.mark.unit
def test_build_prompt_delimiters_and_blocks():
    from types import SimpleNamespace

    doubt = SimpleNamespace(
        title="Why does my loop never end?",
        description="It loops forever.",
        code_snippet="while True: pass",
    )
    problem = SimpleNamespace(statement="Print N numbers.")
    prompt = _build_prompt(doubt, problem, db=None, teacher_note=None)
    assert "----- STUDENT CONTENT START -----" in prompt
    assert "----- STUDENT CONTENT END -----" in prompt
    assert "Print N numbers." in prompt
    assert "while True: pass" in prompt
    assert "Why does my loop never end?" in prompt


@pytest.mark.unit
def test_build_prompt_with_teacher_note():
    from types import SimpleNamespace

    doubt = SimpleNamespace(
        title="T", description="D", code_snippet=None, related_problem_id=None
    )
    prompt = _build_prompt(doubt, None, db=None, teacher_note="Be more concise.")
    assert "TEACHER NOTE FROM PREVIOUS REJECTION" in prompt
    assert "Be more concise." in prompt


@pytest.mark.unit
def test_call_provider_uses_mock_when_no_keys():
    """With no API keys configured the service must use the deterministic mock."""
    content, model = _call_provider(SYSTEM_PROMPT, "user content")
    assert content == MOCK_ANSWER
    assert model == f"mock-{settings.gemini_model}"


@pytest.mark.unit
def test_call_provider_uses_gateway_when_available(mock_gateway):
    from tests.fixtures.app import make_completion_result

    mock_gateway["available"] = 1
    mock_gateway["results"].append(make_completion_result("draft answer"))
    content, model = _call_provider(SYSTEM_PROMPT, "user content")
    assert content == "draft answer"
    assert model == "mock/gemini#0"
    assert mock_gateway["calls"][0][1]["json_mode"] is False


@pytest.mark.unit
def test_build_prompt_includes_similar_doubts():
    from types import SimpleNamespace

    source = SimpleNamespace(
        id=1,
        title="Recursion depth",
        description="Stack overflow on deep recursion.",
        code_snippet="def f(): return f()",
        related_problem_id=None,
    )
    similar = SimpleNamespace(title="Recursion crash", description="Recursion stack blows up.")
    db = SimpleNamespace(
        scalars=lambda stmt: iter([similar]),
    )
    prompt = _build_prompt(source, None, db=db, teacher_note=None)
    assert "SIMILAR EXISTING DOUBTS" in prompt
    assert "Recursion crash" in prompt


@pytest.mark.unit
def test_build_prompt_ignores_db_errors():
    from types import SimpleNamespace

    source = SimpleNamespace(
        id=1, title="T", description="D", code_snippet="x = 1", related_problem_id=None
    )
    db = SimpleNamespace(scalars=lambda stmt: (_ for _ in ()).throw(RuntimeError("boom")))
    prompt = _build_prompt(source, None, db=db, teacher_note=None)
    assert "SIMILAR EXISTING DOUBTS" not in prompt


@pytest.mark.unit
def test_generate_ai_answer_sync_fallback_on_provider_error(monkeypatch):
    """Verify generate_ai_answer_sync writes fallback draft when _call_provider raises exception."""
    from types import SimpleNamespace
    import app.services.ai_answer as ai_answer_module
    from app.models import AnswerStatus

    fake_answer = SimpleNamespace(
        doubt_id=42,
        status=AnswerStatus.pending_review,
        draft_content=None,
        moderation_flagged=False,
        moderation_reason=None,
        raw_model_response=None,
        model_version=None,
        generated_at=None,
    )
    fake_doubt = SimpleNamespace(id=42, title="T", description="D", related_problem_id=None, code_snippet=None)

    class FakeSession:
        def scalar(self, stmt):
            return fake_answer

        def get(self, model, pk):
            if pk == 42:
                return fake_doubt
            return None

        def rollback(self):
            pass

        def commit(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(ai_answer_module, "SessionLocal", lambda: FakeSession())

    def failing_call_provider(system, prompt):
        raise RuntimeError("Provider connection failed")

    monkeypatch.setattr(ai_answer_module, "_call_provider", failing_call_provider)

    ai_answer_module.generate_ai_answer_sync(42)

    assert fake_answer.status == AnswerStatus.pending_review
    assert fake_answer.model_version == "fallback"
    assert fake_answer.draft_content is not None
    assert "AI could not generate an answer because every configured provider failed" in fake_answer.draft_content
    assert "Provider connection failed" in fake_answer.draft_content

