"""Unit tests for structured logging (app.logging_config)."""

import json
import logging

import pytest

from app.logging_config import JsonFormatter, get_logger, log_event


@pytest.mark.unit
def test_json_formatter_produces_valid_json():
    record = logging.LogRecord(
        name="codejudge.test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello", args=(), exc_info=None,
    )
    record.event_data = {"user_id": 3}
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "hello"
    assert payload["level"] == "info"
    assert payload["logger"] == "codejudge.test"
    assert payload["user_id"] == 3
    assert "ts" in payload


@pytest.mark.unit
def test_log_event_records_extra_fields(caplog):
    logger = get_logger("unit_test")
    with caplog.at_level(logging.INFO, logger="codejudge.unit_test"):
        log_event(logger, logging.INFO, "event_x", a=1, b="two")
    assert any("event_x" in rec.getMessage() for rec in caplog.records)


@pytest.mark.unit
def test_get_logger_has_handlers():
    logger = get_logger("unit_handlers")
    assert len(logger.handlers) >= 1


@pytest.mark.unit
def test_formatter_handles_exceptions():
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = __import__("sys").exc_info()
        record = logging.LogRecord(
            name="codejudge.t", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="failed", args=(), exc_info=exc_info,
        )
        payload = json.loads(JsonFormatter().format(record))
        assert "ValueError" in payload["exc"]


@pytest.mark.unit
def test_safe_rotating_handler_swallows_oserror(monkeypatch):
    from app.logging_config import SafeRotatingFileHandler

    handler = SafeRotatingFileHandler(
        "codejudge-test.log", maxBytes=1024, backupCount=1, encoding="utf-8"
    )

    def broken_emit(self, record):
        raise OSError("file busy")

    monkeypatch.setattr("logging.handlers.RotatingFileHandler.emit", broken_emit)
    record = logging.LogRecord(
        name="codejudge.t", level=logging.WARNING, pathname=__file__, lineno=1,
        msg="warn", args=(), exc_info=None,
    )
    handler.emit(record)  # must not raise
    handler.close()
    import os

    if os.path.exists("codejudge-test.log"):
        os.remove("codejudge-test.log")


@pytest.mark.unit
def test_build_handlers_falls_back_without_file(monkeypatch):
    from app.logging_config import _build_handlers

    def broken_path(*args, **kwargs):
        raise OSError("no write access")

    monkeypatch.setattr("pathlib.Path.mkdir", broken_path)
    handlers = _build_handlers()
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)
