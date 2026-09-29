import time
from typing import Annotated

import redis
from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.deps import CurrentUser

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def _consume(key: str, limit: int, window_seconds: int) -> bool:
    client = _get_client()
    bucket = int(time.time()) // window_seconds
    redis_key = f"rl:{key}:{bucket}"
    count = client.incr(redis_key)
    if count == 1:
        client.expire(redis_key, window_seconds)
    return count <= limit


def rate_limit(limit: int, window_seconds: int, key_prefix: str):
    def _dependency(user: CurrentUser) -> None:
        if not _consume(f"{key_prefix}:{user.id}", limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded, please slow down",
            )

    return _dependency


def rate_limit_ip(limit: int, window_seconds: int, key_prefix: str):
    def _dependency(request: Request) -> None:
        host = request.client.host if request.client else "unknown"
        if not _consume(f"{key_prefix}:ip:{host}", limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded, please slow down",
            )

    return _dependency
