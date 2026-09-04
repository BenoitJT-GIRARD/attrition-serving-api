"""The threshold the service decides on, against the threshold the artefact declares.

This is the test the repository did not have. `api/settings.py` looked up
`model_card["threshold_default"]`; the export script writes `default_threshold`. The lookup
missed every time and the threshold fell back to 0.5, while every published figure said
0.32. On the test set that is recall 0.625 served against 0.833 documented — nine leavers
missed out of twenty-four instead of four.

Nothing in the pipeline could see it: no test loaded the model card, and no test compared a
served decision to the artefact that was supposed to produce it.
"""

from __future__ import annotations

import json

import joblib
import pandas as pd
import pytest

from attrition_serving.api.settings import get_config, reset_config_cache
from attrition_serving.config import PATHS

SAMPLES = PATHS.data_processed / "api_test" / "X_test_sample.json"


@pytest.fixture
def config(monkeypatch: pytest.MonkeyPatch):
    """The configuration as the service builds it, with no environment override."""
    monkeypatch.setenv("SKIP_DOTENV", "1")
    monkeypatch.delenv("MODEL_THRESHOLD", raising=False)
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test_db")
    reset_config_cache()
    yield get_config()
    reset_config_cache()


@pytest.fixture(scope="module")
def model_card() -> dict:
    return json.loads((PATHS.models / "model_card.json").read_text(encoding="utf-8"))


def test_the_service_decides_on_the_threshold_the_artifact_declares(config, model_card) -> None:
    """With no override, the service must read the card. It read a key that is not there."""
    assert config.model_threshold == pytest.approx(model_card["default_threshold"])


def test_an_environment_override_still_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """The variable is an override for an operator, not the source of the default."""
    monkeypatch.setenv("SKIP_DOTENV", "1")
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test_db")
    monkeypatch.setenv("MODEL_THRESHOLD", "0.61")
    reset_config_cache()
    try:
        assert get_config().model_threshold == pytest.approx(0.61)
    finally:
        reset_config_cache()


def test_the_shipped_artifact_loads_and_predicts() -> None:
    """A pickle names its module. Renaming the package made this file unloadable, and
    nothing noticed, because no test ever opened it."""
    pipeline = joblib.load(PATHS.models / "pipeline.joblib")
    expected = json.loads((PATHS.models / "expected_features.json").read_text(encoding="utf-8"))
    samples = pd.read_json(SAMPLES)

    proba = pipeline.predict_proba(samples[expected])[:, 1]
    assert len(proba) == len(samples)
    assert ((proba >= 0.0) & (proba <= 1.0)).all()


def test_the_card_records_the_library_that_wrote_the_artifact(model_card: dict) -> None:
    """A scikit-learn pickle is only readable by a compatible scikit-learn.

    Versioning the artefact without versioning what reads it is versioning a file, not a
    model.
    """
    import sklearn

    assert model_card["sklearn_version"], "the card must name the version that wrote the pickle"
    major_minor = tuple(model_card["sklearn_version"].split(".")[:2])
    assert major_minor == tuple(sklearn.__version__.split(".")[:2]), (
        f"artefact written by scikit-learn {model_card['sklearn_version']}, "
        f"environment has {sklearn.__version__} -- re-export before serving it"
    )


def test_the_decision_is_the_comparison_it_claims_to_be(config, model_card) -> None:
    """`decide` is one line, and it is the line the whole service exists to run."""
    from attrition_serving.api.service import decide

    threshold = model_card["default_threshold"]
    assert decide(threshold + 1e-9) == 1
    assert decide(threshold - 1e-9) == 0
    assert config.model_threshold == pytest.approx(threshold)
