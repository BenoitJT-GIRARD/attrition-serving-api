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
