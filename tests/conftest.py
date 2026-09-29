"""Root test configuration.

Sets a hermetic environment *before* any ``app`` module is imported, injects
the fake ``litellm`` so no external provider is ever called, and wires up the
shared fixtures declared in ``tests/fixtures/``.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Environment must be configured before anything under ``app`` is imported.
# ---------------------------------------------------------------------------
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://codejudge:codejudge@127.0.0.1:5433/codejudge_test",
)
os.environ["REDIS_URL"] = os.environ.get(
    "TEST_REDIS_URL",
    "redis://127.0.0.1:6379/15",
)
os.environ["JWT_SECRET"] = "test-jwt-secret-0123456789-change-me-abcdef"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["CODEJUDGE_LOG_FILE"] = str(Path(tempfile.gettempdir()) / "codejudge-test.log")
os.environ["CODEJUDGE_LOG_MAX_BYTES"] = "1048576"
os.environ["CODEJUDGE_LOG_BACKUP_COUNT"] = "0"

# Force the LLM providers into the built-in deterministic mock mode: no real
# Gemini/Groq/OpenRouter key is visible, so the gateway reports 0 endpoints
# and the AI services fall back to their fixed fake responses.
for _prefix in ("GEMINI_API_KEY", "GROQ_API_KEY"):
    for _index in range(5):
        os.environ[f"{_prefix}{_index if _index else ''}"] = ""
os.environ["GROQ_MODEL"] = "llama-3.3-70b-versatile"

from tests.mocks.litellm_fake import install_fake_litellm  # noqa: E402

install_fake_litellm()

# ---------------------------------------------------------------------------
# Register the fixture modules.
# ---------------------------------------------------------------------------
pytest_plugins = [
    "tests.fixtures.db",
    "tests.fixtures.redis_fixtures",
    "tests.fixtures.auth",
    "tests.fixtures.domain",
    "tests.fixtures.app",
]

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_rate_limit(request, monkeypatch):
    """Disable the Redis rate limiter unless a test opts into it."""
    if request.node.get_closest_marker("real_ratelimit"):
        yield
        return
    import app.ratelimit as ratelimit

    monkeypatch.setattr(ratelimit, "_consume", lambda key, limit, window: True)
    yield


@pytest.fixture
def client(clean_tables, clean_redis):
    """FastAPI ``TestClient`` with the app's DB dependency pointed at the
    test database and server exceptions converted into 500 responses."""
    from fastapi.testclient import TestClient

    from app.database import SessionLocal, get_db
    from app.main import app

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def asgi_app():
    """The bare ASGI app for in-process async/concurrent HTTP tests."""
    from app.main import app

    return app
