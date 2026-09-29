"""PostgreSQL test-database administration.

The test database (``codejudge_test`` by default) is created once per session from
an admin connection and dropped again at session teardown, so no test ever
touches a real database.
"""

from __future__ import annotations

import os

import psycopg2
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

TEST_DB = os.environ.get("TEST_DATABASE_NAME", "codejudge_test")
PG_HOST = os.environ.get("TEST_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("TEST_PG_PORT", "5433"))
PG_USER = os.environ.get("TEST_PG_USER", "codejudge")
PG_PASSWORD = os.environ.get("TEST_PG_PASSWORD", "codejudge")


def admin_connection():
    """Connect to the maintenance ``postgres`` database."""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname="postgres",
        connect_timeout=3,
    )


def ping() -> bool:
    """Return True when PostgreSQL is reachable."""
    try:
        conn = admin_connection()
        conn.close()
        return True
    except Exception:
        return False


def drop_database() -> None:
    conn = admin_connection()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
    conn.close()


def create_database() -> None:
    conn = admin_connection()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{TEST_DB}"')
    conn.close()


def truncate_all(engine: Engine) -> None:
    """Delete every row from every table, preserving the schema."""
    with engine.begin() as conn:
        table_names = inspect(conn).get_table_names()
        if not table_names:
            return
        ordered = ", ".join(f'"{name}"' for name in table_names)
        conn.execute(text(f"TRUNCATE {ordered} CASCADE"))
