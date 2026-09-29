"""Performance / concurrency tests.

These use real PostgreSQL + Redis but keep the docker sandbox and LLM
providers mocked, so they measure API/DB behaviour under load rather than
sandbox throughput. They are opt-in via the ``performance`` marker.
"""

import asyncio

import pytest

from tests.factories.problems import make_problem
from tests.factories.users import make_student
from tests.mocks.arq import FakeQueueRedis
from tests.utils.helpers import auth_header
from tests.utils.jobs import run_job


@pytest.mark.performance
def test_concurrent_submission_creates(client, db, password_hash, problem, job_recorder):
    students = [
        make_student(db, password_hash=password_hash, email=f"perf.{i}@example.com")
        for i in range(5)
    ]
    headers = [
        auth_header(_token(u.id)) for u in students
    ]

    async def _submit(h):
        resp = await asyncio.to_thread(
            client.post,
            "/api/submissions",
            json={"problem_id": problem.id, "language": "python", "source_code": "print(1)"},
            headers=h,
        )
        return resp.status_code

    results = asyncio.run(_run_all([_submit(h) for h in headers]))
    assert all(code == 201 for code in results)
    assert len(job_recorder.names) == 5


@pytest.mark.performance
def test_sequential_grade_throughput(client, db, password_hash, problem_with_cases):
    problem, cases = problem_with_cases
    student = make_student(db, password_hash=password_hash, email="perf.grade@example.com")

    ids = []
    for i in range(10):
        submission = _make_submission_row(db, student.id, problem.id)
        ids.append(submission.id)

    queue = FakeQueueRedis()
    for submission_id in ids:
        run_job("grade_submission", submission_id, redis=queue)

    db.expire_all()
    from sqlalchemy import select
    from app.models import Submission, SubmissionStatus

    rows = db.scalars(select(Submission).where(Submission.id.in_(ids))).all()
    assert all(s.status == SubmissionStatus.graded for s in rows)
    assert all(s.score == 100.0 for s in rows)


@pytest.mark.performance
@pytest.mark.real_ratelimit
def test_rate_limiter_rejects_burst_over_limit(client, db, password_hash, problem, job_recorder):
    """With the real rate limiter active, a burst over the limit is rejected."""
    student = make_student(db, password_hash=password_hash, email="perf.rl@example.com")
    headers = auth_header(_token(student.id))

    payload = {"problem_id": problem.id, "language": "python", "source_code": "print(1)"}
    statuses = [
        client.post("/api/submissions", json=payload, headers=headers).status_code
        for _ in range(8)
    ]
    assert statuses[:6] == [201] * 6
    assert statuses[6] == 429 and statuses[7] == 429
    assert len(job_recorder.names) == 6


def _token(user_id: int) -> str:
    from app.security import create_access_token

    return create_access_token(subject=str(user_id), role="student")


def _make_submission_row(db, student_id, problem_id):
    from tests.factories.submissions import make_submission

    return make_submission(db, student_id=student_id, problem_id=problem_id)


async def _run_all(coros):
    return await asyncio.gather(*coros)
