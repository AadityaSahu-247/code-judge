"""Unit tests for the SQLAlchemy models (schema-level, no database needed)."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import (
    AIAnswer,
    AIFeedback,
    AnswerStatus,
    Doubt,
    DoubtStatus,
    FeedbackStatus,
    Notification,
    Problem,
    ReviewAction,
    ReviewLog,
    Submission,
    SubmissionResult,
    SubmissionStatus,
    TestCase,
    User,
    UserRole,
    Verdict,
)

ALL_MODELS = [
    User,
    Problem,
    TestCase,
    Submission,
    SubmissionResult,
    AIFeedback,
    Doubt,
    AIAnswer,
    ReviewLog,
    Notification,
]


@pytest.mark.unit
def test_role_enum_values():
    assert UserRole.student.value == "student"
    assert UserRole.teacher.value == "teacher"
    assert UserRole.admin.value == "admin"


@pytest.mark.unit
def test_status_enum_values():
    assert SubmissionStatus.queued.value == "queued"
    assert SubmissionStatus.graded.value == "graded"
    assert SubmissionStatus.failed.value == "failed"
    assert Verdict.accepted.value == "accepted"
    assert Verdict.time_limit_exceeded.value == "time_limit_exceeded"
    assert FeedbackStatus.pending.value == "pending"
    assert FeedbackStatus.success.value == "success"
    assert DoubtStatus.open.value == "open"
    assert DoubtStatus.answered.value == "answered"
    assert AnswerStatus.pending_review.value == "pending_review"
    assert AnswerStatus.approved.value == "approved"
    assert AnswerStatus.rejected.value == "rejected"
    assert ReviewAction.approved.value == "approved"
    assert ReviewAction.edited.value == "edited"
    assert ReviewAction.rejected.value == "rejected"


@pytest.mark.unit
@pytest.mark.parametrize("model", ALL_MODELS)
def test_all_tables_compile_for_postgres(model):
    ddl = str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))
    assert ddl.strip().startswith("CREATE TABLE")


@pytest.mark.unit
def test_user_columns():
    mapper = inspect(User)
    assert mapper.columns.email.nullable is False
    assert mapper.columns.password_hash.nullable is False
    assert mapper.columns.role.nullable is False
    assert mapper.columns.email.unique is True
    assert mapper.columns.created_at.server_default is not None


@pytest.mark.unit
def test_submission_relationships_and_fk():
    mapper = inspect(Submission)
    assert mapper.relationships["results"].uselist is True
    fks = {fk.target_fullname for fk in mapper.columns.student_id.foreign_keys}
    assert "users.id" in fks


@pytest.mark.unit
def test_ai_feedback_unique_submission():
    assert inspect(AIFeedback).columns.submission_id.unique is True


@pytest.mark.unit
def test_ai_answer_unique_doubt():
    assert inspect(AIAnswer).columns.doubt_id.unique is True


@pytest.mark.unit
def test_review_log_relationship_chain():
    assert inspect(AIAnswer).relationships["logs"].uselist is True
    assert inspect(ReviewLog).relationships["answer"] is not None


@pytest.mark.unit
def test_notification_columns():
    mapper = inspect(Notification)
    assert mapper.columns.user_id.nullable is False
    assert mapper.columns.read.default.arg is False
