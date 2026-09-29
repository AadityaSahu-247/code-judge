"""Notification factory."""

from app.models import Notification


def make_notification(
    db,
    *,
    user_id: int,
    message: str = "Your doubt has been answered.",
    type: str = "doubt_answered",
    related_doubt_id: int | None = None,
    read: bool = False,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        message=message,
        related_doubt_id=related_doubt_id,
        read=read,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
