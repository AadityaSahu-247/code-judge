import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        default=UserRole.student,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), index=True, nullable=False
    )
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(default=False, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class SubmissionStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    graded = "graded"
    failed = "failed"


class Verdict(str, enum.Enum):
    accepted = "accepted"
    wrong_answer = "wrong_answer"
    time_limit_exceeded = "time_limit_exceeded"
    memory_limit_exceeded = "memory_limit_exceeded"
    runtime_error = "runtime_error"
    compile_error = "compile_error"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), index=True, nullable=False
    )
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(SubmissionStatus, name="submission_status"),
        default=SubmissionStatus.queued,
        nullable=False,
    )
    verdict: Mapped[Verdict | None] = mapped_column(
        SAEnum(Verdict, name="verdict"), nullable=True
    )
    score: Mapped[float | None] = mapped_column(Float)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    results: Mapped[list["SubmissionResult"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="SubmissionResult.test_case_id",
    )


class SubmissionResult(Base):
    __tablename__ = "submission_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    passed: Mapped[bool] = mapped_column(default=False, nullable=False)
    verdict: Mapped[Verdict] = mapped_column(
        SAEnum(Verdict, name="verdict"), nullable=False
    )
    actual_output: Mapped[str | None] = mapped_column(Text)
    exec_time_ms: Mapped[int | None] = mapped_column(Integer)
    memory_kb: Mapped[int | None] = mapped_column(Integer)

    submission: Mapped[Submission] = relationship(back_populates="results")


class FeedbackStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    status: Mapped[FeedbackStatus] = mapped_column(
        SAEnum(FeedbackStatus, name="feedback_status"),
        default=FeedbackStatus.pending,
        nullable=False,
    )
    readability: Mapped[str | None] = mapped_column(Text)
    complexity: Mapped[str | None] = mapped_column(Text)
    best_practices: Mapped[str | None] = mapped_column(Text)
    optimization: Mapped[str | None] = mapped_column(Text)
    raw_model_response: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(100))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    submission: Mapped[Submission] = relationship()


class DoubtStatus(str, enum.Enum):
    open = "open"
    answered = "answered"
    resolved = "resolved"


class AnswerStatus(str, enum.Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"


class ReviewAction(str, enum.Enum):
    approved = "approved"
    edited = "edited"
    rejected = "rejected"


class Doubt(Base):
    __tablename__ = "doubts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[str | None] = mapped_column(Text)
    related_problem_id: Mapped[int | None] = mapped_column(
        ForeignKey("problems.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[DoubtStatus] = mapped_column(
        SAEnum(DoubtStatus, name="doubt_status"),
        default=DoubtStatus.open,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    author: Mapped[User] = relationship(foreign_keys=[student_id])


class AIAnswer(Base):
    __tablename__ = "ai_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    doubt_id: Mapped[int] = mapped_column(
        ForeignKey("doubts.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    status: Mapped[AnswerStatus] = mapped_column(
        SAEnum(AnswerStatus, name="answer_status"),
        default=AnswerStatus.pending_review,
        nullable=False,
    )
    draft_content: Mapped[str | None] = mapped_column(Text)
    moderation_flagged: Mapped[bool] = mapped_column(default=False, nullable=False)
    moderation_reason: Mapped[str | None] = mapped_column(Text)
    raw_model_response: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(100))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    claimed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    doubt: Mapped[Doubt] = relationship()
    claimed_by: Mapped[User | None] = relationship(foreign_keys=[claimed_by_id])
    logs: Mapped[list["ReviewLog"]] = relationship(
        back_populates="answer",
        cascade="all, delete-orphan",
        order_by="ReviewLog.created_at",
    )


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(
        ForeignKey("ai_answers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=False
    )
    action: Mapped[ReviewAction] = mapped_column(
        SAEnum(ReviewAction, name="review_action"), nullable=False
    )
    edited_content: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    answer: Mapped[AIAnswer] = relationship(back_populates="logs")
    reviewer: Mapped[User] = relationship(foreign_keys=[reviewer_id])


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_doubt_id: Mapped[int | None] = mapped_column(
        ForeignKey("doubts.id", ondelete="SET NULL"), index=True
    )
    read: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
