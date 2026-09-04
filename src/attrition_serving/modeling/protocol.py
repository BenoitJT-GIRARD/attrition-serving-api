"""The evaluation protocol: how this repository is allowed to produce a number.

Everything published about the model comes through here, and the module exists because the
previous arrangement made two mistakes that a reader cannot see in a result.

**The operating point was chosen on the data that scored it.** The tuning notebook ran
``find_threshold_for_recall(y_test, p_test, target_recall=0.80)``. A recall of 0.80 obtained
that way is not a property of the model, it is the definition of the threshold. Here the
threshold is chosen inside the training part of each fold, on a validation split the scoring
fold never touches, and the gap between the recall aimed at and the recall obtained is
itself reported -- that gap is the price of the earlier method.

**A single 10% split carried every figure.** 147 rows, 24 of them leavers. Bootstrapped, the
average precision on that split spans [0.355, 0.726]. Repeated stratified cross-validation
uses all 1,470 rows and reports the spread it actually has.

Nothing here reads the test fold to decide anything: not the threshold, not the
recalibration, not the subgroup cut points.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split

#: The share of each training fold held out to choose the threshold. Large enough that the
#: recall curve is not a five-step staircase, small enough to leave the model its data.
VALIDATION_SHARE = 0.25


@dataclass(frozen=True)
class ProtocolConfig:
    """Everything that decides what a published number means."""

    n_splits: int = 5
    n_repeats: int = 5
    seed: int = 42
    #: The recall the threshold aims for, on the validation split. Kept as the historical
    #: target so the two methods can be compared; `cost_curve` is what replaces it.
    target_recall: float = 0.80
    #: How the probabilities are recalibrated before a threshold is read off them.
    #:
    #: - ``"none"`` — raw scores. `class_weight="balanced"` deliberately inflates the
    #:   positive class, so these rank well and are not probabilities.
    #: - ``"holdout"`` — isotonic fitted on the inner validation split.
    #: - ``"crossfit"`` — isotonic fitted by internal cross-validation over the whole
    #:   training fold.
    #:
    #: The distinction between the last two is not cosmetic, and measuring it corrected a
    #: claim this module first stated as fact. Isotonic *is* monotone, so it cannot reorder
    #: anything -- but it is a step function, and it maps many distinct scores onto one
    #: value. Ties are what average precision and ROC AUC penalise. Fitted on ~250 rows the
    #: staircase is coarse, and the ranking pays for it; fitted across the training fold it
    #: has enough steps to keep it.
    calibration: str = "none"


def select_threshold(y_true, p_hat, target_recall: float = 0.80) -> float:
    """The lowest threshold whose recall reaches ``target_recall`` on the data given.

    Returns the median probability when the target is unreachable, rather than 0.5: a
    constant taken from nowhere is how a threshold stops being traceable to anything.
    """
    y_true = np.asarray(y_true)
    p_hat = np.asarray(p_hat)
    _precision, recall, thresholds = precision_recall_curve(y_true, p_hat)
    reachable = np.flatnonzero(recall[:-1] >= target_recall)
    if reachable.size == 0:
        return float(np.median(p_hat))
    return float(thresholds[reachable[-1]])


def _scores_at(y_true, p_hat, threshold: float) -> dict[str, float]:
    y_pred = (np.asarray(p_hat) >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "alert_rate": float(y_pred.mean()),
    }


def evaluate_cv(
    X: pd.DataFrame,
    y: pd.Series,
    make_pipeline,
    params: dict | None = None,
    config: ProtocolConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Repeated stratified cross-validation, with the threshold chosen inside each fold.

    Returns ``(per_fold, out_of_fold)``:

    - ``per_fold`` — one row per fold: AP, ROC AUC, the threshold chosen on the validation
      split, and the precision/recall it gives on the scoring fold;
    - ``out_of_fold`` — one row per (repeat, sample): the true label and the probability
      predicted by a model that never saw it. Calibration and subgroup rates are computed
      from this, which is why it is returned rather than summarised away.
    """
    cfg = config or ProtocolConfig()
    y = pd.Series(y).astype(int).reset_index(drop=True)
    X = X.reset_index(drop=True)

    splitter = RepeatedStratifiedKFold(
        n_splits=cfg.n_splits, n_repeats=cfg.n_repeats, random_state=cfg.seed
    )
    rows: list[dict] = []
    oof: list[pd.DataFrame] = []

    for position, (train_idx, test_idx) in enumerate(splitter.split(X, y)):
        repeat, fold = divmod(position, cfg.n_splits)
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # The threshold is chosen here, on a split of the *training* fold. The scoring fold
        # is not read until the row below is written.
        X_fit, X_val, y_fit, y_val = train_test_split(
            X_train,
            y_train,
            test_size=VALIDATION_SHARE,
            random_state=cfg.seed + position,
            stratify=y_train,
        )
        inner = clone(make_pipeline())
        if params:
            inner.set_params(**params)
        if cfg.calibration == "crossfit":
            # The threshold has to be read off the same probability scale the service will
            # use, so the inner model is calibrated the same way as the outer one.
            inner = CalibratedClassifierCV(inner, method="isotonic", cv=5, ensemble=False)
        inner.fit(X_fit, y_fit)
        p_val = inner.predict_proba(X_val)[:, 1]

        # The recalibration is fitted on the same validation split as the threshold, and
        # for the same reason: it is a decision, and decisions are not made on the data
        # that judges them.
        calibrator = None
        if cfg.calibration == "holdout":
            calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            calibrator.fit(p_val, y_val)
            p_val = calibrator.predict(p_val)
        elif cfg.calibration not in {"none", "crossfit"}:
            raise ValueError(f"unknown calibration {cfg.calibration!r}")

        threshold = select_threshold(y_val, p_val, cfg.target_recall)
        validation_recall = _scores_at(y_val, p_val, threshold)["recall"]

        # Refit on the whole training fold, so the scored model uses every row it is
        # entitled to. Only then is the scoring fold touched.
        model = clone(make_pipeline())
        if params:
            model.set_params(**params)
        if cfg.calibration == "crossfit":
            model = CalibratedClassifierCV(model, method="isotonic", cv=5, ensemble=False)
        model.fit(X_train, y_train)
        p_test = model.predict_proba(X_test)[:, 1]
        if calibrator is not None:
            p_test = calibrator.predict(p_test)

        rows.append(
            {
                "repeat": repeat,
                "fold": fold,
                "n_test": len(test_idx),
                "n_positive": int(y_test.sum()),
                "average_precision": float(average_precision_score(y_test, p_test)),
                "roc_auc": float(roc_auc_score(y_test, p_test)),
                "threshold": threshold,
                "validation_recall": validation_recall,
                **_scores_at(y_test, p_test, threshold),
            }
        )
        oof.append(
            pd.DataFrame(
                {
                    "repeat": repeat,
                    "index": test_idx,
                    "y_true": y_test.to_numpy(),
                    "y_score": p_test,
                }
            )
        )

    return pd.DataFrame(rows), pd.concat(oof, ignore_index=True)


