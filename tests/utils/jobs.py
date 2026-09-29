"""Replay captured jobs through the real ARQ worker functions.

Used by integration/e2e tests to deterministically execute the background
pipeline (grading -> AI feedback, doubt -> AI answer) without a real queue.
"""

from __future__ import annotations

import asyncio

from tests.mocks.arq import fake_arq_context


def run_job(name: str, *args, redis=None, **kwargs) -> None:
    """Run a single ARQ worker function synchronously to completion.

    Uses an explicit event loop via ``asyncio.run`` so it works from plain
    synchronous tests.
    """
    from app.jobs import worker as worker_module

    func = getattr(worker_module, name)
    ctx = fake_arq_context(redis)
    return asyncio.run(func(ctx, *args, **kwargs))


def run_jobs(jobs, redis=None) -> list:
    """Run ``[(name, args, kwargs), ...]`` sequentially."""
    from app.jobs import worker as worker_module

    ctx = fake_arq_context(redis)

    async def _runner():
        results = []
        for name, args, kwargs in jobs:
            func = getattr(worker_module, name)
            results.append(await func(ctx, *args, **kwargs))
        return results

    return asyncio.run(_runner())
