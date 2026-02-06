"""Scheduler test fixtures — only loaded when tests/scheduler/ is collected."""
import pytest

from tests.database.fixtures import (
    create_test_database,
    db_engine,
    db_session,
    TEST_DATABASE_NAME,
    TEST_DATABASE_URL,
)

# Re-export so pytest discovers them as fixtures in this conftest
__all__ = [
    "create_test_database",
    "db_engine",
    "db_session",
    "TEST_DATABASE_NAME",
    "TEST_DATABASE_URL",
]
