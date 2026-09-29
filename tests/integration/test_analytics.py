"""Integration tests for the analytics router."""

import pytest

from app.models import AnswerStatus, ReviewAction
from tests.factories.doubts import make_ai_answer, make_doubt, make_review_log
from tests.factories.users import make_student
from tests.utils.helpers import get_json


@pytest.mark.integration
def test_analytics_forbidden_for_student(client, student_headers):
    assert client.get("/api/analytics/reviews", headers=student_headers).status_code == 403


@pytest.mark.integration
def test_analytics_review_totals(client, teacher_headers, db, student_user, teacher_user):
    d1 = make_doubt(db, student_id=student_user.id)
    a1 = make_ai_answer(db, doubt_id=d1.id, status=AnswerStatus.approved)
    make_review_log(db, answer_id=a1.id, reviewer_id=teacher_user.id, action=ReviewAction.approved)

    d2 = make_doubt(db, student_id=student_user.id)
    a2 = make_ai_answer(db, doubt_id=d2.id, status=AnswerStatus.rejected)
    make_review_log(db, answer_id=a2.id, reviewer_id=teacher_user.id, action=ReviewAction.rejected)

    d3 = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=d3.id, status=AnswerStatus.pending_review)

    data = get_json(client.get("/api/analytics/reviews", headers=teacher_headers), 200)
    assert data["pending_reviews"] == 1
    assert data["generated_answers"] == 3
    assert data["approved_answers"] == 1
    assert data["rejected_answers"] == 1
    assert data["total_reviewed"] == 2
    assert data["approval_rate"] == 0.5
    assert data["reviews_by_action"]["approved"] == 1
    assert data["reviews_by_action"]["rejected"] == 1
    assert data["top_reviewers"][0]["name"] == teacher_user.full_name
    assert data["top_reviewers"][0]["count"] == 2
