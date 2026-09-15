"""Between the payload and the model: normalise, check, align, score, decide.

`check_payload` names every missing field at once rather than one per round trip, because a
caller assembling thirty-two features should not need thirty-two requests to learn what is
missing.

`align_features` reads `models/expected_features.json` and hands the pipeline the columns
it was fitted on, in that order. The contract used to demand five fields the model never
consumed -- two join keys, the anonymised id, and the previous pay rise -- and the service
carefully normalised one of them on the way in. A pipeline fed columns in another order
does not complain; it predicts something else.

`decide` is one line, and it is the line the whole service exists to run.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import joblib
import pandas as pd

from attrition_serving.api.settings import get_config


@lru_cache
def get_expected_features() -> list[str]:
    cfg = get_config()
    data = json.loads(cfg.expected_features_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise ValueError("expected_features.json must hold a list of column names")
    return data


@lru_cache
def load_pipeline():
    cfg = get_config()
    if not cfg.pipeline_path.exists():
        raise FileNotFoundError(f"no model artefact at {cfg.pipeline_path}")
    return joblib.load(cfg.pipeline_path)


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Accept the shapes a human or another system actually sends -- "M", "Oui", "11%" --
    and hand the pipeline the dtypes it was trained on. Without this the model receives a
    string where it learned a number, and scikit-learn's error names a column, not a cause.
    """
    p = dict(payload)

    # gender: 0/1 in the training data. Letters are accepted and mapped.
    if "genre" in p:
        g = p["genre"]
        if isinstance(g, str):
            gs = g.strip().upper()
            if gs in {"M", "H", "HOMME", "MALE", "1"}:
                p["genre"] = 1
            elif gs in {"F", "FEMME", "FEMALE", "0"}:
                p["genre"] = 0
        elif isinstance(g, bool):
            p["genre"] = int(g)

    # overtime: 0/1 in the training data. Yes/no, in either language, is accepted.
    if "heure_supplementaires" in p:
        hs = p["heure_supplementaires"]
        if isinstance(hs, str):
            hss = hs.strip().lower()
            if hss in {"oui", "yes", "true", "1"}:
                p["heure_supplementaires"] = 1
            elif hss in {"non", "no", "false", "0"}:
                p["heure_supplementaires"] = 0
        elif isinstance(hs, bool):
            p["heure_supplementaires"] = int(hs)

    return p


def check_payload(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    """
    Report what a payload is missing: absent features, and present-but-null ones.

    Returned rather than raised, so the caller can put both lists in one 422 instead of
    making the client discover them one request at a time.
    """
    expected = get_expected_features()
    missing = [f for f in expected if f not in payload]
    nulls = [f for f in expected if f in payload and payload[f] is None]
    return missing, nulls


def align_features(payload: dict[str, Any]) -> pd.DataFrame:
    expected = get_expected_features()
    aligned = {f: payload.get(f, None) for f in expected}
    return pd.DataFrame([aligned], columns=expected)


def predict_proba(payload: dict[str, Any]) -> float:
    pipe = load_pipeline()
    X = align_features(payload)
    proba = float(pipe.predict_proba(X)[:, 1][0])
    return proba


def decide(proba: float) -> int:
    cfg = get_config()
    return int(proba >= cfg.model_threshold)
