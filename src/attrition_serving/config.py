"""Seeds, the anonymisation key, and the one place the final model's hyper-parameters live.

The threshold is deliberately absent. It lives in `models/model_card.json`, written by the
export and read by `api/settings.py`, because a second place to write it is a second place
for it to disagree with itself -- which is exactly how this service came to decide at 0.5
while every published figure said otherwise.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from attrition_serving.env import load_env
from attrition_serving.utils.paths import (
    DATA_DIR,
    MODELS_DIR,
    REPORTS_DIR,
    ROOT_DIR,
)

load_env()

#: Where the extracts live. `ATTRITION_DATA_DIR` moves them off the repository tree, which is
#: what the author's own checkout does: the tree sits on a synchronised drive, and a dataset
#: inside it is a dataset one careless `git add -A` away from being published.
#: `docs/data-source.md` says what belongs there and how to rebuild it.
_env_data_dir = os.environ.get("ATTRITION_DATA_DIR", "").strip()
_data_dir: Path = Path(_env_data_dir) if _env_data_dir else DATA_DIR


@dataclass(frozen=True)
class Paths:
    """The named directories this project reads and writes.

    They hang off `utils.paths`, which finds the root once. Nothing else computes one.
    """

    root: Path = ROOT_DIR
    data_raw: Path = _data_dir / "raw"
    data_processed: Path = _data_dir / "processed"
    reports: Path = REPORTS_DIR
    models: Path = MODELS_DIR


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
