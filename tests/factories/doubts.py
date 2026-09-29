"""Doubt / AI-answer / review-log factories."""

from app.models import AIAnswer, AnswerStatus, Doubt, DoubtStatus, ReviewAction, ReviewLog


def make_doubt(
    db,
    *,
    student_id: int,
    title: str = "Why does my loop never end?",
    description: str = "The while condition never becomes false.",
    code_snippet: str | None = "while True: pass",
    related_problem_id: int | None = None,
    status: DoubtStatus = DoubtStatus.open,
) -> Doubt:
    doubt = Doubt(
        student_id=student_id,
        title=title,
        description=description,
        code_snippet=code_snippet,
        related_problem_id=related_problem_id,
        status=status,
    )
    db.add(doubt)
    db.commit()
    db.refresh(doubt)
    return doubt


def make_ai_answer(
    db,
    *,
    doubt_id: int,
    status: AnswerStatus = AnswerStatus.pending_review,
    draft_content: str | None = "Your loop never ends because the exit condition is unreachable.",
    moderation_flagged: bool = False,
    moderation_reason: str | None = None,
    model_version: str = "mock-gemini-2.5-flash",
    claimed_by_id: int | None = None,
    reviewed_by_id: int | None = None,
) -> AIAnswer:
    answer = AIAnswer(
        doubt_id=doubt_id,
        status=status,
        draft_content=draft_content,
        moderation_flagged=moderation_flagged,
        moderation_reason=moderation_reason,
        model_version=model_version,
        claimed_by_id=claimed_by_id,
        reviewed_by_id=reviewed_by_id,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


def make_review_log(
    db,
    *,
    answer_id: int,
    reviewer_id: int,
    action: ReviewAction = ReviewAction.approved,
    edited_content: str | None = None,
    note: str | None = None,
) -> ReviewLog:
    log = ReviewLog(
        answer_id=answer_id,
        reviewer_id=reviewer_id,
        action=action,
        edited_content=edited_content,
        note=note,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
