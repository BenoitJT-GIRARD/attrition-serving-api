import json
from pathlib import Path

import pandas as pd


def test_expected_features_alignment_builds_ordered_df():
    expected_path = Path("models/expected_features.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    # payload incomplet exprès
    payload = {
        "age": 35,
        "genre": "M",
        "revenu_mensuel": 5000,
    }

    # build the frame the way the API is supposed to
    row = {f: payload.get(f, None) for f in expected}
    X = pd.DataFrame([row])[expected]

    assert list(X.columns) == expected
    assert X.loc[0, "age"] == 35
    assert "statut_marital" in X.columns
    assert pd.isna(X.loc[0, "statut_marital"]) or X.loc[0, "statut_marital"] is None
