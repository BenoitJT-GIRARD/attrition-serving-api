from __future__ import annotations

import pandas as pd
from sklearn.model_selection import GridSearchCV


def run_grid_search(
    pipeline,
    param_grid: dict,
    X_train,
    y_train,
    cv,
    scoring: str = "average_precision",
    n_jobs: int = -1,
    verbose: int = 1,
):
    gs = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        scoring=scoring,
        cv=cv,
        n_jobs=n_jobs,
        verbose=verbose,
        return_train_score=True,
    )
    gs.fit(X_train, y_train)
    return gs


def summarize_grid_search(gs: GridSearchCV) -> pd.DataFrame:
    df = pd.DataFrame(gs.cv_results_).copy()
    cols = [
        "rank_test_score",
        "mean_test_score",
        "std_test_score",
        "mean_train_score",
        "std_train_score",
        "params",
    ]
    df = df[cols].sort_values("rank_test_score")
    return df
