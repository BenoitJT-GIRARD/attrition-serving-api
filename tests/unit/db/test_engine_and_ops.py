"""How the database URL is assembled, and what the decision log's operations do.

No PostgreSQL here: the connection string is built from the environment, and the operations
are exercised against SQLite, which is enough to check that the SQL parses, that the closed
set of table names holds, and that the history comes back newest first. The round trip
against a real PostgreSQL is the integration tier's job.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from attrition_serving.db.engine import connect_args_for, get_database_url
from attrition_serving.db.serving_ops import count_rows, fetch_history, truncate_predictions


@pytest.fixture(autouse=True)
def _no_inherited_environment(monkeypatch) -> None:
    for name in ("DATABASE_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


def test_the_url_is_taken_whole_when_one_is_given(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@example:5432/db")

    assert get_database_url() == "postgresql+psycopg://u:p@example:5432/db"


def test_the_url_is_rebuilt_from_the_parts_a_managed_database_hands_out(monkeypatch) -> None:
    monkeypatch.setenv("DB_HOST", "db.example")
    monkeypatch.setenv("DB_PORT", "6543")
    monkeypatch.setenv("DB_NAME", "serving")
    monkeypatch.setenv("DB_USER", "reader")
    monkeypatch.setenv("DB_PASSWORD", "secret")

    assert get_database_url() == "postgresql+psycopg://reader:secret@db.example:6543/serving"


def test_the_defaults_are_the_ones_the_compose_file_brings_up() -> None:
    assert get_database_url() == (
        "postgresql+psycopg://attrition:attrition_pwd@localhost:5432/attrition_serving"
    )


def test_a_managed_host_without_ssl_in_the_url_gets_it_added() -> None:
    """A DSN that forgets sslmode is refused by the host with a message that names nothing."""
    url = "postgresql+psycopg://u:p@db.ref.supabase.co:5432/postgres"

    assert connect_args_for(url) == {"sslmode": "require"}


def test_an_url_that_already_carries_ssl_is_left_alone() -> None:
    url = "postgresql+psycopg://u:p@db.ref.supabase.co:5432/postgres?sslmode=verify-full"

    assert connect_args_for(url) == {}


def test_a_local_database_gets_nothing_added() -> None:
    assert connect_args_for("postgresql+psycopg://a:b@localhost:5432/serving") == {}


@pytest.fixture()
def log(tmp_path):
    """A decision log with the two tables and three rows, in SQLite."""
    engine = create_engine(f"sqlite:///{tmp_path / 'log.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE employees (employee_id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "CREATE TABLE predictions (id INTEGER PRIMARY KEY, created_at TEXT, "
                "employee_id INTEGER, proba_depart REAL, prediction INTEGER, threshold REAL, "
                "model_version TEXT)"
            )
        )
        conn.execute(text("INSERT INTO employees (employee_id) VALUES (1), (2)"))
        for index, stamp in enumerate(("2026-01-01", "2026-03-01", "2026-02-01"), start=1):
            conn.execute(
                text("INSERT INTO predictions VALUES (:id, :at, 1, 0.5, 1, 0.11, 'v1')"),
                {"id": index, "at": stamp},
            )
    yield engine
    engine.dispose()


def test_the_counts_come_from_a_closed_set_of_table_names(log) -> None:
    assert count_rows(log, "employees") == 2
    assert count_rows(log, "predictions") == 3
    with pytest.raises(KeyError):
        count_rows(log, "pg_user")  # type: ignore[arg-type]


def test_the_history_comes_back_newest_first_and_carries_its_threshold(log) -> None:
    rows = fetch_history(log, limit=2)

    assert [row["created_at"] for row in rows] == ["2026-03-01", "2026-02-01"]
    assert rows[0]["threshold"] == 0.11
    assert rows[0]["model_version"] == "v1"


def test_only_the_decision_log_is_emptied(log) -> None:
    """Clearing the employees table would make the next run score nothing, silently."""
    with log.begin() as conn:
        conn.execute(text("DELETE FROM predictions"))

    assert count_rows(log, "predictions") == 0
    assert count_rows(log, "employees") == 2


def test_the_truncation_names_the_table_it_empties() -> None:
    """SQLite has no TRUNCATE; what is pinned here is which table the statement names."""
    import inspect

    source = inspect.getsource(truncate_predictions)

    assert "TRUNCATE TABLE predictions" in source
    assert "employees" in source  # the comment that says why it is not touched
