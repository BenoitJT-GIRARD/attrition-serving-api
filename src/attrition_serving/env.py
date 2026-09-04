from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]  # repo root (src/attrition_serving/env.py -> parents[2])


def load_env(default_env_file: str = ".env.local") -> None:
    """
    Charge .env puis un override (ENV_FILE) : .env.local ou .env.supabase.

    Règles:
    - En CI/tests : SKIP_DOTENV=1 => on ne charge rien.
    - Ne JAMAIS écraser une variable déjà définie (override=False),
      sinon la CI/secrets peuvent être écrasés par un .env local.
    - a file that does not exist is skipped rather than raising;
    """
    if os.getenv("SKIP_DOTENV", "") == "1":
        return

    base_path = ROOT / ".env"
    if base_path.exists():
        load_dotenv(base_path, override=False)

    env_file = os.getenv("ENV_FILE", default_env_file)
    env_path = ROOT / env_file
    if env_path.exists():
        load_dotenv(env_path, override=False)
