"""The estimators, and the single-split tools the protocol replaced.

`modeling/evaluation.py` and `modeling/tuning.py` are the historical machinery: one split, one
threshold read off it. They are kept because notebooks 04 and 05 show that step and say what
was wrong with it, and they are tested because untested code that still runs is code nobody
can change.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from attrition_serving.modeling.evaluation import evaluate_classifier, find_threshold_for_recall
from attrition_serving.modeling.models import make_dummy, make_logreg, make_random_forest
from attrition_serving.modeling.tuning import run_grid_search, summarize_grid_search
from attrition_serving.preprocessing import FeatureGroups


@pytest.fixture()
def groups() -> FeatureGroups:
    return FeatureGroups(
        num_cont=["age"],
        num_log=["revenu_mensuel"],
        num_disc=["nb_formations_suivies"],
        bin_cols=["genre"],
        cat_nom=["departement"],
        cat_ord=["niveau_education"],
        ord_categories=[[1, 2, 3]],
    )


@pytest.fixture()
def dataset() -> tuple[pd.DataFrame, pd.Series]:
    """Sixty rows where the signal is real but weak, so every estimator has something to fit."""
    rng = np.random.default_rng(11)
    n = 60
    X = pd.DataFrame(
        {
            "age": rng.integers(22, 58, n),
            "revenu_mensuel": rng.integers(1500, 18000, n),
            "nb_formations_suivies": rng.integers(0, 6, n),
            "genre": rng.integers(0, 2, n),
            "departement": rng.choice(["Commercial", "Consulting"], n),
            "niveau_education": rng.choice([1, 2, 3], n),
        }
    )
    logit = -1.6 + 0.04 * (X["age"] - 40) - 0.00008 * (X["revenu_mensuel"] - 6000)
    y = pd.Series((rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int))
    if y.sum() < 6:  # pragma: no cover - the seed is fixed, the guard documents the need
        y.iloc[:6] = 1
    return X, y


@pytest.mark.parametrize("factory", [make_dummy, make_logreg, make_random_forest])
def test_every_estimator_is_a_pipeline_that_fits_the_preprocessing_inside_the_fold(
    factory, groups, dataset
) -> None:
    """A preprocessor fitted outside the fold leaks the fold's distribution into it."""
    X, y = dataset

    model = factory(groups)

    assert isinstance(model, Pipeline)
    assert list(dict(model.steps)) == ["preprocess", "model"]
    model.fit(X, y)
    assert model.predict_proba(X).shape == (len(X), 2)


def test_the_two_fitted_estimators_are_seeded(groups) -> None:
    """`saga` is stochastic, and an unseeded run published a threshold nobody could reproduce."""
    assert make_logreg(groups).named_steps["model"].random_state == 42
    assert make_random_forest(groups).named_steps["model"].random_state == 42


def test_the_single_split_evaluation_reports_both_sides_of_the_split(groups, dataset) -> None:
    X, y = dataset
    train, test = slice(0, 40), slice(40, 60)

    out = evaluate_classifier(
        make_logreg(groups), X[train], y[train], X[test], y[test], threshold=0.3
    )

    assert out["threshold"] == 0.3
    assert 0.0 <= out["test_ap"] <= 1.0
    assert out["train_cm"].shape == (2, 2)
    assert len(out["p_test"]) == 20


def test_the_highest_threshold_that_still_reaches_the_target_recall_is_the_one_returned() -> None:
    y = np.array([0, 0, 1, 1, 0, 1, 1, 0])
    p = np.array([0.1, 0.2, 0.9, 0.8, 0.3, 0.7, 0.6, 0.4])

    threshold = find_threshold_for_recall(y, p, target_recall=0.75)

    assert (p >= threshold)[y == 1].mean() >= 0.75
    assert threshold > find_threshold_for_recall(y, p, target_recall=1.0)


def test_an_unreachable_recall_falls_back_to_a_half_and_says_nothing_clever() -> None:
    y = np.array([0, 1])
    p = np.array([0.9, 0.1])

    assert find_threshold_for_recall(y, p, target_recall=1.01) == 0.5


def test_the_grid_search_returns_a_table_one_row_per_combination(groups, dataset) -> None:
    X, y = dataset

    search = run_grid_search(
        make_logreg(groups), {"model__C": [0.1, 1.0]}, X, y, cv=2, n_jobs=1, verbose=0
    )
    table = summarize_grid_search(search)

    assert len(table) == 2
    assert "mean_test_score" in table.columns
    assert table["rank_test_score"].is_monotonic_increasing
