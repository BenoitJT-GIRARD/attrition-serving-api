import json
from pathlib import Path

from sqlalchemy import text

SAMPLE_PATH = Path("data/processed/api_test/X_test_sample.json")


def _count_predictions(engine) -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM predictions;")).scalar_one()


def _load_one_valid_payload() -> dict:
    rows = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    assert len(rows) > 0, "X_test_sample.json est vide"
    # on prend la 1ère ligne
    return {"features": rows[0]}


def test_predict_logs_row(client, engine):
    headers = {"X-API-Key": "test_key"}

    before = _count_predictions(engine)

    payload = _load_one_valid_payload()
    r = client.post("/predict", headers=headers, json=payload)

    assert r.status_code == 200, r.text

    after = _count_predictions(engine)
    assert after == before + 1


def test_history_returns_rows(client, engine):
    headers = {"X-API-Key": "test_key"}

    payload = _load_one_valid_payload()
    client.post("/predict", headers=headers, json=payload)
    client.post("/predict", headers=headers, json=payload)

    r = client.get("/history", headers=headers)
    assert r.status_code == 200, r.text

    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
