"""The request and response models, from which the OpenAPI page is generated.

`PredictResponse` returns the threshold beside the probability. That carries the contract: a
probability that travels without its threshold is not a record of
anything, and the same pair is what goes into the decision log.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

Primitive = int | float | str | bool | None


class PredictRequest(BaseModel):
    """
    A flexible request, validated all the same:
    - features = dict[str, primitive]
    """

    features: dict[str, Primitive] = Field(..., description="Features brutes (avant encodage).")

    @field_validator("features")
    @classmethod
    def validate_primitives(cls, v: dict[str, Any]) -> dict[str, Primitive]:
        for k, val in v.items():
            if not isinstance(val, (int, float, str, bool)) and val is not None:
                raise ValueError(f"{k} carries an unsupported type: {type(val)}")
        return v


class PredictResponse(BaseModel):
    proba_depart: float
    prediction: int
    threshold: float
    model_version: str
    stored: bool
    db_id: int | None = None


class HistoryItem(BaseModel):
    id: int
    created_at: str
    employee_id: int | None
    proba_depart: float
    prediction: int
    threshold: float
    model_version: str
    input_payload: dict[str, Any]
