"""Loading the environment files, once, from the repository root.

Separate from `config` so that a test can import the settings without a dotenv appearing
underneath it: `SKIP_DOTENV=1` is what the API tests set, and it is honoured here for every
caller. An already-defined variable is never overwritten, so a stray `.env.local` on a
developer's machine cannot change what a CI run or a test reads.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from attrition_serving.utils.paths import ROOT_DIR


def load_env(default_env_file: str = ".env.local") -> None:
    """Read `.env`, then the deployment-specific file named by `ENV_FILE`.

    The split is deliberate: what is common to every deployment lives in the first, and what
    is a secret of one deployment lives in the second, which is never committed. A file that
    does not exist is skipped.
    """
    if os.getenv("SKIP_DOTENV", "") == "1":
        return

    base_path = ROOT_DIR / ".env"
    if base_path.exists():
        load_dotenv(base_path, override=False)

    env_path = ROOT_DIR / os.getenv("ENV_FILE", default_env_file)
    if env_path.exists():
        load_dotenv(env_path, override=False)
