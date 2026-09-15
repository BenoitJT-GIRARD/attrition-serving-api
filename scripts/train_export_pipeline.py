"""Fit the model that ships, and write the card that describes it.

    uv run python scripts/run_evaluation.py        # first: what the model is worth
    uv run python scripts/train_export_pipeline.py # then: the artefact and its card

The order matters. This script does not measure anything — `scripts/run_evaluation.py` does,
by repeated cross-validation, and this one reads its summary to learn which calibration arm
and which threshold were chosen. Splitting them is what stops a number from being produced
by the same pass that selects it.

Two things changed here after the audit.

**The model is calibrated.** `class_weight="balanced"` makes the raw scores rank well and
lie: mean predicted 0.375 against a base rate of 0.161. The service returns that number as
`proba_depart` and writes it to PostgreSQL under that name, so it has to be a probability.
Isotonic cross-fitted over the training data brings expected calibration error from 0.214 to
0.015. It costs average precision — 0.607 to 0.569 — because isotonic is a step function and
ties are what average precision penalises; ROC AUC barely moves, 0.823 to 0.820, which is how
you can tell the ordering survived.

**The model is fitted on all the data.** The evaluation is the cross-validation; holding
10% back from the shipped model would only make it worse at the job it is shipped to do. The
rows in `tests/fixtures/` are request-shape fixtures for the API tests, not an
evaluation set, and they are in-sample by construction.
"""

from __future__ import annotations

import json

import joblib
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV

from attrition_serving.config import (
    FINAL_MODEL_PARAMS,
    PATHS,
)
from attrition_serving.modeling.models import make_logreg
from attrition_serving.preprocessing import make_feature_groups
from attrition_serving.utils.paths import TESTS_DIR

TARGET = "a_quitte_l_entreprise"


def main() -> None:
    summary_path = PATHS.reports / "evaluation_summary.json"
    if not summary_path.exists():
        raise SystemExit(
            f"{summary_path} is missing. Run `uv run python scripts/run_evaluation.py` first: "
            "the threshold and the calibration arm are chosen there, not here."
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    arm = summary["protocol"]["shipped_arm"]
    ratio = summary["protocol"]["shipped_cost_ratio"]
    threshold = float(summary["shipped_threshold"])
    measured = summary["arms"][arm]

    df = pd.read_parquet(PATHS.data_processed / "employees_features.parquet")
    X = df.drop(columns=[TARGET])
    y = df[TARGET].astype(int)

    groups = make_feature_groups(df, target=TARGET)
    pipeline = make_logreg(groups)
    pipeline.set_params(**FINAL_MODEL_PARAMS)
    if arm == "crossfit":
        pipeline = CalibratedClassifierCV(pipeline, method="isotonic", cv=5, ensemble=False)
    elif arm != "none":
        raise SystemExit(f"the shipped arm must be 'none' or 'crossfit', got {arm!r}")
    pipeline.fit(X, y)

    PATHS.models.mkdir(parents=True, exist_ok=True)
    PATHS.reports.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, PATHS.models / "pipeline.joblib")

    # What the API requires is what the model consumes -- not every column that happened
    # to be in the training frame. The previous list was `X.columns`, so a caller had to
    # send the anonymised employee id and both join keys to get a prediction, and the
    # pipeline dropped all three. Five required fields did nothing, one of them an
    # identifier the service has no reason to ask for.
    expected_features = [
        *groups.num_cont,
        *groups.num_log,
        *groups.num_disc,
        *groups.bin_cols,
        *groups.cat_nom,
        *groups.cat_ord,
    ]
    unused = sorted(set(X.columns) - set(expected_features))
    (PATHS.models / "expected_features.json").write_text(
        json.dumps(expected_features, indent=2), encoding="utf-8"
    )

    # Request-shape fixtures for the API tests. In-sample, and labelled as such: they
    # exercise the request path, they do not measure anything.
    fixtures_dir = TESTS_DIR / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    X.head(10).to_json(fixtures_dir / "employees_sample.json", orient="records")
    y.head(10).to_json(fixtures_dir / "employees_sample_labels.json", orient="records")

    model_card = {
        "target": TARGET,
        "model_type": "logistic_regression",
        "calibration": arm,
        "final_params": FINAL_MODEL_PARAMS,
        "default_threshold": threshold,
        "threshold_cost_ratio": ratio,
        "threshold_rationale": (
            f"expected-cost optimum when one missed departure is worth {ratio} unnecessary "
            "retention conversations; see reports/cost_curve.csv for the other ratios"
        ),
        "n_fitted_on": len(y),
        "prevalence": float(y.mean()),
        "expected_n_features_raw": len(expected_features),
        # Columns present in the training frame that the pipeline does not read. Recorded
        # rather than left implicit: `augementation_salaire_precedente` is one of them, and
        # a salary-increase variable being silently absent from an attrition model is worth
        # a reader knowing.
        "columns_not_consumed": unused,
        # Measured by cross-validation in scripts/run_evaluation.py, not here. The previous
        # card carried metrics from the same 90/10 split the model was fitted on.
        "evaluation": {
            "protocol": f"{summary['protocol']['n_splits']}x{summary['protocol']['n_repeats']} "
            "repeated stratified cross-validation",
            "average_precision": round(measured["average_precision_mean"], 4),
            "average_precision_sd": round(measured["average_precision_sd"], 4),
            "roc_auc": round(measured["roc_auc_mean"], 4),
            "roc_auc_sd": round(measured["roc_auc_sd"], 4),
            "ece": round(measured["calibration"]["ece"], 4),
            "brier": round(measured["calibration"]["brier"], 4),
        },
        # A scikit-learn pickle is only readable by a compatible scikit-learn, and it names
        # the module that defined its transformers. Versioning the artefact without
        # versioning what reads it is versioning a file, not a model.
        "sklearn_version": sklearn.__version__,
    }
    (PATHS.models / "model_card.json").write_text(
        json.dumps(model_card, indent=2), encoding="utf-8"
    )

    print(f"Exported the '{arm}' model, fitted on {len(y):,} rows.")
    print(f"  threshold {threshold:.3f}, chosen at cost ratio {ratio}")
    print(
        f"  {len(expected_features)} features required by the API; {len(unused)} columns "
        f"in the frame are not consumed: {', '.join(unused)}"
    )
    print(
        f"  cross-validated AP {measured['average_precision_mean']:.3f} "
        f"+/- {measured['average_precision_sd']:.3f}, ECE {measured['calibration']['ece']:.4f}"
    )
    for path in ("pipeline.joblib", "model_card.json", "expected_features.json"):
        print(f"  [ok] models/{path}")


if __name__ == "__main__":
    main()
