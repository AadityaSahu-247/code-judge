import logging

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings
from app.logging_config import get_logger, log_event

logger = get_logger("jobs")

redis_settings = RedisSettings.from_dsn(settings.redis_url)


async def enqueue_job(name: str, *args, **kwargs):
    log_event(
        logger,
        logging.INFO,
        "job_enqueued",
        job=name,
        args=list(args) if args else None,
        kwargs=kwargs or None,
    )
    pool = await create_pool(redis_settings)
    try:
        result = await pool.enqueue_job(name, *args, **kwargs)
        log_event(
            logger,
            logging.INFO,
            "job_enqueued_ok",
            job=name,
            job_id=result.job_id if result else None,
        )
        return result
    finally:
        await pool.close()
