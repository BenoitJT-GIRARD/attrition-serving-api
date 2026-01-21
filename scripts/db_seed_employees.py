from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from attrition_serving.db import get_engine
from attrition_serving.env import load_env

EXPECTED_PATH = Path("models/expected_features.json")
SAMPLE_PATH = Path("data/processed/api_test/X_test_sample.json")


def main(reset: bool = True) -> None:
    load_env(".env.supabase")  # ou ".env.local"

    engine = get_engine()
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))

    # X_test_sample.json doit être un JSON "records": [{...}, {...}]
    rows = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows)

    # S'assure que toutes les features attendues existent
    for col in expected:
        if col not in df.columns:
            df[col] = None

    # Garde uniquement les features attendues, dans l'ordre exact
    df = df[expected].copy()

    # IDs stables (1..N)
    df.insert(0, "employee_id", range(1, len(df) + 1))

    payloads = [
        {
            "employee_id": int(r["employee_id"]),
            "features": json.dumps({k: r[k] for k in expected}),
        }
        for r in df.to_dict(orient="records")
    ]

    with engine.begin() as conn:
        if reset:
            # reset pour POC / démo
            conn.execute(text("DELETE FROM predictions;"))
            conn.execute(text("DELETE FROM employees;"))

        stmt = text(
            """
            INSERT INTO employees (employee_id, features)
            VALUES (:employee_id, CAST(:features AS jsonb))
            """
        )
        conn.execute(stmt, payloads)

    print(f"✅ Seed OK (sample): {len(payloads)} employees inserted from {SAMPLE_PATH}")


if __name__ == "__main__":
    main(reset=True)
