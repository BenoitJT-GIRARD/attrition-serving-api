"""Request dependencies: the API key, and a database session per request.

The engine used to be created at import time, as a module-level `SessionLocal`. Two things
followed. It was built before the application had read its configuration, so the URL came
from whatever the environment happened to hold at import. And nothing ever disposed it: the
test suite reloads the module to reconfigure the app, and every reload left a pool of open
connections behind — visible as a `ResourceWarning` at interpreter shutdown, which is late
enough that nothing fails and no one looks.

It is now built on first use, cached, and disposed when the application shuts down.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from attrition_serving.api.settings import get_config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Depends(api_key_header)) -> None:
    cfg = get_config()
    if not cfg.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY is not configured",
        )
    if api_key != cfg.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@lru_cache
def get_engine() -> Engine:
    """The one engine this process uses, built on first request rather than on import."""
    return create_engine(get_config().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def dispose_engine() -> None:
    """Close the pool and forget it. Called on shutdown, and by tests between reloads."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


def get_db():
    db: Session = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
