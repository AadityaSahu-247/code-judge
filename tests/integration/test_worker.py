"""Integration tests for the ARQ worker pipeline replayed against real
PostgreSQL (docker sandbox and LLM providers are mocked)."""

import pytest

from app.models import AnswerStatus, FeedbackStatus, SubmissionStatus, Verdict
from app.services import grading
from tests.factories.doubts import make_doubt
from tests.factories.problems import make_problem_with_cases
from tests.factories.submissions import make_ai_feedback, make_submission
from tests.mocks.arq import FakeQueueRedis
from tests.utils.jobs import run_job


@pytest.mark.integration
def test_grade_submission_pipeline(client, db, password_hash, student_user, problem_with_cases):
    problem, cases = problem_with_cases
    submission = make_submission(
        db,
        student_id=student_user.id,
        problem_id=problem.id,
        language="python",
        source_code="print('accepted')",
        status=SubmissionStatus.queued,
    )
    make_ai_feedback(db, submission_id=submission.id, status=FeedbackStatus.pending)

    queue = FakeQueueRedis()
    run_job("grade_submission", submission.id, redis=queue)

    db.expire_all()
    graded = db.get(type(submission), submission.id)
    assert graded.status == SubmissionStatus.graded
    assert graded.verdict == Verdict.accepted
    assert graded.score == 100.0
    assert len(graded.results) == len(cases)
    assert queue.enqueued == [("generate_feedback", (submission.id,), {})]


@pytest.mark.integration
def test_grade_submission_partial_score(client, db, password_hash, student_user, problem):
    from tests.factories.problems import make_test_case

    visible = make_test_case(db, problem.id, input_="2 3", expected_output="5", weight=1.0)
    hidden = make_test_case(db, problem.id, input_="9 1", expected_output="10", is_hidden=True, weight=3.0)

    def fake_run(language, source_code, test_case, container_name):
        return grading.CaseResult(
            test_case_id=test_case.id,
            passed=test_case.id == visible.id,
            verdict=Verdict.accepted if test_case.id == visible.id else Verdict.wrong_answer,
            actual_output="5" if test_case.id == visible.id else "0",
            exec_time_ms=1,
        )

    from app.services import grading as grading_module

    original = grading_module._run_test_case
    grading_module._run_test_case = fake_run
    try:
        submission = make_submission(
            db,
            student_id=student_user.id,
            problem_id=problem.id,
            status=SubmissionStatus.queued,
        )
        run_job("grade_submission", submission.id, redis=FakeQueueRedis())
    finally:
        grading_module._run_test_case = original

    db.expire_all()
    graded = db.get(type(submission), submission.id)
    assert graded.status == SubmissionStatus.graded
    assert graded.score == 25.0
    assert graded.verdict == Verdict.wrong_answer


@pytest.mark.integration
def test_grade_submission_marks_single_failed_case_runtime_error(client, db, password_hash, student_user, problem):
    from tests.factories.problems import make_test_case

    make_test_case(db, problem.id, input_="1", expected_output="1", weight=1.0)
    make_test_case(db, problem.id, input_="2", expected_output="2", weight=1.0)

    def boom_run(language, source_code, test_case, container_name):
        if test_case.expected_output == "2":
            raise RuntimeError("sandbox crashed")
        return grading.CaseResult(
            test_case_id=test_case.id,
            passed=True,
            verdict=Verdict.accepted,
            actual_output=test_case.expected_output,
            exec_time_ms=1,
        )

    from app.services import grading as grading_module

    original = grading_module._run_test_case
    grading_module._run_test_case = boom_run
    try:
        submission = make_submission(
            db,
            student_id=student_user.id,
            problem_id=problem.id,
            status=SubmissionStatus.queued,
        )
        run_job("grade_submission", submission.id, redis=FakeQueueRedis())
    finally:
        grading_module._run_test_case = original

    db.expire_all()
    graded = db.get(type(submission), submission.id)
    assert graded.status == SubmissionStatus.graded
    assert graded.verdict == Verdict.runtime_error
    assert graded.score == 50.0
    assert len(graded.results) == 2
    failed_result = next(r for r in graded.results if r.verdict == Verdict.runtime_error)
    assert failed_result.actual_output == ""


@pytest.mark.integration
def test_grade_submission_marks_failed_on_unexpected_error(client, db, password_hash, student_user, problem):
    from tests.factories.problems import make_test_case

    make_test_case(db, problem.id, input_="1", expected_output="1", weight=1.0)

    from app.services import grading as grading_module

    original = grading_module.SessionLocal
    original_run = grading_module._run_test_case

    class BoomSession:
        def __init__(self, real):
            self._real = real
            self.commits = 0

        def __getattr__(self, name):
            return getattr(self._real, name)

        def commit(self):
            self.commits += 1
            if self.commits == 2:
                raise RuntimeError("database full")
            return self._real.commit()

        def close(self):
            self._real.close()

    def failing_session():
        return BoomSession(original())

    grading_module.SessionLocal = failing_session
    try:
        submission = make_submission(
            db,
            student_id=student_user.id,
            problem_id=problem.id,
            status=SubmissionStatus.queued,
        )
        with pytest.raises(RuntimeError, match="database full"):
            run_job("grade_submission", submission.id, redis=FakeQueueRedis())
    finally:
        grading_module.SessionLocal = original
        grading_module._run_test_case = original_run

    db.expire_all()
    failed = db.get(type(submission), submission.id)
    assert failed.status == SubmissionStatus.failed


@pytest.mark.integration
def test_generate_feedback_updates_row(client, db, password_hash, student_user, problem):
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
    row = db.scalar(select(AIFeedback).where(AIFeedback.submission_id == submission.id))
    assert row.status == FeedbackStatus.success
    assert row.readability
    assert row.complexity
    assert row.best_practices
    assert row.optimization
    assert row.model_version == "mock-gemini-2.5-flash"


@pytest.mark.integration
def test_generate_answer_pipeline(client, db, student_user):
    from tests.factories.doubts import make_ai_answer

    doubt = make_doubt(db, student_id=student_user.id)
    make_ai_answer(db, doubt_id=doubt.id, draft_content=None)
    run_job("generate_answer", doubt.id, redis=FakeQueueRedis())

    from app.models import AIAnswer
    from sqlalchemy import select

    db.expire_all()
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt.id))
    assert answer.status == AnswerStatus.pending_review
    assert answer.draft_content
    assert answer.model_version == "mock-gemini-2.5-flash"
    assert answer.generated_at is not None


@pytest.mark.integration
def test_generate_answer_skips_when_doubt_missing(client, db, password_hash):
    result = run_job("generate_answer", 999999, redis=FakeQueueRedis())
    assert "doubt 999999" in result


@pytest.mark.integration
def test_grade_missing_submission_is_noop(client, db, password_hash):
    queue = FakeQueueRedis()
    result = run_job("grade_submission", 999999, redis=queue)
    assert "submission 999999" in result
    assert queue.enqueued == [("generate_feedback", (999999,), {})]
