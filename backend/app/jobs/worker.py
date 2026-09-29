import asyncio
import logging

from arq.connections import RedisSettings

from app.config import settings
from app.logging_config import get_logger, log_event
from app.services.ai_answer import generate_ai_answer_sync
from app.services.ai_feedback import generate_ai_feedback_sync
from app.services.grading import grade_submission_sync

logger = get_logger("worker")


async def grade_submission(ctx: dict, submission_id: int) -> str:
    loop = asyncio.get_running_loop()
    log_event(logger, logging.INFO, "job_started", job="grade_submission", submission_id=submission_id)
    try:
        await loop.run_in_executor(None, grade_submission_sync, submission_id)
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "job_failed",
            job="grade_submission",
            submission_id=submission_id,
            error=type(exc).__name__,
            detail=str(exc)[:500],
        )
        raise
    await ctx["redis"].enqueue_job("generate_feedback", submission_id)
    log_event(logger, logging.INFO, "job_completed", job="grade_submission", submission_id=submission_id)
    return f"graded submission {submission_id}"


async def generate_feedback(ctx: dict, submission_id: int) -> str:
    loop = asyncio.get_running_loop()
    log_event(logger, logging.INFO, "job_started", job="generate_feedback", submission_id=submission_id)
    await loop.run_in_executor(None, generate_ai_feedback_sync, submission_id)
    log_event(logger, logging.INFO, "job_completed", job="generate_feedback", submission_id=submission_id)
    return f"generated AI feedback for submission {submission_id}"


async def generate_answer(ctx: dict, doubt_id: int, teacher_note: str | None = None) -> str:
    loop = asyncio.get_running_loop()
    log_event(
        logger,
        logging.INFO,
        "job_started",
        job="generate_answer",
        doubt_id=doubt_id,
        teacher_note=teacher_note or None,
    )
    await loop.run_in_executor(None, generate_ai_answer_sync, doubt_id, teacher_note)
    log_event(logger, logging.INFO, "job_completed", job="generate_answer", doubt_id=doubt_id)
    return f"generated AI answer for doubt {doubt_id}"


class WorkerSettings:
    functions = [grade_submission, generate_feedback, generate_answer]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    use_uvloop = False
    job_timeout = 300
    max_tries = 1
