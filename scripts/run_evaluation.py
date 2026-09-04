"""Produce every figure this repository publishes about the model.

    uv run python scripts/run_evaluation.py

Three arms over the same folds and the same seeds — raw scores, isotonic fitted on a
held-out split, isotonic cross-fitted over the training fold — because the choice between
them is a trade-off that has to be measured rather than argued.

Writes to `reports/`:

``evaluation_cv.csv``       one row per fold per arm — AP, ROC AUC, the threshold chosen
                            inside that fold, and what it gives on the fold that scores it
``evaluation_summary.json`` means and spreads for each arm, the calibration scores, and the
                            comparison against the single 90/10 split the repository used
                            to publish
``cost_curve.csv``          the threshold that minimises expected cost, per cost ratio
``calibration.csv``         reliability with equal-population bins, per arm
``subgroups.csv``           alert rate and recall per subgroup at the shipped threshold

The single split is recomputed on purpose: knowing whether it was a favourable draw is part
of the result, and it is the only way to say what changed and by how much.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from attrition_serving.config import FINAL_MODEL_PARAMS, PATHS, SETTINGS
from attrition_serving.modeling.models import make_dummy, make_logreg, make_random_forest
from attrition_serving.modeling.protocol import (
    ProtocolConfig,
    cost_curve,
    evaluate_cv,
    reliability,
    subgroup_rates,
    summarise,
)
from attrition_serving.preprocessing import make_feature_groups

TARGET = "a_quitte_l_entreprise"

#: How the probabilities are recalibrated before a threshold is read off them.
ARMS = ("none", "holdout", "crossfit")

#: The arm that ships. The service returns a number it calls a probability and writes it to
#: PostgreSQL under that name; a number labelled a probability has to be one.
SHIPPED_ARM = "crossfit"

#: How many wasted retention conversations one missed departure is worth. The repository
#: does not know an employer's ratio -- it shows what each one implies, and names the one
#: behind the threshold it ships.
COST_RATIOS = (1, 2, 3, 5, 8, 13, 20, 30)
SHIPPED_RATIO = 8

#: The three model families the notebook compares. Measured under the same protocol as
#: everything else, because the notebook stated their scores in prose -- 0.84 accuracy for
#: the dummy, 66% recall for the logistic regression, 0.106 for the forest -- from a single
#: split, and nothing in the repository produced them.
BASELINES = {
    "dummy": make_dummy,
    "logreg": make_logreg,
    "random_forest": make_random_forest,
}

#: The attributes a retention alert must be shown not to concentrate on.
SUBGROUP_COLUMNS = ("genre", "statut_marital", "departement")


def _single_split_baseline(X: pd.DataFrame, y: pd.Series, frame: pd.DataFrame) -> dict[str, float]:
    """The 90/10 split the repository used to publish, recomputed for comparison."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.10, random_state=SETTINGS.random_state, stratify=y
    )
    model = make_logreg(make_feature_groups(frame, target=TARGET))
    model.set_params(**FINAL_MODEL_PARAMS)
    model.fit(X_train, y_train)
    p = model.predict_proba(X_test)[:, 1]
    return {
        "n_test": len(y_test),
        "n_positive": int(y_test.sum()),
        "average_precision": float(average_precision_score(y_test, p)),
        "roc_auc": float(roc_auc_score(y_test, p)),
    }


