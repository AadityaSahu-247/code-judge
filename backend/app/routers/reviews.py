from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.orm import joinedload

from app.deps import CurrentUser, DbDep
from app.jobs.client import enqueue_job
from app.models import AIAnswer, AnswerStatus, Doubt, DoubtStatus, Notification, ReviewAction, ReviewLog, UserRole
from app.ratelimit import rate_limit
from app.sanitize import sanitize_text
from app.schemas import (
    ReviewAnswerOut,
    ReviewApproveIn,
    ReviewEditIn,
    ReviewLogOut,
    ReviewRejectIn,
    ReviewRegenerateIn,
)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def _require_staff(user) -> None:
    if user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher only")


def _load_answer(db, answer_id: int) -> AIAnswer:
    answer = db.scalar(
        select(AIAnswer)
        .where(AIAnswer.id == answer_id)
        .options(
            joinedload(AIAnswer.doubt).joinedload(Doubt.author),
            joinedload(AIAnswer.claimed_by),
        )
    )
    if answer is None:
        raise HTTPException(status_code=404, detail="AI answer not found")
    return answer


def _to_review_out(answer: AIAnswer) -> ReviewAnswerOut:
    doubt = answer.doubt
    return ReviewAnswerOut(
        id=answer.id,
        doubt_id=answer.doubt_id,
        doubt_title=doubt.title if doubt else "Unknown doubt",
        student_name=doubt.author.full_name if doubt and doubt.author else None,
        status=answer.status,
        draft_content=answer.draft_content,
        moderation_flagged=answer.moderation_flagged,
        moderation_reason=answer.moderation_reason,
        model_version=answer.model_version,
        generated_at=answer.generated_at,
        claimed_by_id=answer.claimed_by_id,
        claimed_by_name=answer.claimed_by.full_name if answer.claimed_by else None,
    )


def _notify_student(db, doubt, message: str) -> None:
    db.add(
        Notification(
            user_id=doubt.student_id,
            type="doubt_answered",
            message=message,
            related_doubt_id=doubt.id,
        )
    )


def _ensure_not_claimed_by_other(answer: AIAnswer, user) -> None:
    if answer.claimed_by_id is not None and answer.claimed_by_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This answer is currently being reviewed by another teacher",
        )


@router.get("/answers", response_model=list[ReviewAnswerOut])
def list_pending_answers(
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "list_reviews"))],
) -> list[ReviewAnswerOut]:
    _require_staff(user)
    answers = list(
        db.scalars(
            select(AIAnswer)
            .where(AIAnswer.status == AnswerStatus.pending_review)
            .options(
                joinedload(AIAnswer.doubt).joinedload(Doubt.author),
                joinedload(AIAnswer.claimed_by),
            )
            .order_by(AIAnswer.generated_at.asc().nullsfirst(), AIAnswer.id.asc())
        )
    )
    return [_to_review_out(a) for a in answers]


@router.post("/{answer_id}/claim", response_model=ReviewAnswerOut)
def claim_answer(
    answer_id: int,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "claim_review"))],
) -> ReviewAnswerOut:
    _require_staff(user)
    result = db.execute(
        update(AIAnswer)
        .where(
            AIAnswer.id == answer_id,
            AIAnswer.status == AnswerStatus.pending_review,
            or_(AIAnswer.claimed_by_id.is_(None), AIAnswer.claimed_by_id == user.id),
        )
        .values(claimed_by_id=user.id, claimed_at=datetime.now(timezone.utc))
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This answer is already claimed by another teacher or has been reviewed",
        )
    db.commit()
    answer = _load_answer(db, answer_id)
    return _to_review_out(answer)


