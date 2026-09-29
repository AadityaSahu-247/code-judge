"""Auth fixtures: shared password hash, users per role and their JWT tokens."""

from __future__ import annotations

import pytest

from app.models import UserRole
from app.security import create_access_token, hash_password
from tests.factories import users as user_factories
from tests.utils.helpers import auth_header


@pytest.fixture(scope="session")
def password_hash():
    """One shared bcrypt hash so the expensive hashing runs once per session."""
    return hash_password(user_factories.SHARED_PASSWORD)


@pytest.fixture
def student_user(db, password_hash):
    return user_factories.make_student(db, password_hash=password_hash)


@pytest.fixture
def teacher_user(db, password_hash):
    return user_factories.make_teacher(db, password_hash=password_hash)


@pytest.fixture
def admin_user(db, password_hash):
    return user_factories.make_admin(db, password_hash=password_hash)


@pytest.fixture
def student_token(student_user) -> str:
    return create_access_token(subject=str(student_user.id), role=UserRole.student.value)


@pytest.fixture
def teacher_token(teacher_user) -> str:
    return create_access_token(subject=str(teacher_user.id), role=UserRole.teacher.value)


@pytest.fixture
def admin_token(admin_user) -> str:
    return create_access_token(subject=str(admin_user.id), role=UserRole.admin.value)


@pytest.fixture
def auth_headers() -> dict:
    """Return a factory producing ``Authorization`` header dicts."""
    return auth_header


@pytest.fixture
def student_headers(student_token):
    return auth_header(student_token)


@pytest.fixture
def teacher_headers(teacher_token):
    return auth_header(teacher_token)


@pytest.fixture
def admin_headers(admin_token):
    return auth_header(admin_token)
