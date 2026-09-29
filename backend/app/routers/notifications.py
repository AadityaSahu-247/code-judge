from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbDep
from app.models import Notification
from app.ratelimit import rate_limit
from app.schemas import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(60, 60, "list_notifications"))],
) -> list[NotificationOut]:
    rows = list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
        )
    )
    return [
        NotificationOut(
            id=n.id,
            type=n.type,
            message=n.message,
            related_doubt_id=n.related_doubt_id,
            read=n.read,
            created_at=n.created_at,
        )
        for n in rows
    ]


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[object, Depends(rate_limit(60, 60, "read_notifications"))],
) -> NotificationOut:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your notification")

    notification.read = True
    db.commit()
    db.refresh(notification)
    return NotificationOut(
        id=notification.id,
        type=notification.type,
        message=notification.message,
        related_doubt_id=notification.related_doubt_id,
        read=notification.read,
        created_at=notification.created_at,
    )
