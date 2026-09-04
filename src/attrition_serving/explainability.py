from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sklearn.inspection import permutation_importance


def permutation_importance_df(
    pipeline,
    X_test,
    y_test,
    scoring: str = "average_precision",
    n_repeats: int = 20,
    random_state: int = 42,
) -> pd.DataFrame:
    """Permutation importance over the *original* columns, before encoding.

    Measured on the raw columns rather than the encoded ones on purpose: one-hot turns a
    department into eight indicators, and eight small importances say much less to a reader
    than one column named "department".
    """
    r = permutation_importance(
        pipeline,
        X_test,
        y_test,
        scoring=scoring,
        n_repeats=n_repeats,
        random_state=random_state,
        n_jobs=-1,
    )
    df = pd.DataFrame(
        {
            "feature": X_test.columns,
            "importance_mean": r.importances_mean,
            "importance_std": r.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)
    return df


def get_transformed_feature_names(pipeline) -> np.ndarray:
    pre = pipeline.named_steps["preprocess"]
    return pre.get_feature_names_out()


def transform_X(pipeline, X):
    pre = pipeline.named_steps["preprocess"]
    return pre.transform(X)


def shap_explain_tree_model(pipeline, X_background, X_explain):
    """SHAP for tree models, on the features *after* preprocessing.

    The tree explainer needs the matrix the model actually splits on, so unlike permutation
    importance above, this one speaks in encoded feature names.
    """
    model = pipeline.named_steps["model"]
    Xb = transform_X(pipeline, X_background)
    Xe = transform_X(pipeline, X_explain)

    # TreeExplainer
    explainer = shap.TreeExplainer(model, data=Xb)
    shap_values = explainer.shap_values(Xe)

    feature_names = get_transformed_feature_names(pipeline)
    return explainer, shap_values, Xe, feature_names


def shap_explain_linear_model(pipeline, X_background, X_explain):
    """SHAP for the logistic regression, on the features after preprocessing.

    For a linear model the SHAP value of a feature is its coefficient times its centred
    value, so this is the coefficient view with the scaling put back in.
    """
    model = pipeline.named_steps["model"]
    Xb = transform_X(pipeline, X_background)
    Xe = transform_X(pipeline, X_explain)

    explainer = shap.LinearExplainer(model, Xb)
    shap_values = explainer.shap_values(Xe)

    feature_names = get_transformed_feature_names(pipeline)
    return explainer, shap_values, Xe, feature_names
