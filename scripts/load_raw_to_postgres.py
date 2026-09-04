"""Load the three raw extracts into PostgreSQL, for the exploratory SQL views.

This belongs to the analysis side, not to serving: the API never reads these tables. It
needs the extracts, which are not in the repository.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from attrition_serving.config import PATHS
from attrition_serving.db.engine import get_engine


def sanitize_column(name: str) -> str:
    # lower + remove accents + replace non-alphanum by _
    s = name.strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if s and s[0].isdigit():
        s = f"col_{s}"
    return s


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8", sep=",", low_memory=False)
    df = df.rename(columns={c: sanitize_column(c) for c in df.columns})
    return df


def main():
    engine = get_engine()

    files = {
        "sirh_raw": PATHS.data_raw / "extrait_sirh.csv",
        "eval_raw": PATHS.data_raw / "extrait_eval.csv",
        "sondage_raw": PATHS.data_raw / "extrait_sondage.csv",
    }

    for table, path in files.items():
        df = load_csv(path)
        print(f"{table}: {df.shape} from {path.name}")
        df.to_sql(table, engine, if_exists="replace", index=False)
        print(f" -> loaded into {table}")

    print("Done.")


if __name__ == "__main__":
    main()
