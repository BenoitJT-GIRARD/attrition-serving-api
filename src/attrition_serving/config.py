from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present (never committed)
load_dotenv(override=False)


@dataclass(frozen=True)
class Paths:
    root: Path = Path(__file__).resolve().parents[2]
    data_raw: Path = root / "data" / "raw"
    data_processed: Path = root / "data" / "processed"
    reports: Path = root / "reports"
    models: Path = root / "models"


@dataclass(frozen=True)
class Settings:
    random_state: int
    anonymization_key: str | None


PATHS = Paths()
SETTINGS = Settings(
    random_state=int(os.getenv("RANDOM_STATE", "42")),
    anonymization_key=os.getenv("ANONYMIZATION_KEY"),
)
FINAL_MODEL_PARAMS = {
    "model__C": 0.1,
    "model__l1_ratio": 0.0,  # équivalent L2 selon warning sklearn>=1.8
}


def _get_model_threshold(default: float = 0.5) -> float:
    """
    Threshold used to convert predicted probability into class.
    Priority:
    1) .env variable MODEL_THRESHOLD
    2) fallback to default
    """
    raw = os.getenv("MODEL_THRESHOLD")
    if raw is None:
        return default

    try:
        thr = float(raw)
    except ValueError:
        raise ValueError(f"MODEL_THRESHOLD must be a float, got '{raw}'")

    if not (0.0 < thr < 1.0):
        raise ValueError(f"MODEL_THRESHOLD must be in (0,1), got {thr}")

    return thr


FINAL_MODEL_THRESHOLD = _get_model_threshold(default=0.32)  # exemple : seuil pour recall=0.80
