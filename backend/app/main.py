import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import LOG_FILE, get_logger, log_event
from app.routers import (
    analytics,
    auth,
    doubts,
    health,
    notifications,
    problems,
    reviews,
    submissions,
)

logger = get_logger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log_event(logger, logging.INFO, "app_started", app=settings.app_name, log_file=LOG_FILE)
    yield
    log_event(logger, logging.INFO, "app_stopped", app=settings.app_name)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    log_event(
        logger,
        logging.INFO,
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=elapsed_ms,
    )
    return response

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(submissions.router)
app.include_router(doubts.router)
app.include_router(reviews.router)
app.include_router(notifications.router)
app.include_router(analytics.router)
app.include_router(health.router)


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs"}
