"""The pieces between the extracts and the model: cleaning, derived columns, grouping.

Each of these had no test. Two of them decide what the model sees — which column is
log-transformed, which is one-hot encoded — and one of them, the incoherence count, is
published in the data dossier.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from attrition_serving.data.features import add_engineered_features, compute_incoherence_metrics
from attrition_serving.preprocessing import (
    build_preprocessor,
    keep_existing,
    make_feature_groups,
)


@pytest.fixture()
def frame() -> pd.DataFrame:
    """Twelve rows shaped like the joined extracts, with the columns the grouping names."""
    rng = np.random.default_rng(7)
    n = 12
    return pd.DataFrame(
        {
            "a_quitte_l_entreprise": ["Oui", "Non"] * (n // 2),
            "age": rng.integers(22, 58, n),
            "genre": ["F", "M"] * (n // 2),
            "revenu_mensuel": rng.integers(1500, 18000, n),
            "statut_marital": ["Célibataire", "Marié(e)", "Divorcé(e)"] * (n // 3),
            "departement": ["Commercial", "Consulting"] * (n // 2),
            "poste": ["Consultant", "Manager"] * (n // 2),
            "domaine_etude": ["Marketing", "Autre"] * (n // 2),
            "heure_supplementaires": ["Oui", "Non"] * (n // 2),
            "nombre_experiences_precedentes": rng.integers(0, 6, n),
            "nombre_heures_travailless": [80] * n,
            "ayant_enfants": ["Y"] * n,
            "annee_experience_totale": rng.integers(5, 30, n),
            "annees_dans_l_entreprise": rng.integers(1, 5, n),
            "annees_dans_le_poste_actuel": rng.integers(0, 2, n),
            "annees_depuis_la_derniere_promotion": rng.integers(0, 4, n),
            "annes_sous_responsable_actuel": rng.integers(0, 4, n),
            "distance_domicile_travail": rng.integers(1, 25, n),
            "niveau_education": rng.integers(1, 6, n),
            "niveau_hierarchique_poste": rng.integers(1, 5, n),
            "satisfaction_employee_environnement": rng.integers(1, 5, n),
            "satisfaction_employee_nature_travail": rng.integers(1, 5, n),
            "satisfaction_employee_equipe": rng.integers(1, 5, n),
            "satisfaction_employee_equilibre_pro_perso": rng.integers(1, 5, n),
            "note_evaluation_precedente": rng.integers(1, 5, n),
            "note_evaluation_actuelle": rng.integers(3, 5, n),
            "nombre_participation_pee": rng.integers(0, 4, n),
            "nb_formations_suivies": rng.integers(0, 7, n),
            "frequence_deplacement": ["Occasionnel", "Frequent"] * (n // 2),
        }
    )


def test_the_target_and_the_overtime_flag_become_integers(frame: pd.DataFrame) -> None:
    out = add_engineered_features(frame)

    assert set(out["a_quitte_l_entreprise"].dropna().unique()) <= {0, 1}
    assert set(out["heure_supplementaires"].dropna().unique()) <= {0, 1}


def test_a_column_that_never_varies_is_dropped(frame: pd.DataFrame) -> None:
    """`StandardHours` is 80 for all 1 470 rows: one-hot encoding it adds a column of ones."""
    out = add_engineered_features(frame)

    assert "nombre_heures_travailless" not in out.columns
    assert "ayant_enfants" not in out.columns


def test_a_move_between_roles_is_derived_from_the_two_tenures(frame: pd.DataFrame) -> None:
    out = add_engineered_features(frame)

    assert "changement_poste" in out.columns
    expected = (frame["annees_dans_l_entreprise"] > frame["annees_dans_le_poste_actuel"]).astype(
        int
    )
    assert list(out["changement_poste"]) == list(expected)


def test_gender_is_mapped_only_when_the_source_has_not_done_it(frame: pd.DataFrame) -> None:
    already = frame.assign(genre=[0, 1] * 6)

    assert set(add_engineered_features(frame)["genre"].unique()) == {0, 1}
    assert list(add_engineered_features(already)["genre"]) == list(already["genre"])


def test_a_career_that_contradicts_itself_is_counted_and_not_repaired() -> None:
    """Total experience below tenure cannot happen; the dossier publishes how often it does."""
    frame = pd.DataFrame(
        {
            "annee_experience_totale": [10, 2, 8],
            "annees_dans_l_entreprise": [5, 6, 8],
            "annees_dans_le_poste_actuel": [2, 1, 8],
            "nombre_experiences_precedentes": [1, 0, 0],
        }
    )

    metrics = compute_incoherence_metrics(frame)

    assert metrics["incoherence_hierarchy_count"] == 1.0
    assert metrics["incoherence_hierarchy_ratio"] == pytest.approx(1 / 3)


def test_the_gap_is_not_reported_when_no_row_qualifies() -> None:
    frame = pd.DataFrame(
        {
            "annee_experience_totale": [10, 12],
            "annees_dans_l_entreprise": [5, 6],
            "nombre_experiences_precedentes": [1, 2],
        }
    )

    assert np.isnan(compute_incoherence_metrics(frame)["gap_exp_minus_tenure_when_no_prev_ratio"])


def test_a_frame_missing_the_columns_gets_no_metric() -> None:
    assert compute_incoherence_metrics(pd.DataFrame({"age": [30]})) == {}


def test_grouping_keeps_only_the_columns_the_frame_has() -> None:
    assert keep_existing(["age", "absent"], {"age", "genre"}) == ["age"]


def test_every_grouped_column_exists_and_no_column_is_grouped_twice(frame: pd.DataFrame) -> None:
    prepared = add_engineered_features(frame)
    groups = make_feature_groups(prepared, target="a_quitte_l_entreprise")

    listed = (
        groups.num_cont
        + groups.num_log
        + groups.num_disc
        + groups.bin_cols
        + groups.cat_nom
        + groups.cat_ord
    )
    assert set(listed) <= set(prepared.columns)
    assert len(listed) == len(set(listed))
    assert len(groups.ord_categories) == len(groups.cat_ord)


def test_the_preprocessor_turns_the_frame_into_a_numeric_matrix(frame: pd.DataFrame) -> None:
    prepared = add_engineered_features(frame)
    groups = make_feature_groups(prepared, target="a_quitte_l_entreprise")
    X = prepared.drop(columns=["a_quitte_l_entreprise"])

    matrix = build_preprocessor(groups).fit_transform(X)

    dense = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)
    assert dense.shape[0] == len(X)
    assert np.isfinite(dense).all()


def test_the_log_transform_survives_a_zero(frame: pd.DataFrame) -> None:
    """Tenure is zero for a new joiner, and `log` of zero would take the whole column out."""
    prepared = add_engineered_features(frame.assign(annees_dans_l_entreprise=0))
    groups = make_feature_groups(prepared, target="a_quitte_l_entreprise")
    X = prepared.drop(columns=["a_quitte_l_entreprise"])

    matrix = build_preprocessor(groups).fit_transform(X)

    dense = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)
    assert np.isfinite(dense).all()
