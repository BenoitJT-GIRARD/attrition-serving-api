from __future__ import annotations

import numpy as np
import pandas as pd

YES_SET = {"Y", "OUI", "Oui", "oui", "o", "yes", "y", "true", "1"}
NO_SET = {"N", "NON", "Non", "non", "n", "no", "false", "0"}


def yes_no_to_int(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.lower()
    out = pd.Series(pd.NA, index=series.index, dtype="Int64")
    out[s.isin(YES_SET)] = 1
    out[s.isin(NO_SET)] = 0
    return out


def percent_to_ratio(series: pd.Series) -> pd.Series:
    # "15%" -> 0.15 ; "0.15" -> 0.15 ; NaN stays NaN
    s = series.astype(str).str.strip()
    s = s.replace({"nan": np.nan, "None": np.nan})
    s = s.str.replace("%", "", regex=False)
    s = pd.to_numeric(s, errors="coerce")
    # Heuristic: if values look like 15 (percent points), convert to 0.15
    return np.where(s > 1, s / 100.0, s)


def safe_divide(num: pd.Series, den: pd.Series) -> pd.Series:
    num = pd.to_numeric(num, errors="coerce")
    den = pd.to_numeric(den, errors="coerce")
    return np.where((den > 0) & (~den.isna()) & (~num.isna()), num / den, np.nan)


def drop_constant_columns(df: pd.DataFrame, candidates: list[str] | None = None) -> pd.DataFrame:
    out = df.copy()
    cols = candidates if candidates is not None else list(out.columns)
    to_drop = []
    for c in cols:
        if c in out.columns and out[c].nunique(dropna=False) <= 1:
            to_drop.append(c)
    return out.drop(columns=to_drop, errors="ignore")
