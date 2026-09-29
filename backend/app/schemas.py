from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    AnswerStatus,
    DoubtStatus,
    FeedbackStatus,
    ReviewAction,
    SubmissionStatus,
    UserRole,
    Verdict,
)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.student


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    difficulty: str | None


class ProblemDetailOut(ProblemOut):
    statement: str
    constraints: str | None


class TestCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: int
    input: str
    expected_output: str
    is_hidden: bool
    weight: float


class TestCaseCreate(BaseModel):
    input: str
    expected_output: str
    is_hidden: bool = False
    weight: float = 1.0


class SubmissionCreate(BaseModel):
    problem_id: int
    language: str = Field(min_length=1, max_length=20)
    source_code: str = Field(min_length=1, max_length=200_000)


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: int
    language: str
    status: SubmissionStatus
    verdict: Verdict | None
    score: float | None
    submitted_at: datetime


class SubmissionDetailOut(SubmissionOut):
    student_id: int
    source_code: str


class SubmissionResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_case_id: int
    passed: bool
    verdict: Verdict
    exec_time_ms: int | None
    memory_kb: int | None
    input: str | None = None
    expected_output: str | None = None
    actual_output: str | None = None


class AIFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    status: FeedbackStatus
    readability: str | None
    complexity: str | None
    best_practices: str | None
    optimization: str | None
    model_version: str | None
    generated_at: datetime | None


class DoubtCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=1, max_length=5000)
    code_snippet: str | None = Field(default=None, max_length=20_000)
    related_problem_id: int | None = None


class DoubtUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    code_snippet: str | None = Field(default=None, max_length=20_000)
    status: DoubtStatus | None = None


class DoubtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    student_name: str | None = None
    title: str
    status: DoubtStatus
    related_problem_id: int | None
    created_at: datetime


class DoubtDetailOut(DoubtOut):
    description: str
    code_snippet: str | None


class AIAnswerOut(BaseModel):
    id: int
    doubt_id: int
    status: AnswerStatus
    draft_content: str | None = None
    moderation_flagged: bool = False
    moderation_reason: str | None = None
    model_version: str | None = None
    generated_at: datetime | None = None


class ReviewAnswerOut(BaseModel):
    id: int
    doubt_id: int
    doubt_title: str
    student_name: str | None = None
    status: AnswerStatus
    draft_content: str | None = None
    moderation_flagged: bool = False
    moderation_reason: str | None = None
    model_version: str | None = None
    generated_at: datetime | None = None
    claimed_by_id: int | None = None
    claimed_by_name: str | None = None


class ReviewApproveIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ReviewEditIn(BaseModel):
    edited_content: str = Field(min_length=1, max_length=20_000)
    note: str | None = Field(default=None, max_length=2000)


class ReviewRejectIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class ReviewLogOut(BaseModel):
    id: int
    answer_id: int
    reviewer_name: str | None = None
    action: ReviewAction
    edited_content: str | None = None
    note: str | None = None
    created_at: datetime


class NotificationOut(BaseModel):
    id: int
    type: str
    message: str
    related_doubt_id: int | None = None
    read: bool
    created_at: datetime


class DoubtSimilarOut(DoubtOut):
    similarity: float


class PlagiarismPairOut(BaseModel):
    submission_a_id: int
    submission_b_id: int
    student_a_name: str | None = None
    student_b_name: str | None = None
    verdict_a: Verdict | None = None
    verdict_b: Verdict | None = None
    score_a: float | None = None
    score_b: float | None = None
    similarity: float


class PlagiarismReportOut(BaseModel):
    problem_id: int
    problem_title: str
    threshold: float
    pairs: list[PlagiarismPairOut]


class ReviewRegenerateIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ReviewerStat(BaseModel):
    name: str
    count: int


class AnalyticsOut(BaseModel):
    pending_reviews: int
    generated_answers: int
    approved_answers: int
    rejected_answers: int
    total_reviewed: int
    approval_rate: float
    reviews_by_action: dict[str, int]
    top_reviewers: list[ReviewerStat]
