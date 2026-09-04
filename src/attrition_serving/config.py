"""Paths, seeds and the one place the final model's hyper-parameters are written down.

The threshold is deliberately absent. It lives in `models/model_card.json`, written by the
export and read by `api/settings.py`, because a second place to write it is a second place
for it to disagree with itself -- which is exactly how this service came to decide at 0.5
while every published figure said otherwise.
"""

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
    "model__l1_ratio": 0.0,  # L2, spelled the way scikit-learn 1.8 asks for it
}