def main() -> None:
    frame = pd.read_parquet(PATHS.data_processed / "employees_features.parquet")
    X = frame.drop(columns=[TARGET])
    y = frame[TARGET].astype(int)
    groups = make_feature_groups(frame, target=TARGET)

    per_fold: dict[str, pd.DataFrame] = {}
    out_of_fold: dict[str, pd.DataFrame] = {}
    summary: dict = {"arms": {}}

    for arm in ARMS:
        folds, oof = evaluate_cv(
            X,
            y,
            lambda: make_logreg(groups),
            params=FINAL_MODEL_PARAMS,
            config=ProtocolConfig(calibration=arm),
        )
        _table, scores = reliability(oof)
        per_fold[arm] = folds.assign(arm=arm)
        out_of_fold[arm] = oof
        summary["arms"][arm] = {**summarise(folds), "calibration": scores}

    config = ProtocolConfig()
    summary["protocol"] = {
        "n_splits": config.n_splits,
        "n_repeats": config.n_repeats,
        "seed": config.seed,
        "target_recall": config.target_recall,
        "n_rows": len(y),
        "prevalence": float(y.mean()),
        "shipped_arm": SHIPPED_ARM,
        "shipped_cost_ratio": SHIPPED_RATIO,
    }

    baseline = _single_split_baseline(X, y, frame)
    summary["single_split"] = baseline
    summary["single_split_ap_percentile"] = float(
        (per_fold["none"]["average_precision"] < baseline["average_precision"]).mean()
    )

    PATHS.reports.mkdir(parents=True, exist_ok=True)
    pd.concat(per_fold.values(), ignore_index=True).to_csv(
        PATHS.reports / "evaluation_cv.csv", index=False
    )

    reliability_tables = []
    for arm in ARMS:
        table, _scores = reliability(out_of_fold[arm])
        reliability_tables.append(table.assign(arm=arm))
    pd.concat(reliability_tables, ignore_index=True).to_csv(
        PATHS.reports / "calibration.csv", index=False
    )

    # The cost curve is read on the scale that will be served: a threshold taken from one
    # probability scale does not transfer to another.
    # The three model families, same folds, no calibration and no tuning: this is the
    # comparison the notebook asserted in prose.
    baseline_rows = []
    for name, factory in BASELINES.items():
        params = FINAL_MODEL_PARAMS if name == "logreg" else None
        folds, _oof = evaluate_cv(
            X, y, lambda f=factory: f(groups), params=params, config=ProtocolConfig()
        )
        baseline_rows.append({"model": name, **summarise(folds)})
    baselines = pd.DataFrame(baseline_rows)
    baselines.to_csv(PATHS.reports / "baselines.csv", index=False)

    curve = cost_curve(out_of_fold[SHIPPED_ARM], ratios=COST_RATIOS)
    curve.to_csv(PATHS.reports / "cost_curve.csv", index=False)

    shipped_threshold = float(curve.loc[curve["ratio"] == SHIPPED_RATIO, "threshold_mean"].iloc[0])
    summary["shipped_threshold"] = shipped_threshold

    available = [c for c in SUBGROUP_COLUMNS if c in X.columns]
    subgroups = subgroup_rates(out_of_fold[SHIPPED_ARM], X, available, threshold=shipped_threshold)
    subgroups.to_csv(PATHS.reports / "subgroups.csv", index=False)

    (PATHS.reports / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    raw = summary["arms"]["none"]
    shipped = summary["arms"][SHIPPED_ARM]
    print(
        f"{raw['n_folds']} folds over {raw['n_rows_scored']:,} scored rows "
        f"({raw['n_positive_scored']} departures)\n"
    )
    print(f"{'arm':>10} {'AP':>16} {'ROC AUC':>16} {'Brier':>8} {'ECE':>8} {'mean p':>8}")
    for arm in ARMS:
        block = summary["arms"][arm]
        print(
            f"{arm:>10} {block['average_precision_mean']:>8.3f} "
            f"+/-{block['average_precision_sd']:<5.3f} "
            f"{block['roc_auc_mean']:>8.3f} +/-{block['roc_auc_sd']:<5.3f} "
            f"{block['calibration']['brier']:>8.4f} {block['calibration']['ece']:>8.4f} "
            f"{block['calibration']['mean_predicted']:>8.3f}"
        )
    print(f"\nbase rate {raw['calibration']['base_rate']:.3f}")
    print(
        f"recall at the chosen threshold {raw['recall_mean']:.3f} +/- {raw['recall_sd']:.3f}, "
        f"aimed at {config.target_recall:.2f} (optimism {raw['recall_optimism']:+.3f})"
    )
    print(
        f"the published 90/10 split gave AP {baseline['average_precision']:.3f} — "
        f"above {summary['single_split_ap_percentile']:.0%} of the folds"
    )
    print(f"\n{'model':>14} {'AP':>16} {'ROC AUC':>16} {'recall':>8}")
    for row in baselines.itertuples():
        print(
            f"{row.model:>14} {row.average_precision_mean:>8.3f} "
            f"+/-{row.average_precision_sd:<5.3f} {row.roc_auc_mean:>8.3f} "
            f"+/-{row.roc_auc_sd:<5.3f} {row.recall_mean:>8.3f}"
        )
    print(
        f"\nshipping the '{SHIPPED_ARM}' arm at cost ratio {SHIPPED_RATIO}: "
        f"threshold {shipped_threshold:.3f}, "
        f"AP {shipped['average_precision_mean']:.3f}, "
        f"ECE {shipped['calibration']['ece']:.4f}"
    )
    for path in (
        "evaluation_cv.csv",
        "evaluation_summary.json",
        "baselines.csv",
        "cost_curve.csv",
        "calibration.csv",
        "subgroups.csv",
    ):
        print(f"  [ok] reports/{path}")


if __name__ == "__main__":
    main()
