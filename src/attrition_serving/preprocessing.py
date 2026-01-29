from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
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
            (
                "ord",
                OrdinalEncoder(
                    categories=groups.ord_categories,
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                ),
            ),
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


def keep_existing(cols: list[str], X_columns: set[str]) -> list[str]:
    """Return only columns that exist in X."""
    return [c for c in cols if c in X_columns]


def make_feature_groups(df: pd.DataFrame, target: str) -> FeatureGroups:
    """
    Build FeatureGroups using the project-defined column lists,
    automatically filtering out missing columns.

    This function is the single source of truth for feature grouping
    used by training/export and serving.
    """
    X = df.drop(columns=[target])
    X_cols = set(X.columns)

    # === Numériques continues ===
    num_cont = [
        "age",
        "augmentation_salaire_precedente",
        "distance_domicile_travail",
        "proba_chgt_experience_par_an",
        "proba_chgt_experience_par_an_adulte",
        "ratio_experience_vie_adulte",
    ]

    # === Numériques à log-transform ===
    num_log = [
        "revenu_mensuel",
        "annee_experience_totale",
        "annees_dans_l_entreprise",
        "annees_dans_le_poste_actuel",
        "annes_sous_responsable_actuel",
        "annees_depuis_la_derniere_promotion",
    ]

    # === Numériques discrètes ===
    num_disc = [
        "nombre_participation_pee",
        "nb_formations_suivies",
        "nombre_employee_sous_responsabilite",
        "nombre_experiences_precedentes",
        "nombre_experiences_precedents",  # tolère l'ancienne colonne si présente
    ]

    # === Binaires ===
    bin_cols = ["genre", "heure_supplementaires", "changement_poste"]

    # === Catégorielles nominales ===
    cat_nom = ["statut_marital", "departement", "poste", "domaine_etude"]

    # === Ordinales ===
    cat_ord = [
        "satisfaction_employee_environnement",
        "satisfaction_employee_nature_travail",
        "satisfaction_employee_equipe",
        "satisfaction_employee_equilibre_pro_perso",
        "note_evaluation_precedente",
        "note_evaluation_actuelle",
        "niveau_hierarchique_poste",
        "niveau_education",
        "frequence_deplacement",
        "evolution_note",
    ]

    # Filtrage automatique : on ne garde que les colonnes présentes
    num_cont = keep_existing(num_cont, X_cols)
    num_log = keep_existing(num_log, X_cols)
    num_disc = keep_existing(num_disc, X_cols)
    bin_cols = keep_existing(bin_cols, X_cols)
    cat_nom = keep_existing(cat_nom, X_cols)
    cat_ord = keep_existing(cat_ord, X_cols)

    # Ordres ordinal : version simple = tri des valeurs uniques
    # (tu pourras mettre un ordre métier explicite plus tard si besoin)
    ord_categories = [sorted(df[c].dropna().unique().tolist()) for c in cat_ord]

    return FeatureGroups(
        num_cont=num_cont,
        num_log=num_log,
        num_disc=num_disc,
        bin_cols=bin_cols,
        cat_nom=cat_nom,
        cat_ord=cat_ord,
        ord_categories=ord_categories,
    )
