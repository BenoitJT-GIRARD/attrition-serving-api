"""Create the serving tables from `sql/serving/01_schema.sql`. Idempotent; safe to rerun."""

from __future__ import annotations

from attrition_serving.db.engine import get_engine
from attrition_serving.db.serving_ops import apply_schema
from attrition_serving.env import load_env


def main() -> None:
    load_env()

    engine = get_engine()
    apply_schema(engine)

    print("[ok] schema applied")


if __name__ == "__main__":
    main()
