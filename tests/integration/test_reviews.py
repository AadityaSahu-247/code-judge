"""Integration tests for the reviews router."""

import pytest

from app.models import AnswerStatus, DoubtStatus, UserRole
from app.security import create_access_token
from tests.factories.doubts import make_ai_answer, make_doubt, make_review_log
from tests.factories.users import make_student, make_teacher
from tests.utils.helpers import auth_header, get_json


@pytest.mark.integration
def test_list_pending_answers_only_staff(client, student_headers, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id)
    assert client.get("/api/reviews/answers", headers=student_headers).status_code == 403
    data = get_json(client.get("/api/reviews/answers", headers=teacher_headers), 200)
    assert len(data) == 1
    assert data[0]["status"] == AnswerStatus.pending_review.value


@pytest.mark.integration
def test_claim_answer_sets_claimant(client, teacher_headers, db, student_user, teacher_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id)
    data = get_json(client.post(f"/api/reviews/{answer.id}/claim", headers=teacher_headers), 200)
    assert data["claimed_by_id"] == teacher_user.id
    assert data["claimed_by_name"] == teacher_user.full_name


@pytest.mark.integration
def test_claim_answer_conflict_for_second_teacher(
    client, teacher_headers, db, student_user, teacher_user, password_hash
):
    teacher_b = make_teacher(db, password_hash=password_hash, email="reviewer.b@test.local")
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id)

    get_json(client.post(f"/api/reviews/{answer.id}/claim", headers=teacher_headers), 200)
    token = create_access_token(subject=str(teacher_b.id), role=UserRole.teacher.value)
    resp = client.post(f"/api/reviews/{answer.id}/claim", headers=auth_header(token))
    assert resp.status_code == 409


@pytest.mark.integration
def test_approve_answer_notifies_student(client, teacher_headers, db, student_user, problem):
    from app.models import Notification

    doubt = make_doubt(db, student_id=student_user.id, related_problem_id=problem.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, draft_content="A good answer")

    data = get_json(
        client.post(f"/api/reviews/{answer.id}/approve", json={"note": "looks good"}, headers=teacher_headers),
        200,
    )
    assert data["status"] == AnswerStatus.approved.value

    db.refresh(doubt)
    assert doubt.status == DoubtStatus.answered

    notification = db.scalar(
        db.query(Notification).where(Notification.related_doubt_id == doubt.id)
    )
    assert notification is not None
    assert notification.user_id == student_user.id
    assert notification.type == "doubt_answered"


@pytest.mark.integration
def test_edit_answer_approves_with_edited_content(client, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, draft_content="original")
    data = get_json(
        client.post(
            f"/api/reviews/{answer.id}/edit",
            json={"edited_content": "improved answer", "note": "rewritten"},
            headers=teacher_headers,
        ),
        200,
    )
    assert data["status"] == AnswerStatus.approved.value
    assert data["draft_content"] == "improved answer"


@pytest.mark.integration
def test_reject_answer(client, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id)
    data = get_json(
        client.post(
            f"/api/reviews/{answer.id}/reject", json={"note": "too vague"}, headers=teacher_headers
        ),
        200,
    )
    assert data["status"] == AnswerStatus.rejected.value


@pytest.mark.integration
def test_approve_already_reviewed_409(client, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, status=AnswerStatus.approved)
    resp = client.post(
        f"/api/reviews/{answer.id}/approve", json={}, headers=teacher_headers
    )
    assert resp.status_code == 409


@pytest.mark.integration
def test_review_logs_are_listed(client, teacher_headers, db, student_user, teacher_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, status=AnswerStatus.approved)
    make_review_log(
        db,
        answer_id=answer.id,
        reviewer_id=teacher_user.id,
        note="approved on first pass",
    )
    data = get_json(client.get(f"/api/reviews/{answer.id}/logs", headers=teacher_headers), 200)
    assert len(data) == 1
    assert data[0]["action"] == "approved"
    assert data[0]["reviewer_name"] == teacher_user.full_name


@pytest.mark.integration
def test_edit_answer_empty_content_after_sanitization(client, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id)
    resp = client.post(
        f"/api/reviews/{answer.id}/edit",
        json={"edited_content": "<script>alert(1)</script>"},
        headers=teacher_headers,
    )
    assert resp.status_code == 422


@pytest.mark.integration
def test_reject_already_reviewed_409(client, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, status=AnswerStatus.rejected)
    resp = client.post(
        f"/api/reviews/{answer.id}/reject", json={"note": "nope"}, headers=teacher_headers
    )
    assert resp.status_code == 409


@pytest.mark.integration
def test_regenerate_reuses_last_rejection_note(
    client, teacher_headers, db, student_user, teacher_user, job_recorder
):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(
        db, doubt_id=doubt.id, status=AnswerStatus.rejected, draft_content="old"
    )
    make_review_log(
        db,
        answer_id=answer.id,
        reviewer_id=teacher_user.id,
        action="rejected",
        note="be more concise",
    )
    data = get_json(
        client.post(f"/api/reviews/{answer.id}/regenerate", json={}, headers=teacher_headers),
        200,
    )
    assert data["status"] == AnswerStatus.pending_review.value
    assert job_recorder.calls[0][1] == (answer.doubt_id, "be more concise")


@pytest.mark.integration
def test_review_logs_require_staff(client, student_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id)
    assert client.get(f"/api/reviews/{answer.id}/logs", headers=student_headers).status_code == 403


@pytest.mark.integration
def test_approve_answer_claimed_by_other_teacher_409(
    client, teacher_headers, db, student_user, teacher_user, password_hash
):
    teacher_b = make_teacher(db, password_hash=password_hash, email="reviewer.c@test.local")
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, claimed_by_id=teacher_user.id)

    token = create_access_token(subject=str(teacher_b.id), role=UserRole.teacher.value)
    resp = client.post(
        f"/api/reviews/{answer.id}/approve", json={}, headers=auth_header(token)
    )
    assert resp.status_code == 409


@pytest.mark.integration
def test_approve_missing_answer_404(client, teacher_headers):
    assert client.post("/api/reviews/999999/approve", json={}, headers=teacher_headers).status_code == 404


@pytest.mark.integration
def test_edit_already_reviewed_409(client, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, status=AnswerStatus.approved)
    resp = client.post(
        f"/api/reviews/{answer.id}/edit",
        json={"edited_content": "too late"},
        headers=teacher_headers,
    )
    assert resp.status_code == 409


@pytest.mark.integration
def test_regenerate_only_rejected_answers(client, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    answer = make_ai_answer(db, doubt_id=doubt.id, status=AnswerStatus.approved)
    resp = client.post(f"/api/reviews/{answer.id}/regenerate", json={}, headers=teacher_headers)
    assert resp.status_code == 409
