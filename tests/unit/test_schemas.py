"""Unit tests for the Pydantic request/response validators (app.schemas)."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    DoubtCreate,
    ReviewEditIn,
    ReviewRejectIn,
    SubmissionCreate,
    TestCaseCreate,
    UserCreate,
)


@pytest.mark.unit
def test_valid_user_create():
    u = UserCreate(email="student@example.com", password="supersecret", full_name="A")
    assert u.email == "student@example.com"


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "longenough", "full_name": "A"},
        {"email": "a@b.com", "password": "short", "full_name": "A"},
        {"email": "a@b.com", "password": "longenough", "full_name": ""},
    ],
)
def test_invalid_user_create_rejected(payload):
    with pytest.raises(ValidationError):
        UserCreate(**payload)


@pytest.mark.unit
def test_submission_create_bounds():
    SubmissionCreate(problem_id=1, language="python", source_code="x")
    with pytest.raises(ValidationError):
        SubmissionCreate(problem_id=1, language="", source_code="x")
    with pytest.raises(ValidationError):
        SubmissionCreate(problem_id=1, language="python", source_code="")
    with pytest.raises(ValidationError):
        SubmissionCreate(problem_id=1, language="python", source_code="a" * 200_001)


@pytest.mark.unit
def test_doubt_create_validation():
    DoubtCreate(title="valid", description="desc")
    with pytest.raises(ValidationError):
        DoubtCreate(title="ab", description="desc")
    with pytest.raises(ValidationError):
        DoubtCreate(title="valid", description="")
    with pytest.raises(ValidationError):
        DoubtCreate(title="valid", description="a" * 5001)
    with pytest.raises(ValidationError):
        DoubtCreate(title="valid", description="desc", code_snippet="a" * 20_001)


@pytest.mark.unit
def test_test_case_create_defaults():
    tc = TestCaseCreate(input="1", expected_output="1")
    assert tc.is_hidden is False
    assert tc.weight == 1.0


@pytest.mark.unit
def test_review_edit_requires_content():
    ReviewEditIn(edited_content="new text")
    with pytest.raises(ValidationError):
        ReviewEditIn(edited_content="")
    with pytest.raises(ValidationError):
        ReviewEditIn(edited_content="a" * 20_001)


@pytest.mark.unit
def test_review_reject_requires_note():
    with pytest.raises(ValidationError):
        ReviewRejectIn(note="")
    ReviewRejectIn(note="ok")
