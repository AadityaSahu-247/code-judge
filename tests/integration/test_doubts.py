"""Integration tests for the doubts router."""

import pytest

from tests.factories.doubts import make_ai_answer, make_doubt
from tests.factories.problems import make_problem
from tests.factories.users import make_student
from tests.utils.helpers import auth_header, get_json


@pytest.mark.integration
def test_create_doubt_enqueues_answer_job(client, student_headers, db, problem, job_recorder):
    payload = {
        "title": "Why is my pointer null?",
        "description": "It stays null after allocation.",
        "code_snippet": "int *p; p = NULL;",
        "related_problem_id": problem.id,
    }
    data = get_json(client.post("/api/doubts", json=payload, headers=student_headers), 201)
    assert data["title"] == payload["title"]
    assert data["student_name"]
    assert job_recorder.names == ["generate_answer"]
    assert job_recorder.calls[0][1] == (data["id"],)


@pytest.mark.integration
def test_create_doubt_unknown_problem_404(client, student_headers):
    resp = client.post(
        "/api/doubts",
        json={"title": "Trouble", "description": "Something breaks.", "related_problem_id": 999999},
        headers=student_headers,
    )
    assert resp.status_code == 404


@pytest.mark.integration
def test_create_doubt_sanitizes_title(client, student_headers):
    payload = {"title": "  <script>alert(1)</script>  ", "description": "body text"}
    data = get_json(client.post("/api/doubts", json=payload, headers=student_headers), 201)
    assert "<script>" not in data["title"]
    assert data["title"] != ""


@pytest.mark.integration
def test_list_doubts_and_search(client, student_headers, db, student_user):
    make_doubt(db, student_id=student_user.id, title="Loop bug in Python", description="infinite while loop")
    make_doubt(db, student_id=student_user.id, title="Array out of bounds", description="index error")
    data = get_json(client.get("/api/doubts?q=loop", headers=student_headers), 200)
    assert len(data) == 1
    assert data[0]["title"] == "Loop bug in Python"


@pytest.mark.integration
def test_list_doubts_filter_by_problem(client, student_headers, db, student_user, problem):
    p2 = make_problem(db, title="Second Problem")
    make_doubt(db, student_id=student_user.id, related_problem_id=problem.id)
    make_doubt(db, student_id=student_user.id, related_problem_id=p2.id)
    data = get_json(client.get(f"/api/doubts?problem_id={problem.id}", headers=student_headers), 200)
    assert len(data) == 1


@pytest.mark.integration
def test_get_doubt_detail(client, student_headers, db, student_user, problem):
    doubt = make_doubt(db, student_id=student_user.id, related_problem_id=problem.id)
    data = get_json(client.get(f"/api/doubts/{doubt.id}", headers=student_headers), 200)
    assert data["description"] == doubt.description
    assert data["student_name"] == student_user.full_name


@pytest.mark.integration
def test_update_doubt_own(client, student_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    data = get_json(
        client.patch(
            f"/api/doubts/{doubt.id}",
            json={"title": "Renamed doubt"},
            headers=student_headers,
        ),
        200,
    )
    assert data["title"] == "Renamed doubt"


@pytest.mark.integration
def test_update_doubt_forbidden_for_other_user(client, student_headers, db, password_hash):
    owner = make_student(db, password_hash=password_hash, email="doubt.owner@test.local")
    doubt = make_doubt(db, student_id=owner.id)
    resp = client.patch(
        f"/api/doubts/{doubt.id}", json={"title": "Hijacked"}, headers=student_headers
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_delete_doubt_own(client, student_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    assert client.delete(f"/api/doubts/{doubt.id}", headers=student_headers).status_code == 204
    assert client.get(f"/api/doubts/{doubt.id}", headers=student_headers).status_code == 404


@pytest.mark.integration
def test_similar_doubts_returns_related(client, student_headers, db, student_user):
    source = make_doubt(
        db, student_id=student_user.id, title="Recursion depth error", description="stack overflows"
    )
    make_doubt(
        db, student_id=student_user.id, title="Recursion overflow", description="stack blows up"
    )
    make_doubt(
        db, student_id=student_user.id, title="CSS flexbox", description="centering is hard"
    )
    data = get_json(
        client.get(f"/api/doubts/similar?doubt_id={source.id}", headers=student_headers), 200
    )
    titles = [d["title"] for d in data]
    assert "Recursion overflow" in titles
    assert all(d["id"] != source.id for d in data)


@pytest.mark.integration
def test_get_answer_pending_hidden_for_student(client, student_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content="secret draft")
    data = get_json(client.get(f"/api/doubts/{doubt.id}/answer", headers=student_headers), 200)
    assert data["status"] == "pending_review"
    assert data["draft_content"] is None


@pytest.mark.integration
def test_get_answer_approved_visible_to_student(client, student_headers, db, student_user):
    from app.models import AnswerStatus

    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, status=AnswerStatus.approved, draft_content="final answer")
    data = get_json(client.get(f"/api/doubts/{doubt.id}/answer", headers=student_headers), 200)
    assert data["draft_content"] == "final answer"


@pytest.mark.integration
def test_get_answer_large_content(client, student_headers, db, student_user):
    from app.models import AnswerStatus

    large_draft = "A" * 10000
    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, status=AnswerStatus.approved, draft_content=large_draft)
    data = get_json(client.get(f"/api/doubts/{doubt.id}/answer", headers=student_headers), 200)
    assert data["draft_content"] == large_draft
    assert len(data["draft_content"]) == 10000


@pytest.mark.integration
def test_get_answer_visible_to_teacher_even_pending(client, teacher_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content="teacher draft")
    data = get_json(client.get(f"/api/doubts/{doubt.id}/answer", headers=teacher_headers), 200)
    assert data["draft_content"] == "teacher draft"


@pytest.mark.integration
def test_get_answer_404_when_not_generated(client, student_headers, db, student_user):
    doubt = make_doubt(db, student_id=student_user.id)
    assert client.get(f"/api/doubts/{doubt.id}/answer", headers=student_headers).status_code == 404


@pytest.mark.integration
def test_delete_doubt_forbidden_for_other_user(client, student_headers, db, password_hash):
    from tests.factories.users import make_student

    owner = make_student(db, password_hash=password_hash, email="doubt.owner2@test.local")
    doubt = make_doubt(db, student_id=owner.id)
    resp = client.delete(f"/api/doubts/{doubt.id}", headers=student_headers)
    assert resp.status_code == 403


@pytest.mark.integration
def test_update_doubt_extra_fields(client, student_headers, db, student_user):
    from app.models import DoubtStatus

    doubt = make_doubt(db, student_id=student_user.id)
    data = get_json(
        client.patch(
            f"/api/doubts/{doubt.id}",
            json={
                "description": "  <script>alert(1)</script>updated description  ",
                "code_snippet": "print('hi')",
                "status": DoubtStatus.resolved.value,
            },
            headers=student_headers,
        ),
        200,
    )
    assert data["description"] == "updated description"
    assert data["code_snippet"] == "print('hi')"
    assert data["status"] == DoubtStatus.resolved.value
