"""Integration tests for the notifications router."""

import pytest

from tests.factories.notifications import make_notification
from tests.utils.helpers import get_json


@pytest.mark.integration
def test_list_notifications_only_mine(client, student_headers, db, student_user):
    make_notification(db, user_id=student_user.id, message="You have a new answer.")
    data = get_json(client.get("/api/notifications", headers=student_headers), 200)
    assert len(data) == 1
    assert data[0]["message"] == "You have a new answer."
    assert data[0]["read"] is False


@pytest.mark.integration
def test_mark_notification_read(client, student_headers, db, student_user):
    notification = make_notification(db, user_id=student_user.id)
    data = get_json(
        client.patch(f"/api/notifications/{notification.id}/read", headers=student_headers),
        200,
    )
    assert data["read"] is True


@pytest.mark.integration
def test_mark_notification_read_forbidden_for_other_user(
    client, student_headers, db, password_hash
):
    from tests.factories.users import make_student

    owner = make_student(db, password_hash=password_hash, email="notif.owner@test.local")
    notification = make_notification(db, user_id=owner.id)
    resp = client.patch(
        f"/api/notifications/{notification.id}/read", headers=student_headers
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_mark_missing_notification_404(client, student_headers):
    assert client.patch("/api/notifications/999999/read", headers=student_headers).status_code == 404
