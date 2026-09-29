"""Integration tests for AI-service retry and failure handling through the
worker pipeline with a scripted gateway."""

import pytest

from app.models import AnswerStatus, FeedbackStatus, SubmissionStatus, Verdict
from tests.factories.doubts import make_ai_answer, make_doubt
from tests.factories.submissions import make_ai_feedback, make_submission
from tests.mocks.arq import FakeQueueRedis
from tests.utils.jobs import run_job


@pytest.mark.integration
def test_generate_answer_retries_then_succeeds(client, db, student_user, mock_gateway):
    from tests.fixtures.app import make_completion_result
    from app.services.llm_gateway import LLMGatewayError

    mock_gateway["available"] = 1
    mock_gateway["errors"] = [
        LLMGatewayError("transient 1"),
        LLMGatewayError("transient 2"),
    ]
    mock_gateway["results"].append(make_completion_result("final draft"))

    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content=None)
    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt.id))
    assert answer.status == AnswerStatus.pending_review
    assert answer.draft_content == "final draft"
    assert len(mock_gateway["calls"]) == 3


@pytest.mark.integration
@pytest.mark.integration
def test_generate_answer_records_failure(client, db, student_user, mock_gateway):
    from app.services.llm_gateway import LLMGatewayError

    mock_gateway["available"] = 1
    mock_gateway["errors"] = [
        LLMGatewayError("boom 1"),
        LLMGatewayError("boom 2"),
        LLMGatewayError("boom 3"),
    ]

    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content=None)
    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt.id))
    assert answer.status == AnswerStatus.pending_review
    assert answer.model_version == "fallback"
    assert "generation failed" in answer.raw_model_response
    assert answer.draft_content is not None
    assert "AI could not generate an answer because every configured provider failed" in answer.draft_content


@pytest.mark.integration
def test_generate_answer_gemini_failure_failover_to_groq(client, db, student_user, mock_gateway):
    """Test that if Gemini fails, failover continues through provider attempts until success."""
    from tests.fixtures.app import make_completion_result
    from app.services.llm_gateway import LLMGatewayError

    mock_gateway["available"] = 1
    # Gemini fails on attempt 1, Groq succeeds on attempt 2
    mock_gateway["errors"] = [LLMGatewayError("Gemini rate limit 429")]
    mock_gateway["results"] = [make_completion_result("Groq response", model="mock/groq#0")]

    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content=None)
    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt.id))
    assert answer.status == AnswerStatus.pending_review
    assert answer.draft_content == "Groq response"
    assert answer.model_version == "mock/groq#0"


@pytest.mark.integration
def test_generate_answer_groq_failure_failover_to_gemini(client, db, student_user, mock_gateway):
    """Test that if Groq fails after initial attempt, failover continues until success."""
    from tests.fixtures.app import make_completion_result
    from app.services.llm_gateway import LLMGatewayError

    mock_gateway["available"] = 1
    mock_gateway["errors"] = [LLMGatewayError("Groq service unavailable 503")]
    mock_gateway["results"] = [make_completion_result("Gemini response", model="mock/gemini#1")]

    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content=None)
    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt.id))
    assert answer.status == AnswerStatus.pending_review
    assert answer.draft_content == "Gemini response"
    assert answer.model_version == "mock/gemini#1"


@pytest.mark.integration
def test_generate_answer_all_providers_fail_creates_fallback_draft(client, db, student_user, mock_gateway):
    """Test that when all provider attempts fail, a teacher-visible fallback draft is stored."""
    from app.services.llm_gateway import LLMGatewayError

    mock_gateway["available"] = 1
    mock_gateway["errors"] = [
        LLMGatewayError("Gemini failed"),
        LLMGatewayError("Groq failed"),
        LLMGatewayError("All backends exhausted"),
    ]

    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content=None)
    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt.id))
    assert answer.status == AnswerStatus.pending_review
    assert answer.model_version == "fallback"
    assert "AI could not generate an answer because every configured provider failed" in answer.draft_content
    assert "Error:" in answer.draft_content
    assert "A teacher should review and answer this doubt manually" in answer.draft_content
    assert answer.draft_content != ""
    assert answer.draft_content is not None


@pytest.mark.integration
def test_generate_feedback_records_failure(client, db, password_hash, student_user, problem, mock_gateway):
    from app.services.llm_gateway import LLMGatewayError

    mock_gateway["available"] = 1
    mock_gateway["errors"] = [
        LLMGatewayError("boom 1"),
        LLMGatewayError("boom 2"),
        LLMGatewayError("boom 3"),
    ]

    submission = make_submission(
        db,
        student_id=student_user.id,
        problem_id=problem.id,
        status="graded",
        verdict="accepted",
        score=100.0,
    )
    make_ai_feedback(db, submission_id=submission.id, status=FeedbackStatus.pending)
    run_job("generate_feedback", submission.id, redis=FakeQueueRedis())

    from app.models import AIFeedback
    from sqlalchemy import select

    db.expire_all()
    feedback = db.scalar(select(AIFeedback).where(AIFeedback.submission_id == submission.id))
    assert feedback.status == FeedbackStatus.failed
    assert feedback.model_version == "fallback"
    assert feedback.readability


@pytest.mark.integration
def test_generate_feedback_noop_when_missing_row(client, db, password_hash):
    run_job("generate_feedback", 999999, redis=FakeQueueRedis())


@pytest.mark.integration
def test_generate_feedback_skips_when_not_graded(client, db, student_user, problem):
    submission = make_submission(
        db,
        student_id=student_user.id,
        problem_id=problem.id,
        status="queued",
    )
    make_ai_feedback(db, submission_id=submission.id, status=FeedbackStatus.pending)
    run_job("generate_feedback", submission.id, redis=FakeQueueRedis())

    from app.models import AIFeedback
    from sqlalchemy import select

    db.expire_all()
    feedback = db.scalar(select(AIFeedback).where(AIFeedback.submission_id == submission.id))
    assert feedback.status == FeedbackStatus.pending


