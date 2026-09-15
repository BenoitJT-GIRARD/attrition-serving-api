"""Create the serving tables from `sql/serving/01_schema.sql`. Idempotent; safe to rerun."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from attrition_serving.db.engine import get_engine
from attrition_serving.env import load_env


def main() -> None:
    load_env()

    engine = get_engine()
    sql_path = Path("sql/serving/01_schema.sql")
    sql = sql_path.read_text(encoding="utf-8")

    with engine.begin() as conn:
        conn.execute(text(sql))

    print("[ok] schema applied")


if __name__ == "__main__":
    main()
