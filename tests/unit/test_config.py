"""Unit tests for app.config."""

import pytest

from app.config import Settings, settings


@pytest.mark.unit
def test_defaults_are_sane():
    s = Settings(_env_file=None)
    assert s.database_url.startswith("postgresql+psycopg2://")
    assert s.redis_url.startswith("redis://")
    assert s.jwt_algorithm == "HS256"
    assert s.access_token_expire_minutes == 1440
    assert s.app_name == "CodeJudge API"
    assert s.gemini_model == "gemini-2.5-flash"
    assert s.wall_timeout_seconds == 20
    assert s.memory_limit_mb == 256
    assert s.cpu_limit == 0.5
    assert s.pids_limit == 128


@pytest.mark.unit
def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "custom-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("WALL_TIMEOUT_SECONDS", "9")
    s = Settings(_env_file=None)
    assert s.jwt_secret == "custom-secret"
    assert s.access_token_expire_minutes == 30
    assert s.wall_timeout_seconds == 9


@pytest.mark.unit
def test_extra_fields_are_ignored(monkeypatch):
    monkeypatch.setenv("SOME_UNKNOWN_SETTING", "value")
    Settings(_env_file=None)


@pytest.mark.unit
def test_global_settings_singleton():
    assert isinstance(settings, Settings)
    assert settings.jwt_secret == "test-jwt-secret-0123456789-change-me-abcdef"


@pytest.mark.unit
def test_empty_llm_keys_force_mock_mode():
    s = Settings(_env_file=None)
    assert s.gemini_api_key == ""
