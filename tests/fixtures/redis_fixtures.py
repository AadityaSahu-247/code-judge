"""Redis fixtures: an isolated logical database, flushed per test."""

from __future__ import annotations

import redis
import pytest

from app.config import settings


@pytest.fixture(scope="session")
def test_redis():
    """Client for the isolated test Redis logical database."""
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
    except Exception as exc:  # pragma: no cover - env dependent
        pytest.skip(f"Redis is not reachable: {exc}")

    client.flushdb()
    yield client
    client.flushdb()
    client.close()


@pytest.fixture(scope="session")
def redis_settings_dsn():
    return settings.redis_url


@pytest.fixture
def clean_redis(test_redis):
    test_redis.flushdb()
    yield
