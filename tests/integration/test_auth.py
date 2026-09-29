"""Integration tests for the auth router against real PostgreSQL + Redis."""

import pytest

from tests.factories.users import SHARED_PASSWORD, make_student
from tests.utils.helpers import get_json


@pytest.mark.integration
def test_signup_creates_student(client):
    payload = {
        "email": "new.student@example.com",
        "password": "strongpass123",
        "full_name": "New Student",
    }
    data = get_json(client.post("/api/auth/signup", json=payload), 201)
    assert data["email"] == "new.student@example.com"
    assert data["role"] == "student"
    assert data["full_name"] == "New Student"
    assert "id" in data


@pytest.mark.integration
def test_signup_rejects_duplicate_email(client):
    payload = {
        "email": "dupe@example.com",
        "password": "strongpass123",
        "full_name": "First User",
    }
    get_json(client.post("/api/auth/signup", json=payload), 201)
    resp = client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.integration
def test_login_returns_token(client, db, password_hash):
    user = make_student(db, password_hash=password_hash)
    data = get_json(
        client.post(
            "/api/auth/login",
            data={"username": user.email, "password": SHARED_PASSWORD},
        ),
        200,
    )
    assert data["token_type"] == "bearer"
    assert data["access_token"]


@pytest.mark.integration
def test_login_rejects_wrong_password(client, db, password_hash):
    user = make_student(db, password_hash=password_hash)
    resp = client.post(
        "/api/auth/login",
        data={"username": user.email, "password": "wrong-password"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
def test_me_returns_current_user(client, student_headers, student_user):
    data = get_json(client.get("/api/auth/me", headers=student_headers), 200)
    assert data["id"] == student_user.id
    assert data["email"] == student_user.email


@pytest.mark.integration
def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.integration
def test_me_rejects_invalid_token(client):
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401
