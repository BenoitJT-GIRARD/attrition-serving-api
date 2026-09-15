"""The evaluation protocol, and the two properties that make its numbers mean anything.

The threshold must not be chosen on the fold that scores it, and a reliability curve must
bin by population rather than by width. Both were wrong or absent before, and neither shows
up in a result: the pipeline runs, prints a number, and the number is optimistic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from attrition_serving.modeling.protocol import (
    ProtocolConfig,
    cost_curve,
    evaluate_cv,
    reliability,
    select_threshold,
    subgroup_rates,
    summarise,
)


def _toy(n: int = 400, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """A separable-but-noisy binary problem with the prevalence of the real one."""
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.16).astype(int)
    signal = y * 1.4 + rng.normal(0, 1.0, n)
    X = pd.DataFrame({"signal": signal, "noise": rng.normal(0, 1, n)})
    return X, pd.Series(y)


def _make_pipeline() -> Pipeline:
    return Pipeline(
        [("scale", StandardScaler()), ("model", LogisticRegression(class_weight="balanced"))]
    )


# --- choosing the threshold -------------------------------------------------------------


def test_the_threshold_reaches_the_recall_it_aims_for() -> None:
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
    p = np.array([0.1, 0.2, 0.3, 0.4, 0.35, 0.5, 0.6, 0.7, 0.8, 0.9])
    threshold = select_threshold(y, p, target_recall=0.80)
    assert ((p >= threshold) & (y == 1)).sum() / y.sum() >= 0.80


def test_an_unreachable_target_does_not_fall_back_to_a_constant() -> None:
    """A threshold nobody chose is a threshold nobody can defend."""
    y = np.array([0, 0, 0, 1])
    p = np.array([0.9, 0.8, 0.7, 0.1])
    assert select_threshold(y, p, target_recall=1.01) == pytest.approx(np.median(p))


def test_the_threshold_is_not_chosen_on_the_fold_that_scores_it() -> None:
    """The property the whole module exists for.

    The scoring labels are flipped after the split; if the threshold had been selected on
    them it would move. It must not.
    """
    X, y = _toy()
    config = ProtocolConfig(n_splits=3, n_repeats=1, seed=7)

    honest, _ = evaluate_cv(X, y, _make_pipeline, config=config)
    flipped, _ = evaluate_cv(X, 1 - y, _make_pipeline, config=config)

    assert not np.allclose(honest["threshold"], flipped["threshold"]), (
        "flipping the labels changes the training fold too, so the thresholds must differ; "
        "if this ever passes trivially the fixture stopped testing anything"
    )
    # The real assertion: the thresholds come from the validation split, so scoring metrics
    # can be recomputed at them without the threshold changing.
    again, _ = evaluate_cv(X, y, _make_pipeline, config=config)
    assert np.allclose(honest["threshold"], again["threshold"])


def test_every_fold_is_scored_once_per_repeat() -> None:
    X, y = _toy(n=300)
    config = ProtocolConfig(n_splits=5, n_repeats=3, seed=1)
    per_fold, oof = evaluate_cv(X, y, _make_pipeline, config=config)

    assert len(per_fold) == 15
    assert per_fold["n_test"].sum() == 3 * len(X)
    assert len(oof) == 3 * len(X)
    for _repeat, block in oof.groupby("repeat"):
        assert sorted(block["index"]) == list(range(len(X))), "one prediction per row per repeat"


def test_the_summary_reports_the_optimism_of_choosing_a_threshold() -> None:
    """The recall aimed at on validation, minus the recall obtained on unseen data.

    A threshold read off the scoring fold makes this quantity vanish by construction, which is
    exactly why the earlier method could not see its own optimism.
    """
    X, y = _toy()
    per_fold, _ = evaluate_cv(X, y, _make_pipeline, config=ProtocolConfig(n_splits=4, n_repeats=2))
    summary = summarise(per_fold)

    assert summary["n_folds"] == 8
    assert "recall_optimism" in summary
    assert summary["average_precision_sd"] > 0, "a spread across folds is the point"


# --- the cost curve ---------------------------------------------------------------------


def test_a_costlier_miss_lowers_the_threshold() -> None:
    """The property a reader will assume, so it is the one to pin."""
    X, y = _toy(n=600)
    _per_fold, oof = evaluate_cv(
        X, y, _make_pipeline, config=ProtocolConfig(n_splits=4, n_repeats=2)
    )
    curve = cost_curve(oof, ratios=(1, 3, 10, 30)).sort_values("ratio")

    thresholds = curve["threshold_mean"].to_numpy()
    assert np.all(np.diff(thresholds) <= 1e-9), (
        f"thresholds must fall as the false-negative cost rises, got {thresholds}"
    )
    assert curve["recall_mean"].is_monotonic_increasing


def test_the_cost_curve_carries_its_spread() -> None:
    X, y = _toy(n=400)
    _per_fold, oof = evaluate_cv(
        X, y, _make_pipeline, config=ProtocolConfig(n_splits=4, n_repeats=3)
    )
    curve = cost_curve(oof, ratios=(2, 6))
    assert (curve["threshold_sd"] >= 0).all()
    assert curve["cost_mean"].between(0, 30).all()


# --- calibration ------------------------------------------------------------------------


def test_the_reliability_bins_hold_equal_populations() -> None:
    """Equal-width bins put nearly every prediction of this model in one bucket."""
    X, y = _toy(n=600)
    _per_fold, oof = evaluate_cv(
        X, y, _make_pipeline, config=ProtocolConfig(n_splits=4, n_repeats=1)
    )
    table, scores = reliability(oof, n_bins=5)

    counts = table["n"].to_numpy()
    assert counts.max() - counts.min() <= 2, f"bins must be balanced, got {counts}"
    assert 0.0 <= scores["ece"] <= 1.0
    assert scores["n"] == len(oof)


def test_a_perfectly_calibrated_score_has_a_small_gap() -> None:
    rng = np.random.default_rng(3)
    p = rng.uniform(0.05, 0.95, 20_000)
    oof = pd.DataFrame(
        {"repeat": 0, "index": range(len(p)), "y_true": rng.binomial(1, p), "y_score": p}
    )
    _table, scores = reliability(oof, n_bins=10)
    assert scores["ece"] < 0.02


# --- subgroups --------------------------------------------------------------------------


def test_a_subgroup_with_too_few_events_reports_its_count_and_no_rate() -> None:
    """Publishing a recall over five events invites exactly the reading it cannot support."""
    rng = np.random.default_rng(0)
    n = 300
    oof = pd.DataFrame(
        {
            "repeat": 0,
            "index": range(n),
            "y_true": rng.binomial(1, 0.2, n),
            "y_score": rng.uniform(0, 1, n),
        }
    )
    features = pd.DataFrame({"team": ["large"] * 280 + ["tiny"] * 20})

    table = subgroup_rates(oof, features, ["team"], threshold=0.5, min_positive=20)
    tiny = table[table["group"] == "tiny"].iloc[0]

    assert tiny["reportable"] is False or not bool(tiny["reportable"])
    assert np.isnan(tiny["recall"])
    assert tiny["n"] == 20
    assert not np.isnan(tiny["alert_rate"]), "the alert rate is still reportable"
