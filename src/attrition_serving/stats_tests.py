from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def _is_normal(x: np.ndarray) -> bool:
    x = x[~np.isnan(x)]
    if x.size < 8:
        return False
    # normaltest needs n>=8, ok here
    p = stats.normaltest(x).pvalue
    return p > 0.05


def compare_groups_univariate(df: pd.DataFrame, target: str, cols: list[str]) -> pd.DataFrame:
    out = []
    d = df.copy()
    d = d[d[target].isin([0, 1])]
    g0 = d[d[target] == 0]
    g1 = d[d[target] == 1]

    for col in cols:
        if col not in d.columns:
            continue
        x0 = pd.to_numeric(g0[col], errors="coerce").to_numpy()
        x1 = pd.to_numeric(g1[col], errors="coerce").to_numpy()

        x0 = x0[~np.isnan(x0)]
        x1 = x1[~np.isnan(x1)]
        if len(x0) < 5 or len(x1) < 5:
            continue

        normal = _is_normal(x0) and _is_normal(x1)
        if normal:
            test = "t_test_welch"
            stat, p = stats.ttest_ind(x0, x1, equal_var=False)
            # effect size: Cohen's d
            d_eff = (np.mean(x1) - np.mean(x0)) / np.sqrt(
                (np.var(x0, ddof=1) + np.var(x1, ddof=1)) / 2
            )
        else:
            test = "mann_whitney"
            stat, p = stats.mannwhitneyu(x0, x1, alternative="two-sided")
            d_eff = np.nan

        out.append(
            {
                "feature": col,
                "test": test,
                "statistic": float(stat),
                "p_value": float(p),
                "mean_group0": float(np.mean(x0)),
                "mean_group1": float(np.mean(x1)),
                "mean_diff": float(np.mean(x1) - np.mean(x0)),
                "effect_size_cohens_d_if_t": float(d_eff) if np.isfinite(d_eff) else np.nan,
            }
        )

    res = pd.DataFrame(out).sort_values("p_value")
    if not res.empty:
        res["p_value_fdr"] = multipletests(res["p_value"], method="fdr_bh")[1]
    return res
