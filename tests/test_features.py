import pandas as pd

from attrition_serving.features import add_engineered_features


def test_add_engineered_features_basic():
    df = pd.DataFrame(
        {
            "a_quitte_l_entreprise": ["oui", "non"],
            "heure_supplementaires": ["non", "oui"],
            "augmentation_salaire_precedente": ["15%", "0.10"],
            "annees_dans_l_entreprise": [5, 2],
            "annees_dans_le_poste_actuel": [1, 2],
            "age": [30, 40],
            "annee_experience_totale": [5, 15],
            "note_evaluation_actuelle": [4, 3],
            "note_evaluation_precedente": [3, 3],
            "nombre_experiences_precedentes": [1, 2],
        }
    )
    out = add_engineered_features(df)
    assert out["a_quitte_l_entreprise"].tolist() == [1, 0]
    assert out["heure_supplementaires"].tolist() == [0, 1]
    assert float(out["augmentation_salaire_precedente"].iloc[0]) == 0.15
    assert "changement_poste" in out.columns
    assert "evolution_note" in out.columns
