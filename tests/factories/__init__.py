"""Factories build persisted domain objects for tests.

Each factory takes the current SQLAlchemy ``db`` session (the ``db`` fixture)
and commits. Factories never call production services or the network.
"""
