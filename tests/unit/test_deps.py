"""Unit tests for the auth dependencies (get_current_user / require_role)."""

import pytest
from fastapi import HTTPException

from app.deps import get_current_user, require_role
from app.models import UserRole
from app.security import create_access_token
from tests.factories.users import make_user


@pytest.mark.unit
def test_get_current_user_missing_user_raises_401(db):
    token = create_access_token(subject="999999", role=UserRole.student)
    with pytest.raises(HTTPException) as exc:
        get_current_user(db, token)
    assert exc.value.status_code == 401


@pytest.mark.unit
def test_get_current_user_invalid_token_raises_401(db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(db, "not-a-jwt")
    assert exc.value.status_code == 401
    assert exc.value.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.unit
def test_require_role_allows_matching_role(db):
    student = make_user(db, role=UserRole.student)
    dep = require_role(UserRole.student)
    assert dep(student) is student


@pytest.mark.unit
def test_require_role_denies_other_role(db):
    student = make_user(db, role=UserRole.student)
    dep = require_role(UserRole.teacher)
    with pytest.raises(HTTPException) as exc:
        dep(student)
    assert exc.value.status_code == 403
