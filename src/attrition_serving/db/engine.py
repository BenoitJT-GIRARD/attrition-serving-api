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


#: Hosts whose managed PostgreSQL refuses a connection without TLS, and does it with a message
#: that names nothing useful. Adding the parameter here is cheaper than the support round trip.
MANAGED_HOSTS = ("supabase.co",)


def connect_args_for(url: str) -> dict[str, str]:
    """What has to be added to a DSN before it will connect. A function, so it is testable.

    It used to be four lines inside `get_engine`, where the only way to check the decision was
    to build an engine and read back what SQLAlchemy had done with it.
    """
    if any(host in url for host in MANAGED_HOSTS) and "sslmode" not in url:
        return {"sslmode": "require"}
    return {}


def get_engine():
    url = get_database_url()
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args_for(url))
