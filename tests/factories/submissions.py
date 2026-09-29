"""Submission and AI-feedback factories."""

from app.models import AIFeedback, FeedbackStatus, Submission, SubmissionResult, SubmissionStatus, Verdict


def make_submission(
    db,
    *,
    student_id: int,
    problem_id: int,
    language: str = "python",
    source_code: str = "print('accepted')",
    status: SubmissionStatus = SubmissionStatus.queued,
    verdict: Verdict | None = None,
    score: float | None = None,
) -> Submission:
    submission = Submission(
        student_id=student_id,
        problem_id=problem_id,
        language=language,
        source_code=source_code,
        status=status,
        verdict=verdict,
        score=score,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def make_submission_result(
    db,
    *,
    submission_id: int,
    test_case_id: int,
    passed: bool = True,
    verdict: Verdict = Verdict.accepted,
    actual_output: str | None = "5",
    exec_time_ms: int = 5,
    memory_kb: int = 1024,
) -> SubmissionResult:
    result = SubmissionResult(
        submission_id=submission_id,
        test_case_id=test_case_id,
        passed=passed,
        verdict=verdict,
        actual_output=actual_output,
        exec_time_ms=exec_time_ms,
        memory_kb=memory_kb,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def make_ai_feedback(
    db,
    *,
    submission_id: int,
    status: FeedbackStatus = FeedbackStatus.success,
    readability: str = "Clean solution.",
    complexity: str = "O(1) time and space.",
    best_practices: str = "Good naming.",
    optimization: str = "Nothing to optimize.",
    model_version: str = "mock-gemini-2.5-flash",
) -> AIFeedback:
    feedback = AIFeedback(
        submission_id=submission_id,
        status=status,
        readability=readability,
        complexity=complexity,
        best_practices=best_practices,
        optimization=optimization,
        model_version=model_version,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
