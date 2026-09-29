from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import CurrentUser, DbDep
from app.jobs.client import enqueue_job
from app.models import AIFeedback, Problem, Submission, SubmissionResult, TestCase, UserRole
from app.ratelimit import rate_limit
from app.schemas import (
    AIFeedbackOut,
    SubmissionCreate,
    SubmissionDetailOut,
    SubmissionOut,
    SubmissionResultOut,
)
from app.services.grading import LANGUAGES, supported_languages

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def _load_submission(db: Session, submission_id: int) -> Submission:
    submission = db.scalar(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.results))
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


def _authorize_view(db: Session, user, submission: Submission) -> None:
    if user.role in (UserRole.teacher, UserRole.admin):
        return
    if submission.student_id != user.id:
        raise HTTPException(status_code=403, detail="Not your submission")


@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    payload: SubmissionCreate,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(6, 60, "create_submission"))],
) -> Submission:
    if db.get(Problem, payload.problem_id) is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    if payload.language not in LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language. Supported: {', '.join(supported_languages())}",
        )

    submission = Submission(
        student_id=user.id,
        problem_id=payload.problem_id,
        language=payload.language,
        source_code=payload.source_code,
    )
    db.add(submission)
    db.flush()

    db.add(AIFeedback(submission_id=submission.id))
    db.commit()
    db.refresh(submission)

    await enqueue_job("grade_submission", submission.id)
    return submission


@router.get("", response_model=list[SubmissionOut])
def list_submissions(
    db: DbDep,
    user: CurrentUser,
    problem_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
) -> list[Submission]:
    query = select(Submission)
    if user.role not in (UserRole.teacher, UserRole.admin):
        query = query.where(Submission.student_id == user.id)
    elif student_id is not None:
        query = query.where(Submission.student_id == student_id)
    if problem_id is not None:
        query = query.where(Submission.problem_id == problem_id)

    return list(db.scalars(query.order_by(Submission.submitted_at.desc())))


@router.get("/{submission_id}", response_model=SubmissionDetailOut)
def get_submission(submission_id: int, db: DbDep, user: CurrentUser) -> Submission:
    submission = _load_submission(db, submission_id)
    _authorize_view(db, user, submission)
    return submission


@router.get("/{submission_id}/results", response_model=list[SubmissionResultOut])
def get_submission_results(
    submission_id: int,
    db: DbDep,
    user: CurrentUser,
) -> list[SubmissionResultOut]:
    submission = _load_submission(db, submission_id)
    _authorize_view(db, user, submission)

    test_cases = {
        tc.id: tc
        for tc in db.scalars(
            select(TestCase).where(TestCase.problem_id == submission.problem_id)
        )
    }
    is_privileged = user.role in (UserRole.teacher, UserRole.admin)

    output = []
    for result in submission.results:
        tc = test_cases.get(result.test_case_id)
        is_hidden = tc.is_hidden if tc is not None else False
        show_details = is_privileged or not is_hidden
        output.append(
            SubmissionResultOut(
                id=result.id,
                test_case_id=result.test_case_id,
                passed=result.passed,
                verdict=result.verdict,
                exec_time_ms=result.exec_time_ms,
                memory_kb=result.memory_kb,
                input=tc.input if (show_details and tc is not None) else None,
                expected_output=tc.expected_output if (show_details and tc is not None) else None,
                actual_output=result.actual_output if show_details else None,
            )
        )
    return output


@router.get("/{submission_id}/ai-feedback", response_model=AIFeedbackOut)
def get_ai_feedback(
    submission_id: int,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "read_feedback"))],
) -> AIFeedback:
    submission = _load_submission(db, submission_id)
    _authorize_view(db, user, submission)

    feedback = db.scalar(select(AIFeedback).where(AIFeedback.submission_id == submission_id))
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback
