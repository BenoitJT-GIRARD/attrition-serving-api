from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from attrition_serving.db import get_engine
from attrition_serving.env import load_env


def main() -> None:
    # Choix explicite de l'environnement
    load_env(".env.supabase")  # ou ".env.local"

    engine = get_engine()
    sql_path = Path("sql/serving/01_schema.sql")
    sql = sql_path.read_text(encoding="utf-8")

    with engine.begin() as conn:
        conn.execute(text(sql))

    print("✅ Schema applied")


if __name__ == "__main__":
    main()
