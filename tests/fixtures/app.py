"""Application fixtures: TestClient, job recorder, LLM gateway and docker mocks.

``mock_enqueue`` and ``mock_docker`` are autouse so every test is isolated
from the real queue and the real docker sandbox by default. Opt out with the
``real_arq`` / ``real_docker`` markers when a test intentionally exercises the
real infrastructure.
"""

from __future__ import annotations

import pytest

from app.services.llm_gateway import CompletionResult, TokenUsage
from tests.mocks.arq import JobRecorder


@pytest.fixture
def job_recorder():
    """Captures every ``enqueue_job`` call made by the API during a test."""
    recorder = JobRecorder()
    yield recorder
    recorder.reset()


@pytest.fixture(autouse=True)
def mock_enqueue(request, monkeypatch, job_recorder):
    """Replace ``enqueue_job`` in every router that uses it (unless real_arq)."""
    if request.node.get_closest_marker("real_arq"):
        yield job_recorder
        return

    import app.jobs.client as jobs_client
    import app.routers.doubts
    import app.routers.reviews
    import app.routers.submissions

    async def fake_enqueue(name, *args, **kwargs):
        return await job_recorder.enqueue(name, *args, **kwargs)

    monkeypatch.setattr(app.routers.submissions, "enqueue_job", fake_enqueue)
    monkeypatch.setattr(app.routers.doubts, "enqueue_job", fake_enqueue)
    monkeypatch.setattr(app.routers.reviews, "enqueue_job", fake_enqueue)
    monkeypatch.setattr(jobs_client, "enqueue_job", fake_enqueue)
    yield job_recorder


@pytest.fixture(autouse=True)
def mock_docker(request, monkeypatch):
    """Deterministic grader: every test case passes (unless real_docker)."""
    if request.node.get_closest_marker("real_docker"):
        yield
        return

    from app.models import Verdict
    from app.services import grading
    from app.services.grading import CaseResult

    def fake_run_test_case(language, source_code, test_case, container_name):
        return CaseResult(
            test_case_id=test_case.id,
            passed=True,
            verdict=Verdict.accepted,
            actual_output=test_case.expected_output,
            exec_time_ms=1,
        )

    monkeypatch.setattr(grading, "_run_test_case", fake_run_test_case)
    yield fake_run_test_case


@pytest.fixture
def mock_gateway(monkeypatch):
    """Deterministic fake for the LLM gateway (never touches the network).

    ``state["available"]`` decides whether the services use the provider path;
    queued ``results``/``errors`` are consumed in order by ``complete``.
    """
    from app.services.llm_gateway import LLMGatewayError, gateway

    state = {
        "available": 1,
        "results": [],
        "errors": [],
        "calls": [],
    }

    def fake_available():
        return state["available"]

    def fake_complete(messages, **kwargs):
        state["calls"].append((messages, kwargs))
        if state["errors"]:
            raise state["errors"].pop(0)
        if state["results"]:
            return state["results"].pop(0)
        raise LLMGatewayError("no mock result queued")

    monkeypatch.setattr(gateway, "available", fake_available)
    monkeypatch.setattr(gateway, "complete", fake_complete)
    return state


def make_completion_result(content: str, model: str = "mock/gemini#0") -> CompletionResult:
    return CompletionResult(
        content=content,
        provider="gemini",
        model="gemini-2.5-flash",
        key_index=0,
        model_version=model,
        endpoint_id="gemini:test",
        latency_ms=12.5,
        tokens=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        request_id="test-request",
    )
