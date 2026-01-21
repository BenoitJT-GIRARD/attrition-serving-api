from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]  # racine repo (ajuste si besoin)
MODELS_DIR = ROOT / "models"


def load_env(default_env_file: str = ".env.local") -> None:
    """
    Charge d'abord .env (commun), puis un override (local/supabase) si présent.
    Pourquoi: séparer config commune vs secrets d'environnement.
    """
    load_dotenv(ROOT / ".env", override=False)
    env_file = os.getenv("ENV_FILE", default_env_file)
    load_dotenv(ROOT / env_file, override=True)


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    database_url: str
    model_threshold: float
    model_version: str
    expected_features_path: Path
    pipeline_path: Path
    model_card_path: Path


@lru_cache
def get_config() -> AppConfig:
    load_env()

    model_card_path = MODELS_DIR / "model_card.json"
    expected_features_path = MODELS_DIR / "expected_features.json"
    pipeline_path = MODELS_DIR / "pipeline.joblib"

    model_card = {}
    if model_card_path.exists():
        model_card = json.loads(model_card_path.read_text(encoding="utf-8"))

    api_key = os.getenv("API_KEY", "")
    database_url = os.getenv("DATABASE_URL", "")

    # seuil: env > model_card > 0.5
    threshold = os.getenv("MODEL_THRESHOLD")
    if threshold is None or threshold == "":
        threshold = model_card.get("threshold_default", 0.5)
    threshold = float(threshold)

    # version: env > model_card > "dev"
    model_version = os.getenv("MODEL_VERSION") or model_card.get("model_version", "dev")

    if not database_url:
        raise RuntimeError("DATABASE_URL manquant (vérifie .env.local ou .env.supabase)")

    return AppConfig(
        api_key=api_key,
        database_url=database_url,
        model_threshold=threshold,
        model_version=model_version,
        expected_features_path=expected_features_path,
        pipeline_path=pipeline_path,
        model_card_path=model_card_path,
    )