def summarise(per_fold: pd.DataFrame) -> dict[str, float | int]:
    """Mean and spread across folds, for every quantity the repository publishes."""
    summary: dict[str, float | int] = {
        "n_folds": len(per_fold),
        "n_rows_scored": int(per_fold["n_test"].sum()),
        "n_positive_scored": int(per_fold["n_positive"].sum()),
    }
    for column in (
        "average_precision",
        "roc_auc",
        "threshold",
        "recall",
        "precision",
        "f1",
        "alert_rate",
        "validation_recall",
    ):
        summary[f"{column}_mean"] = float(per_fold[column].mean())
        summary[f"{column}_sd"] = float(per_fold[column].std(ddof=1))
    # The distance between the recall the threshold was chosen for and the recall it
    # actually delivers on unseen data. Choosing on the test set drives this to zero by
    # construction, which is exactly why it was invisible.
    summary["recall_optimism"] = summary["validation_recall_mean"] - summary["recall_mean"]
    return summary


def cost_curve(
    out_of_fold: pd.DataFrame, ratios: tuple[float, ...] = (1, 2, 3, 5, 8, 13, 20)
) -> pd.DataFrame:
    """The threshold that minimises expected cost, for each false-negative / false-positive
    ratio.

    A false positive is a retention conversation held for nothing. A false negative is a
    departure nobody saw coming. The repository does not claim to know the ratio for a given
    employer; it shows the threshold each ratio implies and how fast the answer moves.

    Computed per repeat and aggregated, so the spread of the optimum is visible: a curve
    whose optimum wanders across repeats is not an operating point, it is a suggestion.
    """
    records: list[dict] = []
    for ratio in ratios:
        for repeat, block in out_of_fold.groupby("repeat"):
            y_true = block["y_true"].to_numpy()
            p_hat = block["y_score"].to_numpy()
            grid = np.unique(np.round(p_hat, 4))
            costs = []
            for threshold in grid:
                y_pred = (p_hat >= threshold).astype(int)
                false_negative = int(((y_pred == 0) & (y_true == 1)).sum())
                false_positive = int(((y_pred == 1) & (y_true == 0)).sum())
                costs.append(ratio * false_negative + false_positive)
            best = int(np.argmin(costs))
            y_pred = (p_hat >= grid[best]).astype(int)
            records.append(
                {
                    "ratio": ratio,
                    "repeat": int(repeat),
                    "threshold": float(grid[best]),
                    "expected_cost_per_employee": costs[best] / len(y_true),
                    **_scores_at(y_true, p_hat, float(grid[best])),
                }
            )

    per_repeat = pd.DataFrame(records)
    return (
        per_repeat.groupby("ratio")
        .agg(
            threshold_mean=("threshold", "mean"),
            threshold_sd=("threshold", "std"),
            cost_mean=("expected_cost_per_employee", "mean"),
            cost_sd=("expected_cost_per_employee", "std"),
            recall_mean=("recall", "mean"),
            precision_mean=("precision", "mean"),
            alert_rate_mean=("alert_rate", "mean"),
        )
        .reset_index()
    )


