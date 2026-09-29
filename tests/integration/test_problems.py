"""Integration tests for the problems router."""

import pytest

from tests.factories.problems import make_problem, make_problem_with_cases, make_test_case
from tests.factories.submissions import make_submission
from tests.factories.users import make_student, make_teacher
from tests.utils.helpers import get_json


@pytest.mark.integration
def test_list_problems(client, student_headers, db, problem):
    data = get_json(client.get("/api/problems", headers=student_headers), 200)
    assert len(data) == 1
    assert data[0]["id"] == problem.id
    assert data[0]["title"] == problem.title


@pytest.mark.integration
def test_get_problem_detail(client, student_headers, db, problem_with_cases):
    problem, _cases = problem_with_cases
    data = get_json(client.get(f"/api/problems/{problem.id}", headers=student_headers), 200)
    assert data["statement"] == problem.statement
    assert data["constraints"] == problem.constraints


@pytest.mark.integration
def test_get_missing_problem_404(client, student_headers):
    assert client.get("/api/problems/999999", headers=student_headers).status_code == 404


@pytest.mark.integration
def test_problems_require_auth(client):
    assert client.get("/api/problems").status_code == 401


@pytest.mark.integration
def test_student_sees_only_visible_testcases(client, student_headers, db, problem_with_cases):
    problem, _ = problem_with_cases
    data = get_json(client.get(f"/api/problems/{problem.id}/testcases", headers=student_headers), 200)
    assert len(data) == 1
    assert all(tc["is_hidden"] is False for tc in data)


@pytest.mark.integration
def test_teacher_sees_hidden_testcases(client, teacher_headers, db, problem_with_cases):
    problem, _ = problem_with_cases
    data = get_json(client.get(f"/api/problems/{problem.id}/testcases", headers=teacher_headers), 200)
    assert len(data) == 2


@pytest.mark.integration
def test_add_testcases_teacher_only(client, teacher_headers, student_headers, db, problem):
    payload = [
        {"input": "1 2", "expected_output": "3", "is_hidden": True, "weight": 2.0},
        {"input": "0 0", "expected_output": "0"},
    ]
    data = get_json(
        client.post(f"/api/problems/{problem.id}/testcases", json=payload, headers=teacher_headers),
        201,
    )
    assert len(data) == 2
    assert data[0]["is_hidden"] is True
    assert data[0]["weight"] == 2.0


@pytest.mark.integration
def test_add_testcases_forbidden_for_student(client, student_headers, db, problem):
    resp = client.post(
        f"/api/problems/{problem.id}/testcases",
        json=[{"input": "1", "expected_output": "1"}],
        headers=student_headers,
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_plagiarism_report_finds_duplicate_submissions(client, teacher_headers, db, password_hash):
    problem = make_problem(db)
    student_a = make_student(db, password_hash=password_hash, email="solo.a@test.local")
    student_b = make_student(db, password_hash=password_hash, email="solo.b@test.local")
    shared_code = "print('accepted')"
    make_submission(db, student_id=student_a.id, problem_id=problem.id, source_code=shared_code)
    make_submission(db, student_id=student_b.id, problem_id=problem.id, source_code=shared_code)

    data = get_json(
        client.get(f"/api/problems/{problem.id}/plagiarism?threshold=0.5", headers=teacher_headers),
        200,
    )
    assert data["problem_id"] == problem.id
    assert len(data["pairs"]) == 1
    assert data["pairs"][0]["similarity"] > 0.5


@pytest.mark.integration
def test_plagiarism_forbidden_for_student(client, student_headers, db, problem):
    resp = client.get(f"/api/problems/{problem.id}/plagiarism", headers=student_headers)
    assert resp.status_code == 403


@pytest.mark.integration
def test_testcases_missing_problem_404(client, student_headers):
    assert client.get("/api/problems/999999/testcases", headers=student_headers).status_code == 404


@pytest.mark.integration
def test_add_testcases_missing_problem_404(client, teacher_headers):
    resp = client.post(
        "/api/problems/999999/testcases",
        json=[{"input": "1", "expected_output": "1"}],
        headers=teacher_headers,
    )
    assert resp.status_code == 404


@pytest.mark.integration
def test_plagiarism_missing_problem_404(client, teacher_headers):
    resp = client.get("/api/problems/999999/plagiarism", headers=teacher_headers)
    assert resp.status_code == 404


@pytest.mark.integration
def test_plagiarism_skips_same_student_pairs(client, teacher_headers, db, password_hash):
    problem = make_problem(db)
    student_a = make_student(db, password_hash=password_hash, email="same.owner@test.local")
    shared_code = "print('identical')"
    make_submission(db, student_id=student_a.id, problem_id=problem.id, source_code=shared_code)
    make_submission(db, student_id=student_a.id, problem_id=problem.id, source_code=shared_code)

    data = get_json(
        client.get(f"/api/problems/{problem.id}/plagiarism?threshold=0.1", headers=teacher_headers),
        200,
    )
    assert data["pairs"] == []
