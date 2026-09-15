"""Fixtures for the tests that need a real PostgreSQL.

They skip when there is none, and they skip *quickly*. Without a connect timeout the driver
waits on the operating system's default, and the suite took four and a half minutes to
report two errors on a machine with no database running. A suite that hangs is a suite
people stop running, and then it stops catching anything.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest
import sqlalchemy
from fastapi.testclient import TestClient

from attrition_serving.api.settings import reset_config_cache
from attrition_serving.db.serving_ops import apply_schema, truncate_predictions

#: The local docker-compose database. Override with DATABASE_URL to point elsewhere.
DEFAULT_URL = "postgresql+psycopg://attrition:attrition_pwd@localhost:5432/attrition_serving"

#: Seconds to wait for a connection before deciding there is nothing there.
CONNECT_TIMEOUT = 3


@pytest.fixture(scope="session")
def engine():
    """A connected engine, or a skip that says how to get one."""
    url = os.getenv("TEST_DATABASE_URL", DEFAULT_URL)
    candidate = sqlalchemy.create_engine(
        url, connect_args={"connect_timeout": CONNECT_TIMEOUT}, pool_pre_ping=True
    )
    try:
        with candidate.connect() as connection:
            connection.execute(sqlalchemy.text("SELECT 1"))
    except sqlalchemy.exc.OperationalError as exc:
        pytest.skip(
            f"no PostgreSQL at {url.rsplit('@', 1)[-1]} ({type(exc).__name__}). "
            "Start it with `docker compose up -d`, or set TEST_DATABASE_URL."
        )
    apply_schema(candidate)
    yield candidate
    # The pool holds its connections open until the engine is disposed. Left undisposed it
    # surfaces as a `ResourceWarning` during interpreter shutdown -- late enough that
    # nothing fails and nobody looks.
    candidate.dispose()


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch):
    """A configuration that does not depend on whatever .env happens to be on disk."""
    monkeypatch.setenv("SKIP_DOTENV", "1")
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("MODEL_VERSION", "test")
    # An explicit threshold: these tests exercise the round trip, not the operating point,
    # and tests/unit/test_served_threshold_matches_artifact.py is what pins the default.
    monkeypatch.setenv("MODEL_THRESHOLD", "0.5")
    monkeypatch.setenv("DATABASE_URL", os.getenv("TEST_DATABASE_URL", DEFAULT_URL))
    reset_config_cache()


@pytest.fixture(autouse=True)
def clean_predictions(engine):
    truncate_predictions(engine)
    yield


@pytest.fixture
def client():
    from attrition_serving.api import deps, main

    deps.dispose_engine()
    importlib.reload(main)
    with TestClient(main.app) as test_client:
        yield test_client
    deps.dispose_engine()


TIER = "integration"

#: This directory. `pytest_collection_modifyitems` is handed EVERY collected item, not only
#: the ones below the conftest that defines it, so the hook filters by path: without this the
#: system tier reports the integration tier's files as unmarked. The marker is read with
#: `get_closest_marker`, never from `item.keywords` — the keywords carry the names of the
#: parent nodes, so the directory called `integration` makes every file in it look marked.
HERE = Path(__file__).resolve().parent


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    unmarked = sorted(
        {
            str(item.path.relative_to(HERE))
            for item in items
            if getattr(item, "path", None) is not None
            and HERE in item.path.parents
            and item.get_closest_marker(TIER) is None
        }
    )
    if unmarked:
        raise pytest.UsageError(
            f"{len(unmarked)} file(s) under tests/{TIER}/ without "
            f"`pytestmark = pytest.mark.{TIER}`: " + ", ".join(unmarked)
        )
