"""The decision log is best-effort, and the answer says which it was.

`routers/predict.py` promised this in its docstring and did not deliver it: the insert was
unguarded, so an unreachable database produced a 500 on every prediction. The system tier found
that by starting the service without one; these tests hold the behaviour in place.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from attrition_serving.api.routers.predict import _log_decision

ROW = {
    "employee_id": 1,
    "input_payload": '{"age": 41}',
    "proba": 0.52,
    "pred": 1,
    "thr": 0.1105,
    "ver": "v1",
}


@pytest.fixture()
def session(tmp_path):
    """A session against a log that exists. SQLite is enough to check the statement runs."""
    engine = create_engine(f"sqlite:///{tmp_path / 'log.db'}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "employee_id INTEGER, input_payload TEXT, proba_depart REAL, "
                "prediction INTEGER, threshold REAL, model_version TEXT)"
            )
        )
    made = sessionmaker(bind=engine)()
    yield made
    made.close()
    engine.dispose()


@pytest.fixture()
def broken_session(tmp_path):
    """A session against a database with no table: the write fails, the caller must not."""
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    made = sessionmaker(bind=engine)()
    yield made
    made.close()
    engine.dispose()


def test_a_written_decision_returns_the_row_it_landed_in(session, monkeypatch) -> None:
    import attrition_serving.api.routers.predict as route

    monkeypatch.setattr(
        route,
        "_INSERT_PRED",
        text(
            "INSERT INTO predictions (employee_id, input_payload, proba_depart, prediction, "
            "threshold, model_version) VALUES (:employee_id, :input_payload, :proba, :pred, "
            ":thr, :ver) RETURNING id"
        ),
    )

    written = _log_decision(session, **ROW)

    assert isinstance(written, int)
    assert session.execute(text("SELECT COUNT(*) FROM predictions")).scalar_one() == 1


def test_a_log_that_cannot_be_written_returns_nothing_and_raises_nothing(broken_session) -> None:
    assert _log_decision(broken_session, **ROW) is None


def test_the_session_is_usable_again_after_a_failed_write(broken_session) -> None:
    """Without the rollback the session stays in a failed transaction, and so does the next
    request that borrows it from the pool."""
    _log_decision(broken_session, **ROW)

    with pytest.raises(SQLAlchemyError):
        broken_session.execute(text("SELECT * FROM predictions")).all()
    broken_session.rollback()
    assert broken_session.execute(text("SELECT 1")).scalar_one() == 1
