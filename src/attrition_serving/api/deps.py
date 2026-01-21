from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from attrition_serving.api.settings import get_config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Depends(api_key_header)) -> None:
    cfg = get_config()
    if not cfg.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY non configurée",
        )
    if api_key != cfg.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def get_sessionmaker():
    cfg = get_config()
    engine = create_engine(cfg.database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


SessionLocal = get_sessionmaker()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
