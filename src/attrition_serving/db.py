from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


def get_engine():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "attrition_serving")
    user = os.getenv("DB_USER", "attrition")
    pwd = os.getenv("DB_PASSWORD", "attrition_pwd")

    url = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{name}"
    return create_engine(url, pool_pre_ping=True)
