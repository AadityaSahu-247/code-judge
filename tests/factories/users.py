"""User factories. A shared password hash keeps hashing cost out of the loop."""

from app.models import User, UserRole
from app.security import hash_password

SHARED_PASSWORD = "password123"

_counter = 0


def _unique_email(role: UserRole, suffix: str) -> str:
    global _counter
    _counter += 1
    base = suffix or f"{role.value}-{_counter}"
    return f"{base}@example.com"


def make_user(
    db,
    *,
    email: str | None = None,
    full_name: str | None = None,
    role: UserRole = UserRole.student,
    password: str = SHARED_PASSWORD,
    password_hash: str | None = None,
) -> User:
    user = User(
        email=email or _unique_email(role, ""),
        password_hash=password_hash or hash_password(password),
        full_name=full_name or f"Test {role.value.title()}",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_student(db, **kwargs) -> User:
    kwargs.setdefault("role", UserRole.student)
    kwargs.setdefault("email", "student@example.com")
    kwargs.setdefault("full_name", "Test Student")
    return make_user(db, **kwargs)


def make_teacher(db, **kwargs) -> User:
    kwargs.setdefault("role", UserRole.teacher)
    kwargs.setdefault("email", "teacher@example.com")
    kwargs.setdefault("full_name", "Test Teacher")
    return make_user(db, **kwargs)


def make_admin(db, **kwargs) -> User:
    kwargs.setdefault("role", UserRole.admin)
    kwargs.setdefault("email", "admin@example.com")
    kwargs.setdefault("full_name", "Test Admin")
    return make_user(db, **kwargs)
