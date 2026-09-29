"""Integration tests for the health router (real DB + Redis connectivity)."""

import pytest


@pytest.mark.integration
def test_health_ok(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["redis"] == "ok"


@pytest.mark.integration
def test_root_endpoint(client):
    data = client.get("/").json()
    assert data["app"] == "CodeJudge API"
    assert "/docs" in data["docs"]


@pytest.mark.integration
def test_health_returns_503_when_redis_down(client, monkeypatch):
    import redis as redis_module

    class DeadRedis:
        def ping(self):
            raise redis_module.exceptions.ConnectionError("no route to host")

    def dead_client(*args, **kwargs):
        return DeadRedis()

    monkeypatch.setattr(redis_module.Redis, "from_url", staticmethod(dead_client))
    resp = client.get("/api/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["detail"]["database"] == "ok"
    assert body["detail"]["redis"].startswith("error:")