def reliability(out_of_fold: pd.DataFrame, n_bins: int = 10) -> tuple[pd.DataFrame, dict]:
    """Reliability with equal-population bins, plus Brier and ECE.

    Equal-population, not equal-width: with a model whose scores pile up below 0.3, fixed
    bands put almost every prediction in the first bucket and the curve says nothing about
    the range where the decisions are actually made.
    """
    frame = out_of_fold.copy()
    frame["bin"] = pd.qcut(frame["y_score"], q=n_bins, duplicates="drop")
    grouped = (
        frame.groupby("bin", observed=True)
        .agg(
            n=("y_true", "size"),
            mean_predicted=("y_score", "mean"),
            observed_rate=("y_true", "mean"),
        )
        .reset_index(drop=True)
    )
    grouped["gap"] = grouped["observed_rate"] - grouped["mean_predicted"]

    total = int(grouped["n"].sum())
    ece = float((grouped["n"] / total * grouped["gap"].abs()).sum())
    return grouped, {
        "brier": float(brier_score_loss(frame["y_true"], frame["y_score"])),
        "ece": ece,
        "n": total,
        "base_rate": float(frame["y_true"].mean()),
        "mean_predicted": float(frame["y_score"].mean()),
    }


def subgroup_rates(
    out_of_fold: pd.DataFrame,
    features: pd.DataFrame,
    columns: list[str],
    threshold: float,
    min_positive: int = 20,
) -> pd.DataFrame:
    """Alert rate and recall per subgroup, at the shipped threshold.

    No correction and no fairness claim: a table, and what it says. A subgroup with fewer
    than ``min_positive`` leavers gets its count reported and its recall left empty --
    publishing a rate over five events would invite exactly the reading it cannot support.
    """
    joined = out_of_fold.join(features.reset_index(drop=True), on="index")
    joined["y_pred"] = (joined["y_score"] >= threshold).astype(int)

    records: list[dict] = []
    for column in columns:
        for value, block in joined.groupby(column, observed=True):
            positives = int(block["y_true"].sum())
            enough = positives >= min_positive
            records.append(
                {
                    "attribute": column,
                    "group": str(value),
                    "n": len(block),
                    "n_positive": positives,
                    # The base rate has to sit next to the alert rate, or the two get
                    # confused. A group that leaves twice as often *should* be alerted on
                    # more; what a reader needs to separate is that from a group the model
                    # simply treats differently.
                    "base_rate": float(block["y_true"].mean()),
                    "alert_rate": float(block["y_pred"].mean()),
                    "recall": float(
                        block.loc[block["y_true"] == 1, "y_pred"].mean() if enough else np.nan
                    ),
                    "reportable": enough,
                }
            )
    return pd.DataFrame(records)
