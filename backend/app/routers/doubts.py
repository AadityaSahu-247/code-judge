from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.deps import CurrentUser, DbDep
from app.jobs.client import enqueue_job
from app.models import AIAnswer, AnswerStatus, Doubt, Problem, User, UserRole
from app.ratelimit import rate_limit
from app.sanitize import sanitize_text
from app.schemas import (
    AIAnswerOut,
    DoubtCreate,
    DoubtDetailOut,
    DoubtOut,
    DoubtSimilarOut,
    DoubtUpdate,
)
from app.services.similarity import text_similarity

router = APIRouter(prefix="/api/doubts", tags=["doubts"])


def _to_out(doubt: Doubt) -> DoubtDetailOut:
    return DoubtDetailOut(
        id=doubt.id,
        student_id=doubt.student_id,
        student_name=doubt.author.full_name if doubt.author else None,
        title=doubt.title,
        status=doubt.status,
        related_problem_id=doubt.related_problem_id,
        created_at=doubt.created_at,
        description=doubt.description,
        code_snippet=doubt.code_snippet,
    )


def _load_doubt(db: Session, doubt_id: int) -> Doubt:
    doubt = db.scalar(
        select(Doubt).where(Doubt.id == doubt_id).options(joinedload(Doubt.author))
    )
    if doubt is None:
        raise HTTPException(status_code=404, detail="Doubt not found")
    return doubt


def _can_modify(doubt: Doubt, user) -> bool:
    return doubt.student_id == user.id or user.role in (UserRole.teacher, UserRole.admin)


@router.post("", response_model=DoubtDetailOut, status_code=status.HTTP_201_CREATED)
async def create_doubt(
    payload: DoubtCreate,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(5, 60, "create_doubt"))],
) -> DoubtDetailOut:
    if payload.related_problem_id is not None and db.get(Problem, payload.related_problem_id) is None:
        raise HTTPException(status_code=404, detail="Related problem not found")

    doubt = Doubt(
        student_id=user.id,
        title=sanitize_text(payload.title) or "Untitled doubt",
        description=sanitize_text(payload.description) or "",
        code_snippet=sanitize_text(payload.code_snippet),
        related_problem_id=payload.related_problem_id,
    )
    db.add(doubt)
    db.flush()
    db.add(AIAnswer(doubt_id=doubt.id))
    db.commit()
    db.refresh(doubt)
    doubt.author = user

    await enqueue_job("generate_answer", doubt.id)
    return _to_out(doubt)


@router.get("", response_model=list[DoubtOut])
def list_doubts(
    db: DbDep,
    user: CurrentUser,
    q: str | None = Query(default=None),
    problem_id: int | None = Query(default=None),
) -> list[DoubtOut]:
    query = select(Doubt).options(joinedload(Doubt.author))

    if q:
        escaped = q.strip().replace("%", "\\%").replace("_", "\\_")
        term = f"%{escaped}%"
        query = query.where(
            or_(
                Doubt.title.ilike(term, escape="\\"),
                Doubt.description.ilike(term, escape="\\"),
            )
        )
    if problem_id is not None:
        query = query.where(Doubt.related_problem_id == problem_id)

    doubts = list(db.scalars(query.order_by(Doubt.created_at.desc())))
    return [_to_out(d) for d in doubts]


@router.get("/similar", response_model=list[DoubtSimilarOut])
def similar_doubts(
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "similar_doubts"))],
    doubt_id: int = Query(...),
    limit: int = Query(default=5, ge=1, le=20),
) -> list[DoubtSimilarOut]:
    source = _load_doubt(db, doubt_id)
    source_text = f"{source.title} {source.description}"

    scored: list[tuple[float, Doubt]] = []
    for candidate in db.scalars(
        select(Doubt).where(Doubt.id != doubt_id).options(joinedload(Doubt.author))
    ):
        similarity = text_similarity(
            source_text, f"{candidate.title} {candidate.description}"
        )
        if similarity > 0.15:
            scored.append((similarity, candidate))
    scored.sort(key=lambda item: -item[0])

    output = []
    for similarity, candidate in scored[:limit]:
        base = _to_out(candidate)
        output.append(
            DoubtSimilarOut(
                id=base.id,
                student_id=base.student_id,
                student_name=base.student_name,
                title=base.title,
                status=base.status,
                related_problem_id=base.related_problem_id,
                created_at=base.created_at,
                similarity=round(similarity, 4),
            )
        )
    return output


@router.get("/{doubt_id}", response_model=DoubtDetailOut)
def get_doubt(doubt_id: int, db: DbDep, user: CurrentUser) -> DoubtDetailOut:
    return _to_out(_load_doubt(db, doubt_id))


@router.patch("/{doubt_id}", response_model=DoubtDetailOut)
def update_doubt(
    doubt_id: int,
    payload: DoubtUpdate,
    db: DbDep,
    user: CurrentUser,
) -> DoubtDetailOut:
    doubt = _load_doubt(db, doubt_id)
    if not _can_modify(doubt, user):
        raise HTTPException(status_code=403, detail="Not allowed to edit this doubt")

    data = payload.model_dump(exclude_unset=True)
    if "title" in data:
        doubt.title = sanitize_text(data["title"]) or doubt.title
    if "description" in data:
        doubt.description = sanitize_text(data["description"]) or ""
    if "code_snippet" in data:
        doubt.code_snippet = sanitize_text(data["code_snippet"])
    if "status" in data:
        doubt.status = data["status"]

    db.commit()
    db.refresh(doubt)
    return _to_out(doubt)


@router.delete("/{doubt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doubt(doubt_id: int, db: DbDep, user: CurrentUser) -> None:
    doubt = _load_doubt(db, doubt_id)
    if not _can_modify(doubt, user):
        raise HTTPException(status_code=403, detail="Not allowed to delete this doubt")
    db.delete(doubt)
    db.commit()


@router.get("/{doubt_id}/answer", response_model=AIAnswerOut)
def get_doubt_answer(
    doubt_id: int,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "read_answer"))],
) -> AIAnswerOut:
    _load_doubt(db, doubt_id)
    answer = db.scalar(select(AIAnswer).where(AIAnswer.doubt_id == doubt_id))
    if answer is None:
        raise HTTPException(status_code=404, detail="AI answer not generated yet")

    can_view_draft = user.role in (UserRole.teacher, UserRole.admin) or answer.status == AnswerStatus.approved
    return AIAnswerOut(
        id=answer.id,
        doubt_id=answer.doubt_id,
        status=answer.status,
        draft_content=answer.draft_content if can_view_draft else None,
        moderation_flagged=answer.moderation_flagged,
        moderation_reason=answer.moderation_reason,
        model_version=answer.model_version,
        generated_at=answer.generated_at,
    )
