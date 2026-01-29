from pathlib import Path

from sqlalchemy import text

from attrition_serving.db import get_engine
from attrition_serving.env import load_env


def main():
    load_env()
    engine = get_engine()
    sql_path = Path("sql/serving/02_seed_checks.sql")
    sql = sql_path.read_text(encoding="utf-8")

    with engine.connect() as conn:
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            res = conn.execute(text(stmt))
            try:
                rows = res.fetchall()
                print(rows[:5])
            except Exception:
                print("(no rows)")

    print("✅ Checks executed")


if __name__ == "__main__":
    main()
