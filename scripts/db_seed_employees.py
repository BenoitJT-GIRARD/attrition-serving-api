"""Load the ten committed request fixtures into `employees`, so `/predict_by_id` has rows.

Ten rows, and not the whole extract: the dataset is not redistributed here, and ten rows
in request shape are what a demonstration and the API tests need. `docs/data-source.md`
says where the full extract comes from.
"""

from __future__ import annotations

import json
import os

import pandas as pd
from sqlalchemy import text

from attrition_serving.db.engine import get_engine
from attrition_serving.env import load_env
from attrition_serving.utils.paths import MODELS_DIR, TESTS_DIR

EXPECTED_PATH = MODELS_DIR / "expected_features.json"
SAMPLE_PATH = TESTS_DIR / "fixtures" / "employees_sample.json"


def main(reset: bool | None = None) -> None:
    load_env()  # ENV_FILE picks the deployment file

    # Wiping first is the local default, and never the remote one: re-seeding a shared
    # database would delete rows somebody else is looking at.
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
        f"[ok] {len(payloads)} employees seeded from {SAMPLE_PATH} "
        f"(ENV_FILE={env_file}, reset={reset})"
    )


if __name__ == "__main__":
    main(reset=None)
