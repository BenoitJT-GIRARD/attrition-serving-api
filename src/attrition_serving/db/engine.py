"""The database URL and the SQLAlchemy engine, built once.

`pool_pre_ping` is on because a managed PostgreSQL closes idle connections without telling
anyone, and a pooled connection that died between two requests fails on the next query
rather than on the checkout.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine


def get_database_url() -> str:
    """
    `DATABASE_URL` if it is set, otherwise rebuilt from the `DB_*` parts.

    No dotenv is read here. Loading environment files is the caller's job, and doing it in
    two places is how a script and the service end up talking to different databases.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "attrition_serving")
    user = os.getenv("DB_USER", "attrition")
    pwd = os.getenv("DB_PASSWORD", "attrition_pwd")

    return f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{name}"


def get_engine():
    url = get_database_url()

    # Supabase: SSL requis si oublié sslmode=require
    connect_args = {}
    if "supabase.co" in url and "sslmode" not in url:
        connect_args = {"sslmode": "require"}

    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)