@router.post("/{answer_id}/approve", response_model=ReviewAnswerOut)
def approve_answer(
    answer_id: int,
    payload: ReviewApproveIn,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "review_action"))],
) -> ReviewAnswerOut:
    _require_staff(user)
    answer = _load_answer(db, answer_id)
    _ensure_not_claimed_by_other(answer, user)

    result = db.execute(
        update(AIAnswer)
        .where(AIAnswer.id == answer_id, AIAnswer.status == AnswerStatus.pending_review)
        .values(
            status=AnswerStatus.approved,
            reviewed_by_id=user.id,
            reviewed_at=datetime.now(timezone.utc),
            claimed_by_id=None,
            claimed_at=None,
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="This answer has already been reviewed")

    doubt = answer.doubt
    if doubt is not None:
        doubt.status = DoubtStatus.answered
        _notify_student(db, doubt, f'Your doubt "{doubt.title}" has been answered by a teacher.')

    db.add(
        ReviewLog(
            answer_id=answer_id,
            reviewer_id=user.id,
            action=ReviewAction.approved,
            note=payload.note,
        )
    )
    db.commit()
    answer = _load_answer(db, answer_id)
    return _to_review_out(answer)


@router.post("/{answer_id}/edit", response_model=ReviewAnswerOut)
def edit_answer(
    answer_id: int,
    payload: ReviewEditIn,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "review_action"))],
) -> ReviewAnswerOut:
    _require_staff(user)
    answer = _load_answer(db, answer_id)
    _ensure_not_claimed_by_other(answer, user)
    edited = sanitize_text(payload.edited_content)
    if not edited:
        raise HTTPException(status_code=422, detail="Edited content is empty after sanitization")

    result = db.execute(
        update(AIAnswer)
        .where(AIAnswer.id == answer_id, AIAnswer.status == AnswerStatus.pending_review)
        .values(
            status=AnswerStatus.approved,
            draft_content=edited,
            reviewed_by_id=user.id,
            reviewed_at=datetime.now(timezone.utc),
            claimed_by_id=None,
            claimed_at=None,
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="This answer has already been reviewed")

    doubt = answer.doubt
    if doubt is not None:
        doubt.status = DoubtStatus.answered
        _notify_student(db, doubt, f'Your doubt "{doubt.title}" has been answered by a teacher.')

    db.add(
        ReviewLog(
            answer_id=answer_id,
            reviewer_id=user.id,
            action=ReviewAction.edited,
            edited_content=edited,
            note=payload.note,
        )
    )
    db.commit()
    answer = _load_answer(db, answer_id)
    return _to_review_out(answer)


@router.post("/{answer_id}/reject", response_model=ReviewAnswerOut)
def reject_answer(
    answer_id: int,
    payload: ReviewRejectIn,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "review_action"))],
) -> ReviewAnswerOut:
    _require_staff(user)
    answer = _load_answer(db, answer_id)
    _ensure_not_claimed_by_other(answer, user)

    result = db.execute(
        update(AIAnswer)
        .where(AIAnswer.id == answer_id, AIAnswer.status == AnswerStatus.pending_review)
        .values(
            status=AnswerStatus.rejected,
            reviewed_by_id=user.id,
            reviewed_at=datetime.now(timezone.utc),
            claimed_by_id=None,
            claimed_at=None,
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="This answer has already been reviewed")

    db.add(
        ReviewLog(
            answer_id=answer_id,
            reviewer_id=user.id,
            action=ReviewAction.rejected,
            note=payload.note,
        )
    )
    db.commit()
    answer = _load_answer(db, answer_id)
    return _to_review_out(answer)


@router.post("/{answer_id}/regenerate", response_model=ReviewAnswerOut)
async def regenerate_answer(
    answer_id: int,
    payload: ReviewRegenerateIn,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "regenerate_answer"))],
) -> ReviewAnswerOut:
    _require_staff(user)
    answer = _load_answer(db, answer_id)
    if answer.status != AnswerStatus.rejected:
        raise HTTPException(status_code=409, detail="Only rejected answers can be regenerated")
    _ensure_not_claimed_by_other(answer, user)

    note = (payload.note or "").strip()
    if not note:
        latest = db.scalar(
            select(ReviewLog)
            .where(
                ReviewLog.answer_id == answer_id,
                ReviewLog.action == ReviewAction.rejected,
            )
            .order_by(ReviewLog.created_at.desc())
        )
        note = (latest.note or "").strip() if latest else ""

    answer.status = AnswerStatus.pending_review
    answer.draft_content = None
    answer.raw_model_response = None
    answer.model_version = None
    answer.generated_at = None
    answer.reviewed_at = None
    answer.reviewed_by_id = None
    answer.claimed_by_id = None
    answer.claimed_at = None
    db.commit()

    await enqueue_job("generate_answer", answer.doubt_id, note or None)
    answer = _load_answer(db, answer_id)
    return _to_review_out(answer)


@router.get("/{answer_id}/logs", response_model=list[ReviewLogOut])
def list_review_logs(
    answer_id: int,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "read_review_logs"))],
) -> list[ReviewLogOut]:
    _require_staff(user)
    _load_answer(db, answer_id)
    logs = list(
        db.scalars(
            select(ReviewLog)
            .where(ReviewLog.answer_id == answer_id)
            .options(joinedload(ReviewLog.reviewer))
            .order_by(ReviewLog.created_at.asc())
        )
    )
    return [
        ReviewLogOut(
            id=log.id,
            answer_id=log.answer_id,
            reviewer_name=log.reviewer.full_name if log.reviewer else None,
            action=log.action,
            edited_content=log.edited_content,
            note=log.note,
            created_at=log.created_at,
        )
        for log in logs
    ]
