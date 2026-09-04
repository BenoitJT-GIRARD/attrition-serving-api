"""Replay `sql/serving/02_seed_checks.sql` statement by statement and print what each returns.

The fastest way to see whether a seed landed, and what the log currently holds.
"""

from pathlib import Path

from sqlalchemy import text

from attrition_serving.db.engine import get_engine
from attrition_serving.env import load_env


def main():
    load_env()
    engine = get_engine()
    sql_path = Path("sql/serving/02_seed_checks.sql")
    sql = sql_path.read_text(encoding="utf-8")

    with engine.connect() as conn:
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            res = conn.execute(text(stmt))
            # A DDL or DML statement has no result set to fetch; that is the only
            # reason this can raise here, and catching everything hid it.
            if res.returns_rows:
                print(res.fetchall()[:5])
            else:
                print("(no rows)")

    print("✅ Checks executed")


if __name__ == "__main__":
    main()
