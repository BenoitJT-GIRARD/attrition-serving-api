from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


@dataclass(frozen=True)
class ColumnSpec:
    target: str
    categorical: list[str]
    numerical: list[str]
    ordinal: list[str] | None = None


def require_columns(df: pd.DataFrame, cols: Iterable[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns in dataframe: {missing}")


def print_basic_overview(df: pd.DataFrame, max_cols: int = 60) -> None:
    print("Shape:", df.shape)
    print("\nColumns (first ones):")
    cols = list(df.columns)
    print(cols[:max_cols])
    if len(cols) > max_cols:
        print(f"... (+{len(cols) - max_cols} more)")


def target_distribution(df: pd.DataFrame, target: str) -> pd.Series:
    require_columns(df, [target])
    return df[target].value_counts(dropna=False)


def plot_categorical_share(df: pd.DataFrame, col: str, target: str | None = None) -> None:
    """
    If target is provided, shows distribution of `col` within each target class.
    Else shows overall distribution.
    """
    require_columns(df, [col])
    if target is None:
        vc = df[col].value_counts(dropna=False)
        ax = vc.plot(kind="bar")
        ax.set_title(f"Distribution - {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Count")
        plt.tight_layout()
        return

    require_columns(df, [target])
    ct = pd.crosstab(df[col], df[target], normalize="columns") * 100
    ax = ct.plot(kind="bar", stacked=False)
    ax.set_title(f"{col} (%) par classe de {target}")
    ax.set_xlabel(col)
    ax.set_ylabel("% within class")
    plt.tight_layout()


def plot_numeric_distribution(df: pd.DataFrame, col: str, bins: int = 30) -> None:
    require_columns(df, [col])
    s = df[col].dropna()
    plt.figure()
    plt.hist(s, bins=bins)
    plt.title(f"Distribution - {col}")
    plt.xlabel(col)
    plt.ylabel("Count")
    plt.tight_layout()


def plot_numeric_by_target(df: pd.DataFrame, col: str, target: str) -> None:
    require_columns(df, [col, target])
    plt.figure()
    sns.boxplot(data=df, x=target, y=col)
    plt.title(f"{col} selon {target}")
    plt.tight_layout()


def numeric_group_stats(df: pd.DataFrame, numeric_cols: list[str], target: str) -> pd.DataFrame:
    require_columns(df, numeric_cols + [target])
    return df.groupby(target)[numeric_cols].agg(["count", "mean", "std", "median", "min", "max"])
