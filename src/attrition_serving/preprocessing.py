from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, OrdinalEncoder, StandardScaler


@dataclass(frozen=True)
class FeatureGroups:
    # Numériques continues (avec log sur certaines)
    num_cont: list[str]
    num_log: list[str]

    # Numériques discrètes
    num_disc: list[str]

    # Binaires 0/1
    bin_cols: list[str]

    # Catégorielles nominales
    cat_nom: list[str]

    # Ordinales (on garde le sens)
    cat_ord: list[str]
    ord_categories: list[list]  # même longueur que cat_ord


def _log1p_safe(X):
    # X arrive en array 2D
    X = np.asarray(X, dtype=float)
    # évite log sur négatifs : on clip à 0 (au pire on documente la décision)
    X = np.clip(X, a_min=0, a_max=None)
    return np.log1p(X)


def build_preprocessor(groups: FeatureGroups) -> ColumnTransformer:
    num_cont_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    num_log_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("log", FunctionTransformer(_log1p_safe, feature_names_out="one-to-one")),
            ("scaler", StandardScaler()),
        ]
    )

    num_disc_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    bin_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("scaler", StandardScaler()),
        ]
    )

    cat_nom_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(drop="first", handle_unknown="ignore")),
        ]
    )

    cat_ord_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("ord", OrdinalEncoder(categories=groups.ord_categories)),
            ("scaler", StandardScaler()),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num_cont", num_cont_pipe, groups.num_cont),
            ("num_log", num_log_pipe, groups.num_log),
            ("num_disc", num_disc_pipe, groups.num_disc),
            ("bin", bin_pipe, groups.bin_cols),
            ("cat_nom", cat_nom_pipe, groups.cat_nom),
            ("cat_ord", cat_ord_pipe, groups.cat_ord),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return preprocessor
