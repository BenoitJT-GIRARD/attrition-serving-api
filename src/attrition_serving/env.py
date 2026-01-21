from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = (
    Path(__file__).resolve().parents[2]
)  # repo root (src/attrition_serving/env.py -> parents[2])


def load_env(default_env_file: str = ".env.local") -> None:
    """
    Charge .env puis un override (ENV_FILE) : .env.local ou .env.supabase.

    - En prod/dev/scripts : on charge.
    - En tests : SKIP_DOTENV=1 => on ne charge rien (tout vient de monkeypatch/env).
    """
    if os.getenv("SKIP_DOTENV", "") == "1":
        return

    load_dotenv(ROOT / ".env", override=False)

    env_file = os.getenv("ENV_FILE", default_env_file)
    load_dotenv(ROOT / env_file, override=True)
