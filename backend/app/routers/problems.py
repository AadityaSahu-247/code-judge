from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.deps import CurrentUser, DbDep, require_role
from app.models import Problem, Submission, TestCase, User, UserRole
from app.ratelimit import rate_limit
from app.schemas import (
    PlagiarismPairOut,
    PlagiarismReportOut,
    ProblemDetailOut,
    ProblemOut,
    TestCaseCreate,
    TestCaseOut,
)
from app.services.similarity import code_similarity

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get("", response_model=list[ProblemOut])
def list_problems(db: DbDep, current_user: CurrentUser) -> list[Problem]:
    return list(db.scalars(select(Problem).order_by(Problem.id)))


@router.get("/{problem_id}", response_model=ProblemDetailOut)
def get_problem(problem_id: int, db: DbDep, current_user: CurrentUser) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


@router.get("/{problem_id}/testcases", response_model=list[TestCaseOut])
def list_visible_testcases(
    problem_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> list[TestCase]:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    query = select(TestCase).where(TestCase.problem_id == problem_id)
    if current_user.role not in (UserRole.teacher, UserRole.admin):
        query = query.where(TestCase.is_hidden.is_(False))
    return list(db.scalars(query.order_by(TestCase.id)))


@router.get("/{problem_id}/plagiarism", response_model=PlagiarismReportOut)
def plagiarism_report(
    problem_id: int,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "plagiarism_report"))],
    threshold: float = Query(default=0.6, ge=0.0, le=1.0),
) -> PlagiarismReportOut:
    if current_user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    submissions = list(
        db.scalars(
            select(Submission).where(Submission.problem_id == problem_id)
        )
    )
    names = {
        u.id: u.full_name
        for u in db.scalars(select(User).where(User.id.in_({s.student_id for s in submissions})))
    }

    pairs: list[PlagiarismPairOut] = []
    for i in range(len(submissions)):
        for j in range(i + 1, len(submissions)):
            a, b = submissions[i], submissions[j]
            if a.student_id == b.student_id:
                continue
            similarity = code_similarity(a.source_code, b.source_code)
            if similarity >= threshold:
                pairs.append(
                    PlagiarismPairOut(
                        submission_a_id=a.id,
                        submission_b_id=b.id,
                        student_a_name=names.get(a.student_id),
                        student_b_name=names.get(b.student_id),
                        verdict_a=a.verdict,
                        verdict_b=b.verdict,
                        score_a=a.score,
                        score_b=b.score,
                        similarity=round(similarity, 4),
                    )
                )
    pairs.sort(key=lambda p: -p.similarity)
    return PlagiarismReportOut(
        problem_id=problem.id,
        problem_title=problem.title,
        threshold=threshold,
        pairs=pairs,
    )


@router.post(
    "/{problem_id}/testcases",
    response_model=list[TestCaseOut],
    status_code=status.HTTP_201_CREATED,
)
def add_testcases(
    problem_id: int,
    payload: list[TestCaseCreate],
    db: DbDep,
    _: Annotated[object, Depends(require_role(UserRole.teacher, UserRole.admin))],
) -> list[TestCase]:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    created = [TestCase(problem_id=problem_id, **item.model_dump()) for item in payload]
    db.add_all(created)
    db.commit()
    for tc in created:
        db.refresh(tc)
    return created
