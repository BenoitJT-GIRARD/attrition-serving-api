from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from sqlalchemy import Engine, text


def apply_schema(engine: Engine, schema_path: str = "sql/serving/01_schema.sql") -> None:
    sql = Path(schema_path).read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))


def truncate_predictions(engine: Engine) -> None:
    # On vide uniquement predictions (utile pour tests d'intégration)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE predictions RESTART IDENTITY;"))


AllowedTable = Literal["employees", "predictions"]


def count_rows(engine: Engine, table: AllowedTable) -> int:
    # Whitelist stricte pour éviter toute injection SQL
    queries = {
        "employees": "SELECT COUNT(*) FROM employees;",
        "predictions": "SELECT COUNT(*) FROM predictions;",
    }
    with engine.connect() as conn:
        return int(conn.execute(text(queries[table])).scalar_one())


def fetch_history(engine: Engine, limit: int = 50) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT id, created_at, employee_id, proba_depart, prediction, threshold, model_version
                FROM predictions
                ORDER BY created_at DESC
                LIMIT :limit
                """
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]
