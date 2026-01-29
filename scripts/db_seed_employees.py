from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from attrition_serving.db import get_engine
from attrition_serving.env import load_env

EXPECTED_PATH = Path("models/expected_features.json")
SAMPLE_PATH = Path("data/processed/api_test/X_test_sample.json")


def main(reset: bool | None = None) -> None:
    load_env()  # utilise ENV_FILE

    # reset par défaut : True si local, False sinon
    env_file = os.getenv("ENV_FILE", ".env.local")
    if reset is None:
        reset = env_file == ".env.local"

    engine = get_engine()
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))

    rows = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows)

    for col in expected:
        if col not in df.columns:
            df[col] = None

    df = df[expected].copy()
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
            conn.execute(text("DELETE FROM predictions;"))
            conn.execute(text("DELETE FROM employees;"))

        stmt = text(
            """
            INSERT INTO employees (employee_id, features)
            VALUES (:employee_id, CAST(:features AS jsonb))
            """
        )
        conn.execute(stmt, payloads)

    print(
        f"✅ Seed OK: {len(payloads)} employees inserted from {SAMPLE_PATH} "
        f"(ENV_FILE={env_file}, reset={reset})"
    )


if __name__ == "__main__":
    main(reset=None)
