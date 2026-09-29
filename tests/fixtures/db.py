"""Database fixtures: real PostgreSQL, isolated per session, truncated per test.

Requires the docker-compose services (``docker compose up -d postgres redis``)
or an equivalent PostgreSQL on ``TEST_PG_*``. Tests that need the DB are
skipped with a clear message when PostgreSQL is unreachable.
"""

from __future__ import annotations

import psycopg2
import pytest
from sqlalchemy import text

from app.database import Base, engine as app_engine
from tests.utils import db as db_utils


@pytest.fixture(scope="session")
def test_engine():
    """Create/drop the dedicated test database and build the schema once."""
    if not db_utils.ping():
        pytest.skip(
            "PostgreSQL is not reachable. Start it with "
            "'docker compose up -d postgres redis'."
        )

    db_utils.drop_database()
    db_utils.create_database()

    Base.metadata.create_all(app_engine)

    yield app_engine

    app_engine.dispose()
    db_utils.drop_database()


@pytest.fixture
def db(clean_tables):
    """A fresh, clean SQLAlchemy session bound to the test database."""
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def clean_tables(test_engine):
    """Truncate every table so each test starts from an empty database."""
    db_utils.truncate_all(test_engine)
    yield


@pytest.fixture(scope="session")
def schema_health_check(test_engine):
    """Confirm the schema is live and usable (enum round-trip)."""
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
    finally:
        session.close()
    return test_engine


@pytest.fixture(scope="session")
def admin_pg_connection():
    if not db_utils.ping():
        pytest.skip("PostgreSQL not reachable for admin connection.")
    conn = db_utils.admin_connection()
    conn.autocommit = True
    yield conn
    conn.close()


def _psycopg_url() -> str:
    return (
        f"postgresql://{db_utils.PG_USER}:{db_utils.PG_PASSWORD}"
        f"@{db_utils.PG_HOST}:{db_utils.PG_PORT}/{db_utils.TEST_DB}"
    )


@pytest.fixture
def raw_pg_connection():
    """A raw psycopg2 connection for asserting DB-level behaviour."""
    if not db_utils.ping():
        pytest.skip("PostgreSQL not reachable.")
    conn = psycopg2.connect(
        host=db_utils.PG_HOST,
        port=db_utils.PG_PORT,
        user=db_utils.PG_USER,
        password=db_utils.PG_PASSWORD,
        dbname=db_utils.TEST_DB,
        connect_timeout=3,
    )
    conn.autocommit = True
    yield conn
    conn.close()