@pytest.mark.integration
def test_generate_feedback_skips_when_already_success(client, db, student_user, problem):
    submission = make_submission(
        db,
        student_id=student_user.id,
        problem_id=problem.id,
        status="graded",
    )
    make_ai_feedback(
        db,
        submission_id=submission.id,
        status=FeedbackStatus.success,
        readability="already done",
    )
    run_job("generate_feedback", submission.id, redis=FakeQueueRedis())

    from app.models import AIFeedback
    from sqlalchemy import select

    db.expire_all()
    feedback = db.scalar(select(AIFeedback).where(AIFeedback.submission_id == submission.id))
    assert feedback.readability == "already done"


@pytest.mark.integration
def test_generate_answer_skips_when_approved(client, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(
        db, doubt_id=doubt.id, status=AnswerStatus.approved, draft_content="kept"
    )
    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt.id))
    assert answer.draft_content == "kept"


@pytest.mark.integration
def test_generate_answer_skips_when_doubt_missing(client, db, student_user, monkeypatch):
    import app.services.ai_answer as ai_answer_module
    from app.database import SessionLocal

    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, draft_content=None)

    def missing_doubt_session():
        session = SessionLocal()

        def fake_get(entity, ident):
            if entity is doubt.__class__:
                return None
            return session.get(entity, ident)

        session.get = fake_get
        return session

    monkeypatch.setattr(ai_answer_module, "SessionLocal", missing_doubt_session)
    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    row = db.scalar(select(AIAnswer).where(AIAnswer.id == answer.id))
    assert row.draft_content is None


@pytest.mark.integration
def test_generate_answer_propagates_timeout(client, db, student_user, mock_gateway):
    from app.services.llm_gateway import LLMTimeoutError

    mock_gateway["available"] = 1
    mock_gateway["errors"] = [LLMTimeoutError("gateway deadline")]

    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content=None)

    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt.id))
    assert answer.model_version == "fallback"
    assert "generation failed" in answer.raw_model_response
    assert answer.draft_content is not None
    assert "AI could not generate an answer because every configured provider failed" in answer.draft_content


@pytest.mark.integration
def test_generate_feedback_lenient_parse_on_last_attempt(client, db, student_user, problem, mock_gateway):
    from tests.fixtures.app import make_completion_result

    mock_gateway["available"] = 1
    bad_json = '{"readability": "truncated feedback'
    mock_gateway["results"] = [
        make_completion_result(bad_json),
        make_completion_result(bad_json),
        make_completion_result(bad_json),
    ]

    submission = make_submission(
        db,
        student_id=student_user.id,
        problem_id=problem.id,
        status=SubmissionStatus.graded,
        verdict=Verdict.accepted,
        score=100.0,
    )
    make_ai_feedback(db, submission_id=submission.id, status=FeedbackStatus.pending)
    run_job("generate_feedback", submission.id, redis=FakeQueueRedis())

    from app.models import AIFeedback
    from sqlalchemy import select

    db.expire_all()
    feedback = db.scalar(select(AIFeedback).where(AIFeedback.submission_id == submission.id))
    assert feedback.status == FeedbackStatus.success
    assert "truncated feedback" in feedback.readability


@pytest.mark.integration
def test_generate_feedback_propagates_timeout(client, db, student_user, problem, mock_gateway):
    from app.services.llm_gateway import LLMTimeoutError

    mock_gateway["available"] = 1
    mock_gateway["errors"] = [LLMTimeoutError("gateway deadline")]

    submission = make_submission(
        db,
        student_id=student_user.id,
        problem_id=problem.id,
        status=SubmissionStatus.graded,
        verdict=Verdict.accepted,
        score=100.0,
    )
    make_ai_feedback(db, submission_id=submission.id, status=FeedbackStatus.pending)
    run_job("generate_feedback", submission.id, redis=FakeQueueRedis())

    from app.models import AIFeedback
    from sqlalchemy import select

    db.expire_all()
    feedback = db.scalar(select(AIFeedback).where(AIFeedback.submission_id == submission.id))
    assert feedback.status == FeedbackStatus.failed
    assert feedback.model_version == "fallback"


@pytest.mark.integration
def test_generate_feedback_lenient_parse_failure_marks_failed(
    client, db, student_user, problem, mock_gateway, monkeypatch
):
    from tests.fixtures.app import make_completion_result

    mock_gateway["available"] = 1
    bad_json = '{"readability": "truncated feedback'
    mock_gateway["results"] = [
        make_completion_result(bad_json),
        make_completion_result(bad_json),
        make_completion_result(bad_json),
    ]

    import app.services.ai_feedback as ai_feedback_module

    def broken_lenient(raw):
        raise ValueError("lenient parse impossible")

    monkeypatch.setattr(ai_feedback_module, "_parse_lenient", broken_lenient)

    submission = make_submission(
        db,
        student_id=student_user.id,
        problem_id=problem.id,
        status=SubmissionStatus.graded,
        verdict=Verdict.accepted,
        score=100.0,
    )
    make_ai_feedback(db, submission_id=submission.id, status=FeedbackStatus.pending)
    run_job("generate_feedback", submission.id, redis=FakeQueueRedis())

    from app.models import AIFeedback
    from sqlalchemy import select

    db.expire_all()
    feedback = db.scalar(select(AIFeedback).where(AIFeedback.submission_id == submission.id))
    assert feedback.status == FeedbackStatus.failed
    assert feedback.model_version == "fallback"
