"""A missing key is 401, and a malformed payload is 422 naming what it is missing.

The second matters as much as the first: a caller assembling thirty-two features learns
every missing field at once, not one per round trip.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

from attrition_serving.api import settings


@pytest.fixture()
def client(monkeypatch):
    # No dotenv: the test decides the configuration, not whatever is on this machine.
    monkeypatch.setenv("SKIP_DOTENV", "1")

    # A complete environment, so nothing is read from a developer's own files.
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("MODEL_THRESHOLD", "0.5")
    monkeypatch.setenv("MODEL_VERSION", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/test_db",
    )

    # 3) Reset config cache
    settings.reset_config_cache()

    # Reload the app after the environment is set and the config cache is cleared.
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
