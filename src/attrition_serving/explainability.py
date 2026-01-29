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
    """
    Permutation importance au niveau des FEATURES ORIGINALES (avant encodage),
    ce qui est souvent le plus lisible pour une audience métier.
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
    """
    SHAP pour modèles arbres (RandomForest / GBM) :
    on explique le modèle sur les features APRÈS preprocessing.
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
    """
    SHAP pour régression logistique :
    LinearExplainer sur les features APRÈS preprocessing.
    """
    model = pipeline.named_steps["model"]
    Xb = transform_X(pipeline, X_background)
    Xe = transform_X(pipeline, X_explain)

    explainer = shap.LinearExplainer(model, Xb)
    shap_values = explainer.shap_values(Xe)

    feature_names = get_transformed_feature_names(pipeline)
    return explainer, shap_values, Xe, feature_names
