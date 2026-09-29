import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = os.environ.get("CODEJUDGE_LOG_FILE", str(LOG_DIR / "codejudge.log"))
LOG_MAX_BYTES = int(os.environ.get("CODEJUDGE_LOG_MAX_BYTES", 5 * 1024 * 1024))
LOG_BACKUP_COUNT = int(os.environ.get("CODEJUDGE_LOG_BACKUP_COUNT", 5))
LOG_LEVEL = os.environ.get("CODEJUDGE_LOG_LEVEL", "INFO")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        extra = getattr(record, "event_data", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class SafeRotatingFileHandler(RotatingFileHandler):
    """Rotating file handler that tolerates rotation races between processes.

    The API (uvicorn) and the arq worker both write to the same log file. On
    Windows a rotation triggered by one process can fail while the other holds
    the file open, so rotation errors are swallowed instead of crashing a log
    call.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except OSError:
            pass


def _build_handlers() -> list[logging.Handler]:
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(JsonFormatter())

    handlers: list[logging.Handler] = [stream]

    file_path = Path(LOG_FILE)
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = SafeRotatingFileHandler(
            file_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(JsonFormatter())
        handlers.append(file_handler)
    except OSError:
        pass

    return handlers


def _configure() -> None:
    root = logging.getLogger("codejudge")
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    root.handlers[:] = _build_handlers()
    root.propagate = False


_configure()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"codejudge.{name}")
    logger.propagate = False
    logger.handlers[:] = list(logging.getLogger("codejudge").handlers)
    return logger


def log_event(logger: logging.Logger, level: int, event: str, **fields) -> None:
    logger.log(level, event, extra={"event_data": fields})
