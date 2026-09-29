"""End-to-end journeys through the full FastAPI app.

These run the whole request path through the TestClient and, where useful,
replay the captured ARQ jobs through the real worker functions so the
student/teacher flows are exercised end to end (docker sandbox and LLM
providers remain mocked).
"""

import pytest

from tests.factories.problems import make_problem
from tests.factories.users import make_student, make_teacher
from tests.mocks.arq import FakeQueueRedis
from tests.utils.helpers import auth_header, get_json
from tests.utils.jobs import run_job


@pytest.fixture
def student_journey(client, db, password_hash):
    """A fresh student with a valid JWT."""
    user = make_student(db, password_hash=password_hash, email="journey.student@example.com")
    from app.security import create_access_token

    token = create_access_token(subject=str(user.id), role="student")
    return {"user": user, "headers": auth_header(token)}


@pytest.mark.e2e
def test_student_submit_grade_feedback_flow(client, db, password_hash, problem_with_cases, job_recorder):
    problem, cases = problem_with_cases
    student = make_student(db, password_hash=password_hash, email="e2e.submit@example.com")
    from app.security import create_access_token

    headers = auth_header(
        create_access_token(subject=str(student.id), role="student")
    )

    created = get_json(
        client.post(
            "/api/submissions",
            json={"problem_id": problem.id, "language": "python", "source_code": "print('accepted')"},
            headers=headers,
        ),
        201,
    )
    submission_id = created["id"]

    queue = FakeQueueRedis()
    run_job("grade_submission", submission_id, redis=queue)
    run_job("generate_feedback", submission_id, redis=queue)

    detail = get_json(client.get(f"/api/submissions/{submission_id}", headers=headers), 200)
    assert detail["status"] == "graded"
    assert detail["verdict"] == "accepted"
    assert detail["score"] == 100.0

    results = get_json(client.get(f"/api/submissions/{submission_id}/results", headers=headers), 200)
    assert len(results) == len(cases)
    assert all(r["passed"] for r in results)

    feedback = get_json(client.get(f"/api/submissions/{submission_id}/ai-feedback", headers=headers), 200)
    assert feedback["status"] == "success"
    assert feedback["readability"]
    assert feedback["optimization"]


@pytest.mark.e2e
def test_student_doubt_to_teacher_review_flow(client, db, password_hash, problem, job_recorder):
    student = make_student(db, password_hash=password_hash, email="e2e.doubt.student@example.com")
    teacher = make_teacher(db, password_hash=password_hash, email="e2e.doubt.teacher@example.com")
    from app.models import UserRole
    from app.security import create_access_token

    student_headers = auth_header(create_access_token(subject=str(student.id), role=UserRole.student.value))
    teacher_headers = auth_header(create_access_token(subject=str(teacher.id), role=UserRole.teacher.value))

    doubt = get_json(
        client.post(
            "/api/doubts",
            json={
                "title": "Segfault in my linked list",
                "description": "Deleting a node crashes.",
                "code_snippet": "free(node);",
                "related_problem_id": problem.id,
            },
            headers=student_headers,
        ),
        201,
    )
    doubt_id = doubt["id"]

    queue = FakeQueueRedis()
    run_job("generate_answer", doubt_id, redis=queue)

    pending = get_json(client.get("/api/reviews/answers", headers=teacher_headers), 200)
    matching = [a for a in pending if a["doubt_id"] == doubt_id]
    assert len(matching) == 1
    answer_id = matching[0]["id"]
    assert matching[0]["draft_content"]

    approved = get_json(
        client.post(f"/api/reviews/{answer_id}/approve", json={"note": "looks good"}, headers=teacher_headers),
        200,
    )
    assert approved["status"] == "approved"

    student_answer = get_json(client.get(f"/api/doubts/{doubt_id}/answer", headers=student_headers), 200)
    assert student_answer["status"] == "approved"
    assert student_answer["draft_content"]

    notifications = get_json(client.get("/api/notifications", headers=student_headers), 200)
    assert any(n["related_doubt_id"] == doubt_id for n in notifications)


@pytest.mark.e2e
def test_signup_login_me_and_submission(client, db, problem):
    signup = get_json(
        client.post(
            "/api/auth/signup",
            json={
                "email": "e2e.full@example.com",
                "password": "strongpass123",
                "full_name": "Full Journey",
            },
        ),
        201,
    )
    login = get_json(
        client.post(
            "/api/auth/login",
            data={"username": signup["email"], "password": "strongpass123"},
        ),
        200,
    )
    headers = auth_header(login["access_token"])
    me = get_json(client.get("/api/auth/me", headers=headers), 200)
    assert me["id"] == signup["id"]
    assert me["role"] == "student"

    submission = get_json(
        client.post(
            "/api/submissions",
            json={"problem_id": problem.id, "language": "javascript", "source_code": "console.log(5);"},
            headers=headers,
        ),
        201,
    )
    assert submission["language"] == "javascript"
