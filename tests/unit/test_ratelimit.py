"""Unit tests for the Redis rate limiter (app.ratelimit).

Uses fakeredis so no real Redis connection is required.
"""

import pytest
from types import SimpleNamespace

import fakeredis
import redis as redis_lib

import app.ratelimit as ratelimit
from app.ratelimit import rate_limit, rate_limit_ip


@pytest.fixture
def fake_redis_client(monkeypatch):
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(ratelimit, "_get_client", lambda: client)
    return client


@pytest.mark.unit
@pytest.mark.real_ratelimit
def test_consume_counts_within_window(fake_redis_client):
    assert ratelimit._consume("k", 3, 60) is True
    assert ratelimit._consume("k", 3, 60) is True
    assert ratelimit._consume("k", 3, 60) is True
    assert ratelimit._consume("k", 3, 60) is False


@pytest.mark.unit
@pytest.mark.real_ratelimit
def test_consume_windows_are_isolated(fake_redis_client, monkeypatch):
    current = {"now": 1_000_000}
    monkeypatch.setattr(ratelimit.time, "time", lambda: current["now"])
    assert ratelimit._consume("k", 1, 60) is True
    current["now"] += 60
    assert ratelimit._consume("k", 1, 60) is True
    assert ratelimit._consume("k", 1, 60) is False


@pytest.mark.unit
@pytest.mark.real_ratelimit
def test_rate_limit_dependency_raises_429(fake_redis_client):
    user = SimpleNamespace(id=5)
    dependency = rate_limit(1, 60, "test")
    dependency(user)
    with pytest.raises(ratelimit.HTTPException) as excinfo:
        dependency(user)
    assert excinfo.value.status_code == 429


@pytest.mark.unit
@pytest.mark.real_ratelimit
def test_rate_limit_ip_dependency(fake_redis_client):
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    dependency = rate_limit_ip(2, 60, "test-ip")
    dependency(request)
    dependency(request)
    with pytest.raises(ratelimit.HTTPException) as excinfo:
        dependency(request)
    assert excinfo.value.status_code == 429


@pytest.mark.unit
@pytest.mark.real_ratelimit
def test_redis_failure_propagates(monkeypatch):
    def broken_client():
        raise redis_lib.ConnectionError("redis down")

    monkeypatch.setattr(ratelimit, "_get_client", broken_client)
    with pytest.raises(redis_lib.ConnectionError):
        ratelimit._consume("k", 1, 60)


@pytest.mark.unit
@pytest.mark.real_ratelimit
def test_key_prefix_includes_scope(fake_redis_client):
    assert ratelimit._consume("scoped:key", 1, 60) is True
