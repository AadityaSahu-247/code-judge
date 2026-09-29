from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.config import settings
from app.deps import DbDep

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(db: DbDep) -> dict:
    checks: dict[str, str] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - connectivity check
        checks["database"] = f"error: {exc.__class__.__name__}"

    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # pragma: no cover - connectivity check
        checks["redis"] = f"error: {exc.__class__.__name__}"

    healthy = all(value == "ok" for value in checks.values())
    if not healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=checks,
        )
    return {"status": "ok", **checks}
