"""What the service does to a payload before the model sees it.

`normalize_payload` is the edge of the system: it accepts what an HR export actually holds —
`"M"`, `"Oui"`, a boolean from a JSON form — and hands the pipeline the dtypes it was trained
on. It had no test, and it is the function a caller hits first.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from attrition_serving.api import service


@pytest.fixture(autouse=True)
def _expected(monkeypatch, tmp_path):
    """A three-column contract, so the tests do not depend on the shipped artefact."""
    path = tmp_path / "expected_features.json"
    path.write_text(json.dumps(["age", "genre", "heure_supplementaires"]), encoding="utf-8")

    class Config:
        expected_features_path = path
        model_threshold = 0.25

    service.get_expected_features.cache_clear()
    monkeypatch.setattr(service, "get_config", lambda: Config)
    yield
    service.get_expected_features.cache_clear()


@pytest.mark.parametrize("sent", ["M", "H", "homme", "MALE", "1", " m "])
def test_every_spelling_of_male_becomes_one(sent) -> None:
    assert service.normalize_payload({"genre": sent})["genre"] == 1


@pytest.mark.parametrize("sent", ["F", "femme", "FEMALE", "0"])
def test_every_spelling_of_female_becomes_zero(sent) -> None:
    assert service.normalize_payload({"genre": sent})["genre"] == 0


@pytest.mark.parametrize(("sent", "expected"), [("Oui", 1), ("yes", 1), ("NON", 0), ("false", 0)])
def test_overtime_is_read_in_either_language(sent, expected) -> None:
    assert (
        service.normalize_payload({"heure_supplementaires": sent})["heure_supplementaires"]
        == expected
    )


def test_a_boolean_from_a_json_form_becomes_an_integer() -> None:
    normalised = service.normalize_payload({"genre": True, "heure_supplementaires": False})

    assert normalised["genre"] == 1
    assert normalised["heure_supplementaires"] == 0


def test_a_value_the_mapping_does_not_know_is_left_alone() -> None:
    """Refusing here would name a column; leaving it lets the 422 name the whole contract."""
    assert service.normalize_payload({"genre": "X"})["genre"] == "X"


def test_normalising_does_not_touch_the_caller_s_dictionary() -> None:
    sent = {"genre": "M"}

    service.normalize_payload(sent)

    assert sent == {"genre": "M"}


def test_a_payload_reports_what_is_absent_and_what_is_null_separately() -> None:
    missing, nulls = service.check_payload({"age": 41, "genre": None})

    assert missing == ["heure_supplementaires"]
    assert nulls == ["genre"]


def test_a_complete_payload_reports_nothing() -> None:
    complete = {"age": 41, "genre": 1, "heure_supplementaires": 0}

    assert service.check_payload(complete) == ([], [])


def test_the_frame_handed_to_the_pipeline_is_in_the_contract_s_order() -> None:
    """Column order is part of a fitted pipeline's contract; a dict has no order to trust."""
    aligned = service.align_features({"heure_supplementaires": 1, "age": 41, "genre": 0})

    assert list(aligned.columns) == ["age", "genre", "heure_supplementaires"]
    assert aligned.shape == (1, 3)
    assert aligned.loc[0, "age"] == 41


def test_a_feature_the_payload_omits_arrives_as_a_missing_value() -> None:
    aligned = service.align_features({"age": 41})

    assert pd.isna(aligned.loc[0, "genre"])


def test_the_decision_is_the_probability_against_the_configured_threshold() -> None:
    assert service.decide(0.25) == 1
    assert service.decide(0.2499) == 0


def test_a_contract_that_is_not_a_list_of_names_is_refused(tmp_path, monkeypatch) -> None:
    """A malformed artefact must fail where it is read, not where the column order is wrong."""
    path = tmp_path / "expected_features.json"
    path.write_text(json.dumps({"age": "int"}), encoding="utf-8")

    class Config:
        expected_features_path = path

    service.get_expected_features.cache_clear()
    monkeypatch.setattr(service, "get_config", lambda: Config)

    with pytest.raises(ValueError, match="list of column names"):
        service.get_expected_features()
