import importlib

import pytest
from fastapi.testclient import TestClient

from attrition_serving.api import settings


@pytest.fixture()
def client(monkeypatch):
    # No dotenv: the test decides the configuration, not whatever is on this machine.
    monkeypatch.setenv("SKIP_DOTENV", "1")

    # 2) Force un environnement cohérent
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("MODEL_THRESHOLD", "0.5")
    monkeypatch.setenv("MODEL_VERSION", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/test_db",
    )

    # 3) Reset config cache
    settings.reset_config_cache()

    # 4) Recharger l'app après env + reset cache
    from attrition_serving.api import main

    importlib.reload(main)

    return TestClient(main.app)


def test_predict_requires_api_key(client):
    r = client.post("/predict", json={"age": 35})
    assert r.status_code == 401


def test_predict_validation_error(client):
    r = client.post(
        "/predict",
        headers={"X-API-Key": "test_key"},
        json={"age": "not_an_int"},
    )
    assert r.status_code == 422
