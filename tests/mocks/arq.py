"""Fakes for the ARQ job queue.

``JobRecorder`` stands in for ``app.jobs.client.enqueue_job`` in every
integration/e2e test so no real Redis queue is required and no background
worker races tests. Recorded jobs can be replayed against the real worker
functions in a controlled, deterministic order.
"""

from types import SimpleNamespace


class FakeJob:
    """Minimal stand-in for the object returned by ``pool.enqueue_job``."""

    def __init__(self, job_id: str = "test-job"):
        self.job_id = job_id


class JobRecorder:
    """Captures ``enqueue_job(name, *args, **kwargs)`` calls in order."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def reset(self) -> None:
        self.calls.clear()

    @property
    def names(self) -> list[str]:
        return [name for name, _, _ in self.calls]

    def last(self) -> tuple[str, tuple, dict] | None:
        return self.calls[-1] if self.calls else None

    def for_name(self, name: str) -> list[tuple[str, tuple, dict]]:
        return [call for call in self.calls if call[0] == name]

    async def enqueue(self, name: str, *args, **kwargs):
        """Async stand-in used to patch router-level ``enqueue_job``."""
        self.calls.append((name, args, kwargs))
        return FakeJob(job_id=f"test-{len(self.calls)}")


def fake_arq_context(redis) -> dict:
    """Build an ARQ worker context dict for calling worker functions."""
    return {"redis": redis}


class FakeQueueRedis:
    """Records ``enqueue_job`` calls made from inside worker functions."""

    def __init__(self) -> None:
        self.enqueued: list[tuple[str, tuple, dict]] = []

    async def enqueue_job(self, name, *args, **kwargs):
        self.enqueued.append((name, args, kwargs))
        return FakeJob()
