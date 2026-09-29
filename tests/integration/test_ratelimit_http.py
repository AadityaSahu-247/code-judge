"""Integration tests for the real Redis-backed rate limiter over HTTP."""

import pytest


@pytest.mark.integration
@pytest.mark.real_ratelimit
def test_signup_rate_limited_after_limit(client, clean_redis):
    for i in range(5):
        resp = client.post(
            "/api/auth/signup",
            json={
                "email": f"rl.{i}@example.com",
                "password": "strongpass123",
                "full_name": f"Rate {i}",
            },
        )
        assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/auth/signup",
        json={
            "email": "rl.over@example.com",
            "password": "strongpass123",
            "full_name": "Rate Over",
        },
    )
    assert resp.status_code == 429
    assert "Rate limit" in resp.json()["detail"]
