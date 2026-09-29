"""Integration tests for the submissions router."""

import pytest

from tests.factories.problems import make_problem
from tests.factories.submissions import (
    make_ai_feedback,
    make_submission,
    make_submission_result,
)
from tests.factories.users import make_student, make_teacher
from tests.utils.helpers import auth_header, get_json


@pytest.mark.integration
def test_create_submission_enqueues_grade_job(client, student_headers, db, problem, job_recorder):
    payload = {"problem_id": problem.id, "language": "python", "source_code": "print(2 + 3)"}
    data = get_json(client.post("/api/submissions", json=payload, headers=student_headers), 201)
    assert data["language"] == "python"
    assert data["status"] == "queued"
    assert job_recorder.names == ["grade_submission"]
    assert job_recorder.calls[0][1] == (data["id"],)


@pytest.mark.integration
def test_create_submission_unknown_problem_404(client, student_headers):
    resp = client.post(
        "/api/submissions",
        json={"problem_id": 999999, "language": "python", "source_code": "print(1)"},
        headers=student_headers,
    )
    assert resp.status_code == 404


@pytest.mark.integration
def test_create_submission_unsupported_language_422(client, student_headers, db, problem):
    resp = client.post(
        "/api/submissions",
        json={"problem_id": problem.id, "language": "brainfuck", "source_code": "+"},
        headers=student_headers,
    )
    assert resp.status_code == 422
    assert "Unsupported language" in resp.json()["detail"]


@pytest.mark.integration
def test_list_submissions_scoped_to_student(client, student_headers, db, password_hash, problem):
    student_a = make_student(db, password_hash=password_hash, email="student.aaa@test.local")
    student_b = make_student(db, password_hash=password_hash, email="student.bbb@test.local")
    sub_a = make_submission(db, student_id=student_a.id, problem_id=problem.id)
    make_submission(db, student_id=student_b.id, problem_id=problem.id)

    data = get_json(client.get("/api/submissions", headers=student_headers), 200)
    ids = [s["id"] for s in data]
    assert sub_a.id not in ids  # headers belong to a different student


@pytest.mark.integration
def test_list_submissions_filter_by_problem(client, teacher_headers, db, password_hash, problem):
    student_a = make_student(db, password_hash=password_hash, email="fil.a@test.local")
    make_submission(db, student_id=student_a.id, problem_id=problem.id)
    data = get_json(
        client.get(f"/api/submissions?problem_id={problem.id}", headers=teacher_headers), 200
    )
    assert len(data) == 1
    assert data[0]["problem_id"] == problem.id


@pytest.mark.integration
def test_get_submission_forbidden_for_other_student(client, student_headers, db, password_hash, problem):
    owner = make_student(db, password_hash=password_hash, email="owner@test.local")
    sub = make_submission(db, student_id=owner.id, problem_id=problem.id)
    assert client.get(f"/api/submissions/{sub.id}", headers=student_headers).status_code == 403


@pytest.mark.integration
def test_get_submission_teacher_can_view(client, teacher_headers, db, password_hash, problem):
    owner = make_student(db, password_hash=password_hash, email="owner2@test.local")
    sub = make_submission(db, student_id=owner.id, problem_id=problem.id, source_code="print(1)")
    data = get_json(client.get(f"/api/submissions/{sub.id}", headers=teacher_headers), 200)
    assert data["source_code"] == "print(1)"
    assert data["student_id"] == owner.id


@pytest.mark.integration
def test_get_submission_results_hides_hidden_case_details(client, db, password_hash, problem_with_cases):
    problem, cases = problem_with_cases
    owner = make_student(db, password_hash=password_hash, email="own3@test.local")
    sub = make_submission(db, student_id=owner.id, problem_id=problem.id)
    visible, hidden = cases
    make_submission_result(
        db, submission_id=sub.id, test_case_id=visible.id, actual_output="5"
    )
    make_submission_result(
        db, submission_id=sub.id, test_case_id=hidden.id, actual_output="1000000001"
    )
    headers = auth_header(_token_for(owner))
    data = get_json(client.get(f"/api/submissions/{sub.id}/results", headers=headers), 200)
    assert len(data) == 2
    hidden_result = next(r for r in data if r["test_case_id"] == hidden.id)
    assert hidden_result["input"] is None
    assert hidden_result["expected_output"] is None


@pytest.mark.integration
def test_get_ai_feedback(client, db, password_hash, problem):
    owner = make_student(db, password_hash=password_hash, email="own4@test.local")
    sub = make_submission(db, student_id=owner.id, problem_id=problem.id)
    make_ai_feedback(db, submission_id=sub.id)
    headers = auth_header(_token_for(owner))
    data = get_json(client.get(f"/api/submissions/{sub.id}/ai-feedback", headers=headers), 200)
    assert data["readability"]
    assert data["status"] == "success"


@pytest.mark.integration
def test_get_submission_404(client, teacher_headers):
    assert client.get("/api/submissions/999999", headers=teacher_headers).status_code == 404


@pytest.mark.integration
def test_list_submissions_teacher_filters_by_student(client, teacher_headers, db, password_hash, problem):
    student_a = make_student(db, password_hash=password_hash, email="sf.a@test.local")
    student_b = make_student(db, password_hash=password_hash, email="sf.b@test.local")
    sub_a = make_submission(db, student_id=student_a.id, problem_id=problem.id)
    make_submission(db, student_id=student_b.id, problem_id=problem.id)

    data = get_json(
        client.get(f"/api/submissions?student_id={student_a.id}", headers=teacher_headers), 200
    )
    assert [s["id"] for s in data] == [sub_a.id]


@pytest.mark.integration
def test_get_ai_feedback_404(client, db, password_hash, problem):
    owner = make_student(db, password_hash=password_hash, email="own5@test.local")
    sub = make_submission(db, student_id=owner.id, problem_id=problem.id)
    headers = auth_header(_token_for(owner))
    assert client.get(f"/api/submissions/{sub.id}/ai-feedback", headers=headers).status_code == 404


def _token_for(user):
    from app.models import UserRole
    from app.security import create_access_token

    return create_access_token(subject=str(user.id), role=UserRole.student.value)
