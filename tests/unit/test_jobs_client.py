"""Unit tests for the ARQ enqueue client and DB session generator.

Neither test touches real Redis or a real worker; ``create_pool`` is faked
and ``get_db`` is driven directly against the test engine.
"""

import pytest
from sqlalchemy import text


class FakePoolResult:
    def __init__(self, job_id="job-1"):
        self.job_id = job_id


class FakePool:
    def __init__(self, result=None):
        self.result = result
        self.enqueued = []
        self.closed = False

    async def enqueue_job(self, name, *args, **kwargs):
        self.enqueued.append((name, args, kwargs))
        return self.result

    async def close(self):
        self.closed = True


@pytest.mark.unit
@pytest.mark.real_arq
def test_enqueue_job_returns_result_and_closes_pool(monkeypatch):
    import asyncio

    from app.jobs import client

    pool = FakePool(result=FakePoolResult("abc"))

    async def fake_create_pool(_settings):
        return pool

    monkeypatch.setattr(client, "create_pool", fake_create_pool)

    result = asyncio.run(client.enqueue_job("grade_submission", 42, flag=True))
    assert result.job_id == "abc"
    assert pool.enqueued == [("grade_submission", (42,), {"flag": True})]
    assert pool.closed


@pytest.mark.unit
@pytest.mark.real_arq
def test_enqueue_job_closes_pool_even_on_failure(monkeypatch):
    import asyncio

    from app.jobs import client

    class BoomPool(FakePool):
        async def enqueue_job(self, name, *args, **kwargs):
            raise RuntimeError("redis down")

    pool = BoomPool()

    async def fake_create_pool(_settings):
        return pool

    monkeypatch.setattr(client, "create_pool", fake_create_pool)

    with pytest.raises(RuntimeError, match="redis down"):
        asyncio.run(client.enqueue_job("generate_answer", 7))
    assert pool.closed


@pytest.mark.unit
def test_get_db_yields_session_and_closes_afterward(test_engine):
    from app.database import get_db

    gen = get_db()
    session = next(gen)
    assert session is not None
    assert session.execute(text("SELECT 1")).scalar_one() == 1
    with pytest.raises(StopIteration):
        next(gen)


@pytest.mark.unit
def test_get_db_closes_session_when_yield_raises(test_engine):
    from app.database import get_db

    gen = get_db()
    next(gen)
    with pytest.raises(ValueError, match="boom"):
        gen.throw(ValueError("boom"))
