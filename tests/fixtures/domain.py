"""Domain fixtures: dummy problems, submissions, doubts, answers, notifications."""

from __future__ import annotations

import pytest

from app.models import AnswerStatus, SubmissionStatus, Verdict
from tests.factories import doubts as doubt_factories
from tests.factories import notifications as notification_factories
from tests.factories import problems as problem_factories
from tests.factories import submissions as submission_factories


@pytest.fixture
def problem(db):
    return problem_factories.make_problem(db)


@pytest.fixture
def problem_with_cases(db):
    return problem_factories.make_problem_with_cases(db)


@pytest.fixture
def test_case(db, problem):
    return problem_factories.make_test_case(db, problem.id)


@pytest.fixture
def submission(db, student_user, problem):
    return submission_factories.make_submission(
        db,
        student_id=student_user.id,
        problem_id=problem.id,
        status=SubmissionStatus.graded,
        verdict=Verdict.accepted,
        score=100.0,
    )


@pytest.fixture
def doubt(db, student_user, problem):
    return doubt_factories.make_doubt(
        db,
        student_id=student_user.id,
        related_problem_id=problem.id,
    )


@pytest.fixture
def pending_answer(db, doubt, teacher_user):
    return doubt_factories.make_ai_answer(db, doubt_id=doubt.id)


@pytest.fixture
def approved_answer(db, doubt, teacher_user):
    return doubt_factories.make_ai_answer(
        db,
        doubt_id=doubt.id,
        status=AnswerStatus.approved,
    )


@pytest.fixture
def notification(db, student_user, doubt):
    return notification_factories.make_notification(
        db,
        user_id=student_user.id,
        related_doubt_id=doubt.id,
    )
