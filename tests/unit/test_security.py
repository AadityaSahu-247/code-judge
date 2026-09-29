"""Unit tests for password hashing and JWT handling (app.security)."""

from datetime import timedelta

import jwt
import pytest

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.mark.unit
def test_hash_and_verify_roundtrip():
    digest = hash_password("correct horse battery staple")
    assert digest != "correct horse battery staple"
    assert digest.startswith("$2")
    assert verify_password("correct horse battery staple", digest)


@pytest.mark.unit
def test_wrong_password_is_rejected():
    digest = hash_password("right")
    assert not verify_password("wrong", digest)


@pytest.mark.unit
def test_same_password_hashes_differently():
    assert hash_password("pw") != hash_password("pw")


@pytest.mark.unit
def test_create_and_decode_token():
    token = create_access_token(subject="42", role="student")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "student"
    assert "exp" in payload


@pytest.mark.unit
def test_token_expires():
    token = create_access_token(
        subject="1", role="student", expires_delta=timedelta(seconds=-5)
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


@pytest.mark.unit
def test_tampered_token_is_rejected():
    token = create_access_token(subject="1", role="student")
    tampered = token[:-4] + ("abcd" if token[-4:] != "abcd" else "wxyz")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered)


@pytest.mark.unit
def test_wrong_secret_is_rejected(monkeypatch):
    from app import security

    token = create_access_token(subject="1", role="student")
    monkeypatch.setattr(security.settings, "jwt_secret", "another-secret")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token)


@pytest.mark.unit
def test_token_carries_role_claim():
    token = create_access_token(subject="7", role="teacher")
    assert decode_access_token(token)["role"] == "teacher"
