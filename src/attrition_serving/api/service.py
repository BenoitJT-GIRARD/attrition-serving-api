from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, Tuple

import joblib
import pandas as pd

from attrition_serving.api.settings import get_config


@lru_cache
def get_expected_features() -> list[str]:
    cfg = get_config()
    data = json.loads(cfg.expected_features_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise ValueError("expected_features.json invalide (doit être une liste de strings)")
    return data


@lru_cache
def load_pipeline():
    cfg = get_config()
    if not cfg.pipeline_path.exists():
        raise FileNotFoundError(f"Pipeline introuvable: {cfg.pipeline_path}")
    return joblib.load(cfg.pipeline_path)


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise quelques champs sensibles pour éviter les erreurs de dtype.
    Objectif: accepter des entrées humaines (M/F, Oui/Non) tout en nourrissant
    le pipeline avec les mêmes types que l'entraînement.
    """
    p = dict(payload)

    # genre: attendu 0/1 dans ton sample (0=femme, 1=homme) -> on accepte M/F aussi
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

    # heure_supplementaires: attendu 0/1 dans ton sample -> on accepte Oui/Non/True/False
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

    # augmentation salaire: dans ton sample c'est une STRING type "11 %"
    # -> on accepte aussi 11 ou 0.11 et on convertit en "11 %"
    if "augementation_salaire_precedente" in p:
        a = p["augementation_salaire_precedente"]
        if isinstance(a, (int, float)):
            # si 0.11 -> 11%
            val = a * 100 if 0 < a < 1 else a
            p["augementation_salaire_precedente"] = f"{int(round(val))} %"
        elif isinstance(a, str):
            s = a.strip()
            # normalise "11%" -> "11 %"
            if s.endswith("%") and not s.endswith(" %"):
                s = s[:-1].strip() + " %"
            p["augementation_salaire_precedente"] = s

    return p


def check_payload(payload: Dict[str, Any]) -> Tuple[list[str], list[str]]:
    """
    Vérifie que:
    - toutes les features attendues sont présentes
    - aucune n'est None
    """
    expected = get_expected_features()
    missing = [f for f in expected if f not in payload]
    nulls = [f for f in expected if f in payload and payload[f] is None]
    return missing, nulls


def align_features(payload: Dict[str, Any]) -> pd.DataFrame:
    expected = get_expected_features()
    aligned = {f: payload.get(f, None) for f in expected}
    return pd.DataFrame([aligned], columns=expected)


def predict_proba(payload: Dict[str, Any]) -> float:
    pipe = load_pipeline()
    X = align_features(payload)
    proba = float(pipe.predict_proba(X)[:, 1][0])
    return proba


def decide(proba: float) -> int:
    cfg = get_config()
    return int(proba >= cfg.model_threshold)
