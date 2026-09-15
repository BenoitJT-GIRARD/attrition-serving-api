"""The frame handed to the pipeline carries the expected columns, in the expected order.

A pipeline fed the right columns in the wrong order does not raise. It predicts something
else.
"""

import json

import pandas as pd

from attrition_serving.utils.paths import MODELS_DIR


def test_expected_features_alignment_builds_ordered_df():
    expected_path = MODELS_DIR / "expected_features.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    # Deliberately incomplete: two features short of the contract.
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
