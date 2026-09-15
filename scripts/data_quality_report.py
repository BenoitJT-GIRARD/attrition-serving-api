"""The data-quality dossier, in one place and as a file rather than as prose.

    uv run python scripts/data_quality_report.py

Four questions a reader of an HR model asks, and that this repository answered in scattered
notebook cells or not at all:

- **what is in the data** — rows, columns, missing values, target distribution;
- **what the cleaning changed** — the same counts before and after the join;
- **which features are redundant** — the correlated pairs, and the decision taken;
- **how the categoricals are encoded** — which are nominal, which are ordinal, and in what
  order.

Writes `reports/data_quality.csv`, `reports/cleaning_trace.csv` and
`reports/feature_encoding.csv`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from attrition_serving.config import PATHS
from attrition_serving.preprocessing import make_feature_groups

TARGET = "a_quitte_l_entreprise"

#: Above this absolute Spearman correlation, two features carry substantially the same
#: information. Reported, not dropped: a linear model with L2 handles collinearity, and
#: dropping a column changes what the coefficients mean.
REDUNDANCY_THRESHOLD = 0.80


def quality_table(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per column: type, completeness, cardinality, and how it is treated."""
    groups = make_feature_groups(frame, target=TARGET)
    treatment = {}
    for name, columns in (
        ("median impute + standardise", groups.num_cont),
        ("median impute + log1p + standardise", groups.num_log),
        ("median impute", groups.num_disc),
        ("passthrough (already 0/1)", groups.bin_cols),
        ("most-frequent impute + one-hot", groups.cat_nom),
        ("most-frequent impute + ordinal, order declared", groups.cat_ord),
    ):
        for column in columns:
            treatment[column] = name

    rows = []
    for column in frame.columns:
        series = frame[column]
        rows.append(
            {
                "column": column,
                "dtype": str(series.dtype),
                "n_missing": int(series.isna().sum()),
                "pct_missing": round(float(series.isna().mean()) * 100, 2),
                "n_unique": int(series.nunique(dropna=True)),
                "treatment": (
                    "target" if column == TARGET else treatment.get(column, "not used by the model")
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("column").reset_index(drop=True)


def cleaning_trace(raw_dir: Path, joined: pd.DataFrame, featured: pd.DataFrame) -> pd.DataFrame:
    """The same counts at each stage, so the join can be read rather than trusted."""
    rows = []
    for path in sorted(raw_dir.glob("*.csv")):
        source = pd.read_csv(path)
        rows.append(
            {
                "stage": f"raw: {path.name}",
                "rows": len(source),
                "columns": source.shape[1],
                "cells_missing": int(source.isna().sum().sum()),
                "pct_missing": round(float(source.isna().mean().mean()) * 100, 2),
                "duplicated_rows": int(source.duplicated().sum()),
            }
        )
    for stage, frame in (("joined", joined), ("engineered", featured)):
        rows.append(
            {
                "stage": stage,
                "rows": len(frame),
                "columns": frame.shape[1],
                "cells_missing": int(frame.isna().sum().sum()),
                "pct_missing": round(float(frame.isna().mean().mean()) * 100, 2),
                "duplicated_rows": int(frame.duplicated().sum()),
            }
        )
    return pd.DataFrame(rows)


def redundant_pairs(frame: pd.DataFrame) -> pd.DataFrame:
    """Numeric pairs above the redundancy threshold, with the decision taken on them."""
    numeric = frame.select_dtypes("number").drop(columns=[TARGET], errors="ignore")
    correlation = numeric.corr(method="spearman").abs()
    rows = []
    seen = set()
    for left in correlation.columns:
        for right in correlation.index:
            if left == right or (right, left) in seen:
                continue
            seen.add((left, right))
            value = correlation.loc[right, left]
            if pd.notna(value) and value >= REDUNDANCY_THRESHOLD:
                rows.append(
                    {
                        "feature_a": left,
                        "feature_b": right,
                        "abs_spearman": round(float(value), 3),
                        "decision": "kept",
                        "why": (
                            "L2-regularised logistic regression shares the coefficient "
                            "between correlated features rather than becoming unstable; "
                            "dropping one would change what the other's coefficient means"
                        ),
                    }
                )
    return pd.DataFrame(rows).sort_values("abs_spearman", ascending=False).reset_index(drop=True)


def encoding_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Every categorical, its encoding, and for ordinals the order that was declared."""
    groups = make_feature_groups(frame, target=TARGET)
    rows = [
        {
            "column": column,
            "kind": "nominal",
            "encoding": "one-hot, unknown categories ignored",
            "order": "",
        }
        for column in groups.cat_nom
    ]
    for column, categories in zip(groups.cat_ord, groups.ord_categories, strict=False):
        rows.append(
            {
                "column": column,
                "kind": "ordinal",
                "encoding": "ordinal, order declared",
                "order": " < ".join(str(c) for c in categories),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    featured = pd.read_parquet(PATHS.data_processed / "employees_features.parquet")
    joined_path = PATHS.data_processed / "employees_joined.parquet"
    joined = pd.read_parquet(joined_path) if joined_path.exists() else featured

    PATHS.reports.mkdir(parents=True, exist_ok=True)
    quality = quality_table(featured)
    quality.to_csv(PATHS.reports / "data_quality.csv", index=False)

    trace = cleaning_trace(PATHS.data_raw, joined, featured)
    trace.to_csv(PATHS.reports / "cleaning_trace.csv", index=False)

    pairs = redundant_pairs(featured)
    pairs.to_csv(PATHS.reports / "redundant_features.csv", index=False)

    encoding = encoding_table(featured)
    encoding.to_csv(PATHS.reports / "feature_encoding.csv", index=False)

    print(f"{len(featured):,} rows, {featured.shape[1]} columns")
    print(
        f"  target {TARGET}: {int(featured[TARGET].sum())} departures "
        f"({featured[TARGET].mean():.1%})"
    )
    print(f"  columns with missing values: {int((quality['n_missing'] > 0).sum())}")
    print(f"  correlated pairs above {REDUNDANCY_THRESHOLD}: {len(pairs)}")
    print(
        f"  categoricals: {int((encoding['kind'] == 'nominal').sum())} nominal, "
        f"{int((encoding['kind'] == 'ordinal').sum())} ordinal"
    )
    for name in (
        "data_quality.csv",
        "cleaning_trace.csv",
        "redundant_features.csv",
        "feature_encoding.csv",
    ):
        print(f"  [ok] reports/{name}")


if __name__ == "__main__":
    main()
