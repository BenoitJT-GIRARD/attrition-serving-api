import importlib

import pytest
from fastapi.testclient import TestClient

from attrition_serving.api.settings import reset_config_cache
from attrition_serving.db import get_engine
from attrition_serving.serving_db_ops import apply_schema, truncate_predictions


@pytest.fixture(scope="session")
def engine():
    eng = get_engine()
    apply_schema(eng)
    return eng


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    # Empêche tout dotenv de polluer
    monkeypatch.setenv("SKIP_DOTENV", "1")

    # Config test
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("MODEL_THRESHOLD", "0.5")
    monkeypatch.setenv("MODEL_VERSION", "test")

    # DB docker locale (assure-toi que docker compose up -d tourne)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://attrition:attrition_pwd@localhost:5432/attrition_serving",
    )

    reset_config_cache()


@pytest.fixture(autouse=True)
def clean_predictions(engine):
    truncate_predictions(engine)
    yield


@pytest.fixture()
def client():
    import attrition_serving.api.main as main

    importlib.reload(main)
    return TestClient(main.app)
