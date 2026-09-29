from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbDep
from app.models import AIAnswer, AnswerStatus, ReviewAction, ReviewLog, User, UserRole
from app.ratelimit import rate_limit
from app.schemas import AnalyticsOut, ReviewerStat

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/reviews", response_model=AnalyticsOut)
def review_analytics(
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(30, 60, "analytics"))],
) -> AnalyticsOut:
    if user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    action_rows = db.execute(
        select(ReviewLog.action, func.count()).group_by(ReviewLog.action)
    ).all()
    reviews_by_action = {action.value: count for action, count in action_rows}

    status_rows = db.execute(
        select(AIAnswer.status, func.count()).group_by(AIAnswer.status)
    ).all()
    by_status = {st.value: count for st, count in status_rows}

    total_reviewed = sum(reviews_by_action.values())
    approved_and_edited = reviews_by_action.get(ReviewAction.approved.value, 0) + reviews_by_action.get(
        ReviewAction.edited.value, 0
    )
    approval_rate = round(approved_and_edited / total_reviewed, 4) if total_reviewed else 0.0

    reviewer_rows = db.execute(
        select(User.full_name, func.count())
        .join(ReviewLog, ReviewLog.reviewer_id == User.id)
        .group_by(User.id, User.full_name)
        .order_by(func.count().desc())
        .limit(5)
    ).all()

    return AnalyticsOut(
        pending_reviews=by_status.get(AnswerStatus.pending_review.value, 0),
        generated_answers=sum(by_status.values()),
        approved_answers=by_status.get(AnswerStatus.approved.value, 0),
        rejected_answers=by_status.get(AnswerStatus.rejected.value, 0),
        total_reviewed=total_reviewed,
        approval_rate=approval_rate,
        reviews_by_action=reviews_by_action,
        top_reviewers=[ReviewerStat(name=name, count=count) for name, count in reviewer_rows],
    )
